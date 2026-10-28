# Recherche dans les preuves (E01)

Index des **affirmations publiées** : chaque phrase factuelle d'une fiche projet publiée, avec la preuve qui la porte (URL, empreinte SHA-256 de la capture, pointeur dans le document, date de collecte). Il sert de base à la recherche serveur et à l'assistant sourcé ([E02](../tasks/E02.md)). Tâche : [E01](../tasks/E01.md).

## 1. Ce qui est indexé

L'index est dérivé de `project_detail` pour chaque projet de `published_slugs()`, donc exactement de ce que le site publie ; jamais une capture brute, une décision d'opérateur ni une clé de stockage. `evidence/search/claims.py` (fonctions pures) en tire une affirmation par :

| Genre (`kind`) | Texte indexé | Preuve |
| --- | --- | --- |
| `summary` | Résumé publié | Source du résumé |
| `handover` | Texte original de la date de remise des clés | Source et pointeur de la lecture |
| `programme_total` | Texte original du nombre total de logements | Idem |
| `typologies` | Texte original des typologies (une affirmation par texte, avec les types et chambres lus comme termes) | Idem |
| `amenity` | Texte original de l'équipement, avec son code et son libellé comme termes | Idem |
| `declared_progress` | Statut et avancement déclarés par l'autorité, valeurs publiées jointes | Lecture du registre |
| `registration` | Numéros d'enregistrement et de permis, statut, date, licence, part vendue | Dernière lecture du registre |
| `component_of`, `has_component` | Relation relue entre projets et sa justification | Page qui la justifie |

Règles : le texte est le **texte original** quand la fiche le porte ; sinon les valeurs publiées sont jointes avec leur nom (`register_status: Completed; progress_percent: 100.00`), jamais reformulées. Une affirmation sans source, sans URL ou dont la source est historique (`historical: true`) n'est pas indexée. Positions cartographiques, médias et signal satellite ne sont pas des phrases : ils restent sur la fiche.

`claim_key` est l'empreinte SHA-256 du projet, du genre, du chemin, du texte et de la preuve : une identité de citation stable. Une nouvelle lecture d'une source (autre empreinte) donne une nouvelle clé.

## 2. Recherche plein texte multilingue

`normalize` produit la forme de recherche : décomposition Unicode et retrait des accents et diacritiques arabes, casse repliée, variantes arabes usuelles repliées (`ة`→`ه`, `ى`→`ي`, tatweel retiré), un terme par caractère pour le chinois et le japonais (écrits sans espaces), mots seuls. La base applique ensuite la configuration PostgreSQL `simple` (aucune racinisation propre à une langue) : la même règle vaut pour les 16 langues et pour les textes originaux.

La table `evidence.evidence_search_entry` (migration `0040`) garde `search_text` (l'affirmation, poids A) et `project_terms` (nom du projet, promoteur, slug ; poids B). L'index GIN porte sur l'expression `setweight(to_tsvector('simple', search_text), 'A') || setweight(to_tsvector('simple', project_terms), 'B')` plutôt que sur une colonne stockée, pour que le vecteur n'entre pas dans les journaux de lignes ; `search/index.py` (`VECTOR_SQL`) interroge la même expression.

`search_claims(query, territory=None, limit=20)` exige chaque mot de la requête, en préfixe (`penth` trouve `penthouse`), classe par `ts_rank_cd` puis par projet, et ne renvoie jamais un projet retiré de la publication depuis la dernière reconstruction. Chaque résultat porte sa clé, son projet, son texte et sa preuve.

## 3. Reconstruction

Le flow `property-platform-evidence-search` (déploiement `evidence-search`, tous les jours à 02:30, **horaire inactif** jusqu'à décision) appelle l'opération de domaine `evidence_search`, qui exécute `rebuild_search_index` :

- verrou consultatif : une seule reconstruction à la fois ;
- un run `IngestionRun` (source `evidence-search-index`) par exécution Prefect, idempotent par clé de run ;
- en une transaction : insertion des affirmations nouvelles, suppression de celles qui ne sont plus publiées, les autres restent intactes ; les journaux de lignes ne notent donc que les vrais changements ;
- résumé : projets, affirmations, ajoutées, retirées, gardées.

Dans le contrôle de reconstruction ([REBUILD.md](REBUILD.md)), l'index est reconstruit en dernière étape de finition, après les relations et les liens de vérification ; la table suit la politique `derived` : son effectif est rapporté sans bloquer, car les fiches publiées dont elle dérive sont comparées elles-mêmes. `pipeline_inventory.py` la rattache au flow `property-platform-evidence-search`.

## 4. Route HTTP

`GET /api/v1/preview/evidence-search?q=…&territory=…&limit=…&mode=…` (opération `previewEvidenceSearch`, `api/evidence_search.py`) renvoie `{"items": [...], "mode": …, "semantic": …}`. `mode=text` (défaut) répond par `search_claims` ; `mode=hybrid` par `hybrid_claims` (§5), et `semantic` vaut `true` seulement si le classement sémantique a été fusionné : sans le service, la réponse hybride est exactement la réponse plein texte avec `semantic: false`. Le score sémantique n'est jamais renvoyé. Chaque élément est tel que `search_claims` le produit : clé de citation, projet, genre, chemin, texte, langue, preuve (URL, nom, genre, SHA-256, pointeur, date de collecte) et date d'indexation. `q` est obligatoire (1 à 120 caractères), `territory` prend les mêmes valeurs que l'annuaire des projets, `limit` va de 1 à 50 (20 par défaut). Comme toute route `/preview`, elle répond `403 preview_disabled` hors prévisualisation locale. Les réponses `text` passent par le cache de lecture (`cached_read`) : l'ETag change dès qu'une reconstruction écrit dans la table journalisée. Les réponses `hybrid` ne sont jamais mises en cache : elles dépendent aussi de la disponibilité du service facultatif, que le cache ne suit pas (un repli enregistré pendant une panne lui survivrait). Le contrat est dans `packages/contracts` (`openapi.json`, `src/generated.ts`).

## 5. Recherche sémantique (vecteurs)

Facultative : elle n'existe que si le service `embeddings` tourne et si `EVIDENCE_EMBEDDINGS_URL` le désigne (`infra/local/compose.embeddings.yaml` le règle pour `api` et `ingestion` ; à combiner avec `compose.ingestion.yaml`). Sans lui, tout ce qui précède reste complet et inchangé.

- **Modèle** : `intfloat/multilingual-e5-small`, révision figée dans `search/embeddings.py`, servi par Text Embeddings Inference ([TOOLCHAIN.md](TOOLCHAIN.md)). Avant tout calcul, `check_model` lit `/info` et refuse un service qui annonce un autre modèle ou une autre révision : l'index ne mélange jamais des vecteurs de modèles différents.
- **Texte vectorisé** : `passage: <nom du projet>: <texte de l'affirmation>` ; la requête devient `query: <requête>` (préfixes d'entraînement des modèles E5). Le nom du projet place une date ou un équipement sous son projet ; rien n'est reformulé ni affiché à partir de ce texte.
- **Stockage** : table journalisée `evidence.evidence_search_embedding` (migration `0041`), un vecteur unitaire float32 (384 × 4 octets) par affirmation, avec `model` = `<modèle>@<révision>` et le run qui l'a calculé. Pas de pgvector : l'image PostGIS partagée ne l'a pas, et l'index publié (moins d'un millier d'affirmations) se classe en mémoire. Au-delà de quelques dizaines de milliers d'affirmations, passer à pgvector par une migration explicite.
- **Reconstruction** : après la transaction plein texte, `rebuild_search_index` calcule les vecteurs des affirmations qui n'en ont pas pour le modèle figé (une nouvelle révision les recalcule tous et remplace les anciens). Une affirmation retirée emporte son vecteur. Le résumé du run porte `embeddings` : `not_configured`, `unreachable`, `unexpected_model`, `unexpected_vectors`, ou `succeeded` avec `model`, `added`, `replaced`. L'indisponibilité du service ne fait jamais échouer le run. Dans le contrôle de reconstruction, la table suit la politique `derived`.
- **Requêtes** : `semantic_claims(query, territory, limit)` classe toutes les affirmations publiées qui ont un vecteur du modèle figé par similarité cosinus (champ `score`), sans seuil ; elle lève `EmbeddingsUnavailable` sans le service. `hybrid_claims` fusionne les classements plein texte et sémantique par rang réciproque (`1/(60 + rang)`) et renvoie `(résultats, sémantique_disponible)` ; sans le service, la réponse est celle du plein texte. Chaque résultat porte la même preuve que la recherche plein texte.

**Mesure réelle du 27 octobre** (service local, modèle figé, quatre affirmations types) : la requête arabe « شقق بثلاث غرف » trouve les typologies (0,882 contre 0,807 au suivant) et la question chinoise sur l'achèvement trouve le statut « Completed » du registre ; en revanche, des requêtes françaises courtes (« piscine », « date de livraison ») placent d'abord l'affirmation du registre au format `champ: valeur`, de peu (0,838 contre 0,837 pour la piscine). Les écarts de score d'e5-small sont faibles et ces textes structurés attirent les requêtes courtes : la recherche sémantique seule n'est pas assez fiable pour être affichée telle quelle ; la fusion hybride, qui garde en tête ce que le plein texte trouve, est la forme à exposer.

## 6. Évaluation sur les affirmations publiées

`python manage.py evaluate_evidence_search [--mode text|semantic|hybrid] [--k 10]` (`search/evaluation.py`) mesure la recherche sur ce que le site publie au moment du lancement, **en lecture seule** : les affirmations sont tirées de `published_claims()` en mémoire, le plein texte applique l'expression de l'index (`VECTOR_SQL`) à des tableaux littéraux et les vecteurs sont calculés à la volée ; ni les tables de l'index ni aucune écriture ne sont nécessaires (on peut la lancer avec `PGOPTIONS="-c default_transaction_read_only=on"`). Chaque cas associe une requête à une règle de pertinence sur les champs structurés (genre, chemin, fragment du texte original), jamais à des réponses écrites à la main. Pour chaque cas et chaque mode : nombre d'affirmations pertinentes, nombre de réponses, pertinentes parmi les `k` premières, rang de la première pertinente. Les classements sont ceux de `search_claims` et `hybrid_claims` (même ordre, même fusion, test PostGIS).

**Mesure du 27 octobre, plein texte** (873 affirmations de 183 projets, toutes en anglais ; base partagée en lecture seule) :

| Requête | Langue | Pertinentes | Réponses | Pertinentes parmi les 10 premières | Première pertinente |
| --- | --- | --- | --- | --- | --- |
| swimming pool | en | 102 | 105 | 10 | 1 |
| gym | en | 23 | 25 | 10 | 1 |
| penthouse | en | 43 | 44 | 10 | 1 |
| studio | en | 39 | 44 | 9 | 1 |
| villa | en | 66 | 74 | 9 | 2 |
| completed | en | 6 | 12 | 5 | 1 |
| under construction | en | 26 | 52 | 5 | 1 |
| registration number | en | 32 | 32 | 10 | 1 |
| number of units | en | 62 | 5 | 4 | 1 |
| tower 2 | en | 2 | 55 | 2 | 3 |
| handover date | en | 89 | 0 | 0 | — |
| piscine, salle de sport, appartements de trois chambres, date de livraison, numéro d'enregistrement, nombre de logements | fr | — | 0 | 0 | — |
| مسبح, شقق بثلاث غرف | ar | — | 0 | 0 | — |
| 游泳池, 项目是否已经完工 | zh | — | 0 | 0 | — |

Lecture : le plein texte est précis pour le vocabulaire anglais des sources (équipements, typologies, statut, enregistrement). Il ne trouve rien dans une autre langue, car les textes originaux publiés sont tous en anglais et ne sont jamais traduits, ni quand le texte est une valeur nue (une date de remise des clés `2028-05-01` ne contient pas le mot « handover »). La recherche dans les 16 langues du site passe donc par le classement sémantique (§5), qui n'a été mesuré que sur quatre affirmations : sa mesure sur les 873 affirmations réelles demande de placer les poids du modèle figé (environ 470 Mo, Hugging Face, licence MIT) dans le cache monté du service local, ce que ce lot n'a pas fait sans l'accord du propriétaire.

## 7. Reste à faire (E01)

- Mesure `semantic` et `hybrid` sur les affirmations réelles avec le service local (décision du propriétaire : téléchargement des poids du modèle), puis choix du mode par défaut de la route.
- Cas d'usage web (relais `app/api/…` et affichage), si la tâche le garde plutôt que de le laisser à E02.
