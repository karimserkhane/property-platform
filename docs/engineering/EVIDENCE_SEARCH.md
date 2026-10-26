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

La table `evidence.evidence_search_entry` (migration `0038`) garde `search_text` (l'affirmation, poids A) et `project_terms` (nom du projet, promoteur, slug ; poids B). L'index GIN porte sur l'expression `setweight(to_tsvector('simple', search_text), 'A') || setweight(to_tsvector('simple', project_terms), 'B')` plutôt que sur une colonne stockée, pour que le vecteur n'entre pas dans les journaux de lignes ; `search/index.py` (`VECTOR_SQL`) interroge la même expression.

`search_claims(query, territory=None, limit=20)` exige chaque mot de la requête, en préfixe (`penth` trouve `penthouse`), classe par `ts_rank_cd` puis par projet, et ne renvoie jamais un projet retiré de la publication depuis la dernière reconstruction. Chaque résultat porte sa clé, son projet, son texte et sa preuve.

## 3. Reconstruction

Le flow `property-platform-evidence-search` (déploiement `evidence-search`, tous les jours à 02:30, **horaire inactif** jusqu'à décision) appelle l'opération de domaine `evidence_search`, qui exécute `rebuild_search_index` :

- verrou consultatif : une seule reconstruction à la fois ;
- un run `IngestionRun` (source `evidence-search-index`) par exécution Prefect, idempotent par clé de run ;
- en une transaction : insertion des affirmations nouvelles, suppression de celles qui ne sont plus publiées, les autres restent intactes ; les journaux de lignes ne notent donc que les vrais changements ;
- résumé : projets, affirmations, ajoutées, retirées, gardées.

Dans le contrôle de reconstruction ([REBUILD.md](REBUILD.md)), l'index est reconstruit en dernière étape de finition, après les relations et les liens de vérification ; la table suit la politique `derived` : son effectif est rapporté sans bloquer, car les fiches publiées dont elle dérive sont comparées elles-mêmes. `pipeline_inventory.py` la rattache au flow `property-platform-evidence-search`.

## 4. Route HTTP

`GET /api/v1/preview/evidence-search?q=…&territory=…&limit=…` (opération `previewEvidenceSearch`, `api/evidence_search.py`) renvoie `{"items": [...]}`, chaque élément tel que `search_claims` le produit : clé de citation, projet, genre, chemin, texte, langue, preuve (URL, nom, genre, SHA-256, pointeur, date de collecte) et date d'indexation. `q` est obligatoire (1 à 120 caractères), `territory` prend les mêmes valeurs que l'annuaire des projets, `limit` va de 1 à 50 (20 par défaut). Comme toute route `/preview`, elle répond `403 preview_disabled` hors prévisualisation locale et passe par le cache de lecture (`cached_read`) : l'ETag change dès qu'une reconstruction écrit dans la table journalisée. Le contrat est dans `packages/contracts` (`openapi.json`, `src/generated.ts`).

## 5. Reste à faire (E01)

- Recherche vectorielle (sémantique et interlangue) : extension pgvector et modèle d'embeddings local, service Docker optionnel et figé, sans service payant.
- Cas d'usage web (relais `app/api/…` et affichage), si la tâche le garde plutôt que de le laisser à E02.
