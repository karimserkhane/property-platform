# Feuille de route technique — performance, fiabilité et modularité

Document vivant ouvert le 23 octobre 2026 par Claude Code, à partir de mesures locales. Il complète la [revue de plateforme du 21 octobre](PLATFORM_REVIEW_20261021.md), centrée sur la qualité des données et le parcours utilisateur. Chaque chantier ci-dessous est livré par une pull request courte, testée et documentée ; mettre à jour ce document quand un chantier est terminé ou repriorisé.

## Principes retenus

- **Mesurer avant d'optimiser.** Une optimisation cite sa mesure avant/après dans sa PR. Les chiffres ci-dessous servent de référence.
- **Ne pas recalculer pour chaque visiteur ce qui ne change qu'à l'ingestion.** Les lectures lourdes sont mises en cache avec une invalidation liée à la version des données, jamais avec une durée arbitraire qui afficherait une source exclue.
- **Une seule implémentation par préoccupation transverse** : gardes d'accès, erreurs, compression, journaux, pagination. Une nouvelle route ou une nouvelle source les réutilise au lieu de les recopier.
- **Envoyer au navigateur seulement ce qu'il affiche** : données compressées, découpées par zone et par zoom, images servies comme fichiers cachables.
- **Tester au bon niveau** : fonctions pures en tests unitaires, requêtes et transactions sur PostGIS réel, parcours utilisateur dans un vrai navigateur.
- **Contrats stables** : une optimisation interne ne modifie pas le contrat OpenAPI ; un changement de contrat est explicite et régénéré.

## Mesures du 23 octobre 2026

Environnement local Docker, données réelles d'Al Reem, zone `54.39,24.48,54.42,24.51`, médiane de cinq appels directs à l'API.

| Lecture | Temps serveur | Taille JSON | Compressée (gzip) |
| --- | --- | --- | --- |
| `parcels` (1 000 parcelles) | 0,30 s | 1,04 Mo | 160 Ko |
| `map-context` (rues, bâtiments, lieux, zones) | 0,70 s, 41 requêtes SQL | 1,68 Mo | 216 Ko |
| `district-map` | 0,67 s | 478 Ko | 118 Ko |
| `market-map` | 0,82 s | 140 Ko | 41 Ko |
| `imagery` | 0,11 s | 857 Ko | 649 Ko |
| `projects` (48 fiches) | 0,09 s | 22 Ko | 5 Ko |

Autres constats :

- **Les relais `/api/atlas/*` du site renvoyaient ce JSON sans compression** : Next.js compresse les pages, pas les réponses des route handlers, et l'accès privé Tailscale n'ajoute pas de compression. Un téléphone téléchargeait donc 1 à 1,5 Mo à chaque déplacement de carte. Corrigé par le chantier 2.
- **JavaScript** : environ 500 Ko (165 Ko compressés) de socle React/Next.js par page ; MapLibre n'est chargé que sur les pages de carte. Le poids JavaScript n'est pas la priorité.
- **`district-map`** : la simplification des 216 contours est faite ligne par ligne en Python (GEOS), avec une lecture d'historique par ligne ; seules deux requêtes SQL sont lourdes.
- **`imagery`** : les images sont intégrées en base64 dans le JSON (857 Ko quasi incompressibles) au lieu d'être des fichiers cachables.
- **Base** : `evidence.capture` stocke 817 Mo de contenus bruts dans PostgreSQL pour 2 420 captures, ce qui alourdit chaque sauvegarde.

## Chantiers

| # | Chantier | Gain attendu | État |
| --- | --- | --- | --- |
| 1 | Journaux et trace complète des échecs ; gardes communes des routes API | Diagnostic des imports ; moins de code recopié | Fusionné (PR #1) |
| 2 | Compression brotli/gzip et relais partagé des lectures `/api/atlas/*` | 5 à 7 fois moins de données par affichage de carte | Fusionné (PR #2) |
| 3 | Tuiles vectorielles PostGIS (`ST_AsMVT`) pour parcelles et bâtiments | Carte fluide à l'échelle des sept émirats ; fin de la limite de 12 000 parcelles | Parcelles de l'explorateur : PR #3 ; index par zone : A06 ; bâtiments et rues : A07 |
| 4 | Cache des lectures lourdes avec `ETag` lié à la version des données (`evidence.row_revision`) | `district-map`, `market-map`, `map-context` instantanés en lecture répétée | PR #4 (instantané PostgreSQL) ; version par famille de tables : A08 ; tables de provenance : A16 |
| 5 | Simplification des contours en SQL et regroupement des requêtes de `map-context` | Temps serveur divisé avant même le cache | À faire |
| 6 | Images satellite servies comme fichiers cachables au lieu de base64 dans le JSON | −850 Ko sur la vue imagerie | À faire |
| 7 | Sauvegarde automatique PostgreSQL + stockage privé, avec test de restauration planifié | Reprise après perte de données | Fusionné (PR #8, tâche A03) ; sauvegarde quotidienne et test de restauration hebdomadaire actifs |
| 8 | Tests de parcours navigateur (Playwright) : recherche, fiche, arabe RTL, mobile ; budgets de performance en CI | Régressions visibles avant fusion | À faire |
| 9 | Contenus bruts des captures vers le stockage objet, adressés par SHA-256 | Base et sauvegardes beaucoup plus légères | À faire |
| 10 | Découpage interne d'`evidence` (95 fichiers, 14 700 lignes) en sous-paquets : projets, cartes, sources, historique | Ajout de fonctionnalités sans module fourre-tout ; même application Django et mêmes migrations | À faire |
| 11 | Composants carte : état regroupé en hooks/reducers (`explorer.tsx` 20 états, `map-workbench.tsx` 18) | Fonctionnalités carte plus simples à ajouter et à tester | À faire |
| 12 | Chaîne d'approvisionnement : images et actions par digest, mises à jour automatisées, analyse de vulnérabilités | Builds reproductibles et sûrs | À faire |

Ordre proposé : 3 et 4 d'abord (passage à l'échelle et temps de réponse), puis 7 et 8 (filets de sécurité), puis les chantiers de structure. Le chantier 4 doit traiter un cas limite : deux transactions concurrentes peuvent valider dans le désordre, donc une version fondée sur le seul maximum de `row_revision` doit être complétée (par exemple par l'horizon des transactions en cours) pour ne jamais servir une donnée exclue.

## Tuiles vectorielles des parcelles — 23 octobre 2026

L'explorateur dessine les contours de parcelles depuis des tuiles vectorielles PostGIS au lieu de télécharger toutes les géométries en GeoJSON.

- `GET /api/v1/preview/parcel-tiles/{z}/{x}/{y}` (zooms 8 à 16, `territory` facultatif) renvoie une tuile Mapbox Vector Tile, couche `parcels`, avec la seule propriété `id`. Mêmes règles d'identité que `/parcels` : parcelles courantes (`superseded_by` nul) et espaces de noms du territoire.
- `GET /api/v1/preview/parcel-index` renvoie les mêmes lignes publiées que `/parcels`, sans géométrie, avec `bounds`, `label_point`, `area_m2` et `nearby_projects`. Les distances aux repères de projet (50 m au plus, 0 à l'intérieur) sont calculées dans PostGIS ; le navigateur applique les mêmes règles de choix qu'avant (identité de projet, ambiguïté sous 10 m).
- Côté carte, la catégorie et la visibilité de chaque parcelle sont posées en `feature-state` à partir de l'index : une tuile ne peut pas afficher une parcelle que l'index n'a pas publiée, ni une couleur différente. Les libellés viennent d'une petite source de points.
- La carte de quartier des fiches projet garde ses parcelles GeoJSON (zone réduite) ; le style partagé n'est pas modifié.

Mesures (vue « toute la zone » d'Abu Dhabi, réponses compressées) : une ligne d'index pèse environ 63 octets contre 135 avec sa géométrie ; une tuile vaut 37 Ko au zoom 14 et 175 Ko au zoom 10 à 12 pour toute l'île. Le gain actuel tient surtout au rendu (MapLibre ne découpe plus 10 000 polygones dans le navigateur) et au chargement progressif par zone ; il devient décisif à l'échelle nationale. Prochaines étapes : servir l'index par zone visible plutôt que pour tout le territoire, puis les bâtiments en tuiles.

**Allègement du chargement — 23 octobre 2026.** Retour sur téléphone : la carte semblait plus lente. Deux corrections :

- En dessous du zoom 12, une tuile omet les parcelles de moins d'un demi-pixel à l'écran (seuil d'aire en Web Mercator selon le zoom) ; à partir du zoom 12, toutes les parcelles sont dessinées. Tuiles mesurées au même endroit : zoom 8 191 → 12 Ko, zoom 9 340 → 31 Ko, zoom 10 356 → 76 Ko, zoom 11 361 → 240 Ko.
- L'explorateur dessine l'index page par page (3 000 lignes) au lieu d'attendre la dernière page ; un échec d'une page suivante rejette toujours l'ensemble de la lecture.

**Index par zone visible — 25 octobre 2026 (tâche A06).** L'explorateur ne lit plus l'index de tout le territoire au chargement :

- `features/atlas/parcel-viewport.ts` découpe la vue en cellules fixes de 0,05° (au plus 16, soit la plus grande `bbox` acceptée par l'API), limitées à l'emprise de collecte, et garde les 48 dernières cellules lues (LRU, lectures en échec non conservées). Revenir sur une zone déjà vue ne coûte aucune requête. Vue plus large que 16 cellules : les lignes déjà dessinées restent et l'avis « limite de prévisualisation atteinte » s'affiche.
- Recherche : `GET /api/v1/preview/parcel-search?q=&territory=&limit=` (relais `/api/atlas/parcel-search`) renvoie les lignes d'index dont le code commence par `q` dans tout le territoire ; la recherche de la carte complète les résultats visibles par ces lignes, et choisir une parcelle hors vue recadre la carte sur elle.
- Export CSV : relit à la demande l'index de tout le territoire (pages de 3 000 lignes, filtre d'usage appliqué), comme avant ; la lecture n'a lieu qu'au clic.

Mesures (API locale, Abu Dhabi, JSON décompressé, même méthode que la mesure « avant » du 24 octobre) :

| Lecture | Avant | Après |
| --- | --- | --- |
| Chargement, vue type zoom 14 au centre | 3 requêtes, 8 377 lignes, 5,46 Mo, 1,8 à 2,1 s | 2 cellules, 3 requêtes, 5 193 lignes, 3,39 Mo, 0,1 à 1,2 s |
| Déplacement de 0,03° puis retour | aucune (tout est déjà lu) | 0 requête (cellules en cache) |
| Vue zoom 15, cache vide | 3 requêtes, 8 377 lignes | 1 cellule, 2 requêtes, 3 843 lignes, 2,51 Mo, 0,1 s |
| Export CSV | sans lecture (index déjà chargé) | 3 requêtes, 8 377 lignes, 5,46 Mo, environ 3 s au clic |

Le gain est modeste sur la seule zone collectée aujourd'hui (0,1° × 0,14°) : une cellule couvre plus que la vue au zoom 15. Il devient décisif avec F01 (émirat entier), où le chargement reste borné par les cellules visibles alors que la lecture complète croîtrait avec le territoire. Si la recherche ralentit à cette échelle, ajouter un index sur `code` ; si les cellules pèsent trop au zoom 15, les adapter au zoom.

**Bâtiments et rues en tuiles — 25 octobre 2026 (tâche A07).** L’explorateur ne lit plus `map-context` :

- `GET /api/v1/preview/context-tiles/{z}/{x}/{y}` (zooms 11 à 16, relais `/api/atlas/context-tiles`) : couches `building` (propriété `id`) et `street` (`id`, `name`, `name_ar` : un libellé placé le long d’une ligne lit les propriétés de la tuile, pas l’état d’élément). Mêmes sources et éléments actifs que `map-context` ; sous le zoom 12, les bâtiments de moins d’un demi-pixel sont omis.
- `GET /api/v1/preview/context-index` (relais `/api/atlas/context-index`) : les lignes de `map-context`, rues et bâtiments sans géométrie mais avec `bounds` ; lieux et zones inchangés. L’explorateur marque chaque ligne de sa couche (`IndexedFeature`) ; le code partagé lit `featureShape`, `featureBounds` et `frameGeometry` au lieu de la géométrie. Les `bounds` ne servent qu’au cadrage, jamais au dessin ni au clic.
- Hauteurs en état d’élément ; la vue 3D « hauteurs relevées seulement » filtre sur la liste des identités à hauteur relevée (un filtre ne lit pas l’état d’élément). Clic : l’emprise rendue sous le pointeur, rattachée à sa ligne d’index par identité ; un élément de tuile absent de l’index n’est pas sélectionnable. Ombres solaires : emprises des tuiles chargées (une emprise coupée par un bord de tuile donne un morceau par tuile), hauteurs de l’index.
- La carte de voisinage des fiches projet garde `map-context` (rayon réduit, outils fondés sur la géométrie) ; le style partagé reste compatible avec ses sources GeoJSON.

Mesures (base locale, lecture seule) : Al Reem 0,04 × 0,03° — `map-context` 1 488 Kio brut / 197 Kio gzip, `context-index` 1 286 / 150 Kio, 16 tuiles z15 = 78 Kio ; Saadiyat 0,06 × 0,04° — 1 734 / 210 Kio contre 1 456 / 153 Kio, 35 tuiles z15 = 94 Kio. La géométrie ne pèse qu’environ 15 % du brut : l’essentiel vient des métadonnées `source` répétées par élément (210 Kio pour les rues et 277 Kio pour les lieux à Al Reem). Publier chaque provenance une fois par réponse est la prochaine piste, à proposer comme tâche séparée. Le gain principal est le rendu : MapLibre ne découpe plus les emprises GeoJSON dans le navigateur et les tuiles se chargent par zone.

**Premier import de l’émirat : WRM — 27 octobre 2026 (tâche F03).** Le déploiement manuel `wrm-parcels-adsdi-districts` (flow run `reliable-hippo`) a importé les 46 districts d’Al Dhafra en 17 minutes : **40 752 parcelles observées**, exactement l’effectif du registre revu, dont 40 750 créées et **2 en quarantaine** (géométrie AD-SDI invalide, PLOTID 347654 à Eastern Mahadir et 358310 à Ghayathi) ; aucun district en échec.

Mesures (API locale, lecture seule ; temps du premier appel, médiane de cinq appels répétés servis par le cache de lecture ; tailles non compressées, la compression se fait au relais du site) :

| Lecture | Avant | Après |
| --- | --- | --- |
| Parcelles courantes en base | 8 379 | 49 129 |
| `real_estate.parcel` / `evidence.parcel_observation` | 8 Mo / 28 Mo | 30 Mo / 49 Mo |
| Base entière | 873 Mo | 1 090 Mo (+217 Mo, surtout captures et journaux de lignes) |
| Tuile z8 couvrant Al Reem et l’est d’Al Dhafra, sans territoire | 13 Ko, 0,14 s | 91 Ko, 0,28 s ; 0,04 s répétée |
| Tuile z10 de Madinat Zayed, sans territoire | vide (204) | 161 Ko, 0,19 s ; 0,03 s répétée |
| Tuile z12 / z14 de Madinat Zayed | vide | 104 Ko / 2 Ko, 0,1 s |
| Tuiles d’Al Reem z10 à z16, territoire `abu-dhabi` | 2 à 347 Ko, 0,1 à 0,2 s | identiques (±4 octets), 0,1 à 0,2 s |
| Index, cellule de 0,05° à Madinat Zayed, sans territoire | 0 ligne | 893 lignes, 574 Ko, 0,04 s |
| Index, vue maximale de 0,2° à Madinat Zayed | 0 ligne | 3 000 lignes (page pleine), 1,9 Mo, 0,07 s |
| Index, cellule de 0,05° à Al Reem | 2 779 lignes, 1,8 Mo, 0,05 à 0,13 s | identique |

Lecture : à 49 000 parcelles, tuiles et index par zone restent sous 0,3 s au premier appel, et le coût d’une zone ne dépend que de ce qu’elle contient ; les îles ne ralentissent pas. Une ligne d’index pèse environ 640 octets non compressés et une parcelle environ 5 Ko en base, captures comprises : l’émirat entier (environ 410 000 parcelles) représenterait de l’ordre de 2 Go. **Limite levée par F04** : le territoire `abu-dhabi` de l’explorateur réunissait seulement les trois îles revues ; depuis F04 (`publication/coverage.py`, `emirate_profile`), il lit les parcelles importées de tous les districts du registre. Leur affichage, puis les imports ADM et AAM et la mesure à l’échelle de l’émirat, forment [F04](../tasks/F04.md).
**Import ADM — 27 octobre 2026 (tâche F04).** Le déploiement manuel `adm-parcels-adsdi-districts` (flow run `refined-piculet`, 2 h 05) a parcouru les 98 districts d’Abu Dhabi : 97 importés, **176 536 parcelles créées**, 184 573 observations. Les trois îles revues ont été relues sous leur espace de noms d’origine, sans doublon : Al Maryah 73 inchangées ; Al Reem 2 499 inchangées, 2 416 concordantes, 5 conflits de géométrie et 2 identifiants différents pour une forme quasi identique, en quarantaine ; Saadiyat 5 279 inchangées, 4 987 concordantes, 10 conflits de géométrie, 165 identifiants différents pour une forme quasi identique, 1 géométrie invalide et 1 recouvrement multiple, en quarantaine. Ailleurs, 2 géométries invalides (Al Muntazah, Khalifa Industrial). **Madinat Al Riyad a échoué** (`SourceError` dès la liste) : ses 35 077 parcelles dépassaient le plafond de 20 000 identifiants hérité d’Onwani. AD-SDI a désormais son propre plafond (50 000, testé contre le plus grand district du registre) ; le district sera importé par le même déploiement après fusion.

Mesures (code de la branche F04 sur la base partagée, en lecture seule ; premier appel, puis médiane de cinq appels servis par le cache ; tailles non compressées) :

| Lecture | F03 (49 129 parcelles) | Après ADM (225 665 courantes) |
| --- | --- | --- |
| `real_estate.parcel` / `evidence.parcel_observation` | 30 Mo / 49 Mo | 133 Mo / 146 Mo |
| Base entière | 1 090 Mo | 2 069 Mo |
| Tuile z8 de la ville d’Abu Dhabi | 91 Ko, 0,28 s | 243 Kio, 0,6 à 1,8 s ; 0,003 s répétée |
| Tuile z10 de Khalifa City / d’Al Zahiyah | — | 1 505 / 441 Kio, 0,5 / 0,2 s |
| Tuiles z12 et z14 en ville | — | 90 à 720 Kio, 0,03 à 0,13 s |
| Tuiles d’Al Reem et de Madinat Zayed, territoire `abu-dhabi` | 0,1 à 0,2 s | 0,02 à 0,12 s |
| Index, cellule de 0,05° en ville (Al Zahiyah, Khalifa City, Musaffah, Al Reem) | Al Reem : 2 779 lignes, 0,05 à 0,13 s | 3 000 lignes (page pleine), 1,8 Mio, 1,0 à 1,4 s |
| Recherche de parcelle dans le territoire | — | 0,13 à 0,20 s (0,75 à 0,98 s avant correctif) |

Constats :

- **Provenance indexée.** Chaque lecture de provenance des parcelles parcourait toute la table des observations (alternative « remplacement accepté » de `evidence/projects/queries.py`) : 0,53 s pour une cellule de 3 000 parcelles, puis autant pour la relecture de contrôle du cache. Restreindre les observations aux parcelles demandées et à celles qu’elles remplacent, ce que les deux branches impliquent déjà, utilise les index : 0,10 s ; la recherche passe sous 0,2 s. Le reste du coût d’une page pleine vient de la sérialisation de 3 000 lignes et de la relecture de contrôle ; il dépend de la page, plus de la taille de l’émirat.
- **Index sur `code`** : non ajouté, la recherche reste sous 0,2 s.
- **Explorateur.** En ville, une cellule de 0,05° dépasse la page de 3 000 lignes, et la vue initiale du territoire, bornée désormais par l’émirat, couvre 18 à 28 cellules selon l’écran (contre 12 bornée aux îles) pour un budget de 16 : la liste demandait alors de zoomer, les tuiles restant dessinées et cliquables. Depuis le 27 octobre, jusqu’à quatre fois le budget (64 cellules), l’explorateur lit les 16 cellules les plus proches du centre de la vue et affiche l’avis de données partielles (`parcel-viewport.ts`) ; au-delà, rien n’est lu. Le budget de l’API et la taille des cellules ne changent pas : une cellule pleine en ville reste tronquée à 3 000 lignes avec le même avis.

## Cache des lectures et requêtes conditionnelles — 23 octobre 2026

`api/read_cache.py` met en cache les lectures `/preview` sans effet de bord (parcelles, index, tuiles, contexte, quartiers, marché, projets, références, imagerie) et répond aux requêtes conditionnelles.

- **Version des données** : `pg_current_snapshot()` (prochain identifiant de transaction et écritures en cours) est lu *avant* les données. Toute validation qui pourrait changer une lecture change cet instantané ; une réponse ou un ETag n'est donc jamais servi après un changement, exclusion de source comprise. Aucune durée arbitraire. Un corps en mémoire est gardé plus longtemps selon sa famille de tables (ci-dessous).
- **Validation d'abord** : pour une adresse jamais servie, l'instantané est relevé juste avant la première requête de données de la route ; une requête rejetée par la validation n'atteint toujours pas la base.
- **Mémoire bornée** : une entrée par adresse (la plus récente), 64 Mo au total, 8 Mo par réponse, éviction LRU. Les erreurs et les flux (médias) ne sont jamais mis en cache.
- **Navigateur** : les relais transmettent `If-None-Match`, renvoient `304` et `ETag` faible avec `Cache-Control: private, no-cache` ; sans ETag, la réponse reste `no-store`.

Mesures par le relais (réponses brotli) : `district-map` 0,7 s → 0,08 s en relecture et 0,03 s en revalidation `304` sans corps ; `market-map` 0,8 s → 0,05 s ; index et tuiles de parcelles 0,02 s en `304`. Limite du 23 octobre : n'importe quelle écriture renouvelait la version ; les collectes planifiées chaque minute (file des fonds de carte, zones de marche) la faisaient changer environ une fois par minute en local.

### Version par famille de tables — 26 octobre 2026 (A08)

Une réponse en mémoire reste valable tant qu'aucune validation n'écrit dans **sa famille** : les tables que sa route a réellement lues.

- **Famille relevée, jamais déclarée** : à la première lecture d’une adresse, `pg_stat_xact_user_tables` liste, transaction par transaction, les tables parcourues (y compris par les fonctions et vues SQL). Aucune liste à tenir à jour route par route, donc aucun oubli possible ; si les données lues changent de chemin de code, la famille change d'abord et la route est relue. `public.spatial_ref_sys` (PostGIS, modifiée seulement par l'extension) est ignorée.
- **Version** : pour chaque table de la famille, la dernière ligne visible de `evidence.row_revision` (index `row_revision_table_idx`), plus les transactions encore en cours au moment de la vérification. Le journal est en ajout seul et ses identifiants viennent d'une séquence sans cache de session : une validation dans la famille ajoute soit une ligne plus récente que la dernière visible, soit une ligne d'une transaction déjà en cours, retrouvée par `row_revision_transaction_idx`. Chaque relecture vérifie les deux en une requête et oublie les transactions terminées sans écriture dans la famille.
- **Repli sûr** : si la route lit une table sans journal (vue matérialisée, table hors `real_estate`/`evidence`, le journal lui-même), ou si une validation de la famille a eu lieu pendant la lecture, l'entrée garde l'instantané global d'avant. Une requête conditionnelle sans entrée en mémoire n'est validée que par un instantané global inchangé. Les ETag restent dérivés de l'instantané relevé avant la lecture : une nouvelle lecture donne toujours un nouvel ETag.
- **Tests** (`test_read_cache_postgis.py`) : une écriture dans une table journalisée non lue garde le corps et l'ETag ; une écriture dans la famille et une exclusion (`history_exclusion`, lue par l'annuaire des projets) l'invalident ; une transaction en cours lors de la mise en cache, validée ensuite avec un identifiant de journal plus ancien que la dernière ligne visible, l'invalide aussi (test vérifié par mutation).

Familles relevées sur la base locale le 26 octobre : tuiles de parcelles `real_estate.parcel` seule ; liste des parcelles `parcel`, `parcel_observation`, `parcel_source_alias`, `source`, `capture`, `ingestion_run`, `audit_event` ; `district-map` et `market-map` lisent aussi `capture` et `ingestion_run`. Ces deux tables de provenance reçoivent une ligne à chaque collecte planifiée : les tuiles gardent désormais leur cache entre les collectes, mais les lectures qui citent leurs captures sont encore relues après chacune. Affiner leur granularité (par source ou par jeu de données) est la tâche [A16](../tasks/A16.md).

### Tables de provenance validées par rejeu — 26 octobre 2026 (A16)

Mesure de départ (base locale, 24 heures) : `evidence.ingestion_run` reçoit 2 882 révisions, toutes de la source `walking-analysis` (une exécution par minute, ouverte puis close) ; `evidence.capture` une seule ; aucune autre table journalisée ne change. Avec A08 seul, chaque route qui cite ses captures (`district-map`, `market-map`, liste des parcelles) était donc relue environ toutes les 30 secondes pour une source qu'elle ne lit pas.

- **Version plus fine que la table, sans liste par route** : une version « par source » supposerait de savoir quelles sources une route lit, donc une déclaration à tenir à jour. À la place, chaque requête SQL de la route qui parcourt `capture` ou `ingestion_run` (relevé par `pg_stat_xact_user_tables`, requête par requête) est gardée avec ses paramètres et une empreinte SHA-256 de ses lignes. La granularité est celle des lignes réellement lues, y compris « le dernier run réussi d'un jeu de données ».
- **Rejeu** : quand une validation n'a touché que ces deux tables, un seul instantané `REPEATABLE READ, READ ONLY` vérifie que les autres tables de la famille n'ont pas changé, puis rejoue ces requêtes. Mêmes lignes : le corps et l'ETag sont gardés, et les versions de l'entrée avancent (le contrôle suivant ne rejoue plus rien). Les autres requêtes de la route ne lisent que des tables inchangées avec les mêmes arguments, puisque ces arguments viennent de lignes identiques. Lignes différentes : la route est relue.
- **Repli sûr** : un parcours de ces tables qui ne peut pas être attribué à une requête (curseur serveur qui lit entre deux requêtes, `executemany`) désactive le rejeu ; l'entrée est alors relue à la première écriture de sa famille, comme avec A08. Une exclusion (`history_exclusion`) ou toute autre table de la famille l'invalide toujours.
- **Correctif A08, écrivain au-dessus de l'horizon** : `pg_snapshot_xip` ne liste pas une transaction en cours dont l'identifiant est supérieur ou égal au `xmax` de l'instantané (aucune transaction plus récente n'était terminée). Si une transaction plus ancienne avait validé entre-temps un identifiant de journal plus grand, la validation tardive de cette écrivaine passait inaperçue. L'entrée garde donc cet horizon et chaque contrôle vérifie aussi tous les identifiants de transaction de l'horizon au `xmax` courant (au-delà de 100 000, l'entrée est simplement relue).
- **Tests** (`test_read_cache_postgis.py`) : une collecte d'une autre source garde le corps et l'ETag sans relancer la route ; un run de la source lue qui change de statut l'invalide ; une écrivaine de `ingestion_run` en cours lors de la mise en cache, validée après une collecte d'une autre source, l'invalide ; une exclusion l'invalide même avec des collectes en parallèle ; l'écrivaine au-dessus de l'horizon est détectée. Les deux derniers mécanismes ont été vérifiés par mutation (plage d'horizon vide, rejeu sans comparaison : les tests échouent).

Mesure après (API de cette branche sur la base locale partagée, lectures seules, 18 tours de lecture espacés de 20 secondes pendant que `walking-analysis` collectait chaque minute) :

| Lecture | Famille relevée | Requêtes rejouées | Première lecture | Avec A08 seul | Avec A16 |
| --- | --- | --- | --- | --- | --- |
| `district-map` | `capture`, `district_boundary_observation`, `history_exclusion`, `ingestion_run`, `public_context_snapshot` | 2 | 1,2 s | 6 relectures sur 18 | 0 relecture, 6 rejeux (au plus 0,14 s) |
| `market-map` | les mêmes + `adrec_index_observation`, `adrec_market_snapshot`, `adrec_sale_observation` | 9 | 2,2 s | 6 relectures sur 18 | 0 relecture, 6 rejeux (au plus 0,81 s) |
| liste des parcelles (Reem, `bbox`) | `audit_event`, `capture`, `ingestion_run`, `parcel`, `parcel_observation`, `parcel_source_alias`, `source` | 2 | 0,37 s | 6 relectures sur 18 | 0 relecture, 6 rejeux (au plus 0,30 s) |

Médiane de toutes les lectures servies : 2 ms. Le rejeu de `market-map` reste coûteux (neuf requêtes sur les ventes ADREC), mais il n'a lieu qu'une fois par collecte d'une autre source et sans calcul Python ni sérialisation ; le contrôle suivant, sans nouvelle collecte, ne rejoue rien.

## Ajouter une fonctionnalité sans dégrader la structure

- **Nouvelle lecture HTTP** : route dans `apps/api/src/property_platform/api/` sur un routeur `/preview` existant ou enregistré dans `router.py` (gardes communes automatiques), service dans `publication`, contrat régénéré, relais web de trois lignes avec `relayPreview`.
- **Nouvelle source** : protocole et import dans `evidence`, échec enregistré avec `mark_failed`, collecteur dans `apps/ingestion`, propriétaire documenté dans [REPOSITORY.md](REPOSITORY.md), puis horaire désactivé par défaut.
- **Nouvelle zone ou nouvel émirat** : suivre [UAE_COVERAGE.md](UAE_COVERAGE.md) ; aucune règle propre à une île dans le code partagé.
- **Nouvelle couche de carte** : données servies par zone et par zoom (tuiles dès le chantier 3), libellés dans les seize langues ([INTERNATIONALIZATION.md](INTERNATIONALIZATION.md)).
