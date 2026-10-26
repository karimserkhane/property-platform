# Indice d'activité de chantier par satellite (B06, B07)

Signal indépendant de l'avancement déclaré : a-t-on observé un **changement au sol** sur la parcelle d'un projet entre deux dates ? Ce n'est jamais un pourcentage d'avancement. Un pixel Sentinel-2 mesure 10 m × 10 m : il ne compte pas les étages, et un changement peut être un terrassement, un stockage de matériaux, une démolition ou un aménagement paysager.

## Source

[Copernicus Sentinel-2 L2A](https://registry.opendata.aws/sentinel-2-l2a-cogs/), servi en Cloud Optimized GeoTIFF par le registre ouvert AWS et indexé par le STAC [Earth Search](https://earth-search.aws.element84.com/v1) d'Element 84 : gratuit, sans compte ni clé. L'imagerie de Reem (`imagery_import.py`) lit déjà cette source. Les données Copernicus sont libres d'usage avec attribution (« Contient des données Copernicus Sentinel modifiées »).

## Méthode `sentinel-activity-v1`

Code : `apps/ingestion/src/property_platform_ingestion/collectors/sentinel_activity.py`.

1. **Scènes.** Items STAC `sentinel-2-l2a` vérifiés (identifiant, date avec fuseau, couverture nuageuse, tuile MGRS, fichiers sur `sentinel-cogs`, échelle et décalage de réflectance). Par tuile MGRS et par mois civil, on garde la scène la moins nuageuse sous 20 % ; aucune scène plus nuageuse n'est retenue par défaut.
2. **Fenêtres.** Pour chaque parcelle, bandes 10 m B02, B03, B04, B08 et classification de scène SCL (20 m, rééchantillonnée au plus proche sur la grille 10 m), sur l'emprise de la parcelle. Les nombres numériques sont convertis en réflectance (`valeur × échelle + décalage`, 0 = absence de donnée).
3. **Pixels clairs.** Un pixel compte s'il est dans la parcelle et classé végétation, sol nu, eau ou non classé (SCL 4 à 7) **aux deux dates**. Nuages, ombres, cirrus, saturation, zones sombres et absence de donnée sont exclus.
4. **Mesure.** Il faut au moins 20 pixels clairs et 60 % de la parcelle ; sinon l'état est `insufficient_clear_pixels` et aucun niveau n'est donné. Un pixel a changé si la différence absolue moyenne de réflectance sur les quatre bandes dépasse 0,05. Le résultat conserve les nombres de pixels (parcelle, clairs, changés), la part de pixels changés, la différence médiane et un niveau : `low` (≤ 10 %), `moderate` (≤ 30 %), `high` (au-delà).

Les seuils sont des choix heuristiques de la version 1, non calibrés sur des chantiers vérifiés. Toute modification change `METHOD_VERSION` ; les anciennes mesures restent attachées à leur version.

## Acquisition

Code : `apps/ingestion/src/property_platform_ingestion/collectors/sentinel_windows.py`.

- **Recherche.** `GET https://earth-search.aws.element84.com/v1/search` (collection, emprise WGS84, six mois avant la date de fin, 100 items par page) par `SourceHTTP` : chaque page est une acquisition avec son reçu. Earth Search donne un lien « page suivante » même après le dernier item ; le total `numberMatched` décide de la complétude. Une recherche incomplète, répétée ou au-delà de 5 pages échoue au lieu d'être tronquée. Six mois sur une petite emprise de Reem couvrent deux tuiles MGRS (`39RZH`, `40RBN`) et 187 items, en deux pages (3,9 Mo).
- **Paires.** Les scènes retenues (une par tuile et par mois) sont comparées deux à deux dans l'ordre chronologique, sur la même tuile.
- **Fenêtres.** Rasterio lit chaque fichier par un objet fichier Python : blocs alignés de 64 Kio, demandés en plages HTTPS (`206` obligatoire, encodage `identity`), conservés pour la session car GDAL relit souvent l'en-tête. Budgets : 8 Mio par requête, 32 Mio par fichier, 512 Mio par session. La fenêtre est l'emprise de la parcelle sur la grille 10 m de B04, au plus 256 × 256 pixels ; une parcelle hors de la tuile ou plus grande est refusée. SCL (20 m) est rééchantillonnée au plus proche sur cette grille.
- **Capture.** Une fenêtre est encodée en JSON déterministe (`sentinel-activity-window-v1`) : scène, tuile, date de prise de vue, système de coordonnées, transformation, fichiers sources avec échelle et décalage, puis les nombres numériques d'origine (`uint16`, SCL `uint8`) en base64. Le rejeu décode la capture en réflectance et recalcule le masque de la parcelle (centre du pixel dans la parcelle) ; aucun réseau n'est nécessaire.

Essai réel du 25 octobre 2026 (carré de 300 m à Reem, tuile `40RBN`) : 19 requêtes, environ 11 s et 6,7 Mo par scène pour une fenêtre de 32 × 34 pixels (capture de 15 Ko). Août → septembre 2026 : 42 % de pixels changés (`high`) avec une différence médiane de 0,043 ; septembre → octobre : 4,5 % (`low`). L'écart d'août tient probablement à la saison et à l'atmosphère autant qu'au sol : c'est une limite connue des seuils non calibrés de la version 1, à revoir avant tout changement de `METHOD_VERSION`.

## Stockage

Table `evidence.construction_activity_measurement` (modèle `ConstructionActivityMeasurement`, migration `0035`), journalisée comme les autres tables de preuves et rattachée au flow `property-platform-construction-activity` dans `history/pipeline_inventory.py`. Une ligne par projet, parcelle, paire de scènes et version de méthode ; une seconde lecture de la même paire garde la première mesure. Chaque ligne cite le projet, la parcelle et sa surface géodésique (`parcel_area_m2`), la base de la zone (`area_basis`), la méthode de position d'A02 (`position_method`), le lien d'identité relu qui la justifie, l'exécution, les captures des fenêtres des deux dates, la tuile MGRS, les identifiants et dates de prise de vue, puis les nombres de pixels, la part changée et le niveau. La base refuse une part hors de [0, 1], un niveau autre que `low`, `moderate` ou `high`, une date « après » qui ne suit pas la date « avant », un niveau sur une mesure `insufficient_clear_pixels`, et une parcelle déduite hors de 0,2 à 10 ha ou d'une autre méthode que `authority_point` ou `building_footprint`.

### Parcelles mesurées (décision de Karim du 26 octobre 2026)

`activity_import.measurement_targets` choisit les parcelles, dans l'ordre des liens d'identité :

1. **`reviewed_parcel`** : un lien relu actif relie le projet à une parcelle cadastrale courante (`position_method = cadastral_parcel`). Il l'emporte toujours : un projet qui en a un n'est jamais mesuré sur une parcelle déduite.
2. **`parcel_containing_position`** : sinon, la parcelle courante **unique** qui contient la position relue du projet, si cette position est fiable selon A02 — point de l'autorité (`authority_point`, coordonnées du registre) ou emprise de bâtiment (`building_footprint`, point intérieur de l'emprise) — et si la parcelle fait **de 0,2 à 10 ha** (surface géodésique PostGIS).

Ne sont jamais mesurés sans lien de parcelle relu : les points de courtier, d'éditeur ou déclarés ; une position sur une limite commune à deux parcelles ou hors de toute parcelle ; une parcelle de moins de 0,2 ha (trop peu de pixels) ou de plus de 10 ha (plan d'ensemble). Ces projets attendent un lien relu. Une mesure déduite reste une mesure de la parcelle, pas du projet : B07 doit afficher sa base (« parcelle qui contient le point du registre »). Code : `apps/api/src/property_platform/modules/evidence/activity_import.py`.

## Exécution

Flow Prefect `property-platform-construction-activity`, déploiement `construction-activity` (paramètre `territory` : `all` ou un territoire enregistré), horaire `0 4 5 * *` (Asia/Dubai) enregistré **inactif**. L'opération de domaine `construction_activity` ouvre un `ActivityCollector` (`collectors/sentinel_measure.py`) et appelle `activity_import.measure_activity` :

1. Exécution `IngestionRun` sur la source `sentinel-2-l2a-earth-search`, sous le verrou consultatif `8473303` (une seule mesure à la fois).
2. Une seule recherche sur l'emprise de toutes les parcelles retenues ; chaque page est une capture.
3. Par tuile, la paire des deux dernières scènes retenues ; la paire la plus récente d'abord, si bien qu'une parcelle dans le recouvrement de deux tuiles n'est mesurée qu'une fois.
4. Par projet et parcelle : une mesure déjà enregistrée pour cette paire et cette version arrête la parcelle (`existing`) ; sinon les deux fenêtres sont lues puis capturées (`sentinel_cog_window_ranges`, statut HTTP 206, capture parente = page de recherche qui listait la scène), et le signal est recalculé depuis les octets capturés (`replay_signal`), jamais depuis la mémoire de lecture. Une parcelle illisible sur la tuile (hors tuile, trop grande) passe à la paire suivante, puis compte `unreadable`.
5. Au plus 20 nouvelles mesures par exécution (`deferred` au-delà) ; l'exécution suivante reprend. Une erreur de transport ou de budget sur une parcelle compte `failed` et l'exécution finit `quarantined` ; les captures déjà reçues restent.

Chaque exécution mensuelle ajoute la paire la plus récente ; l'historique se construit donc mois après mois, sans relire les mois passés.

**Constat du 25 octobre 2026 (base locale, lecture seule).** Aucun des 156 liens d'identité actifs ne vise une parcelle : 151 visent un lieu (point) et 5 un bâtiment. Le flow ne mesure donc encore rien. Le point relu d'un projet tombe dans exactement une parcelle courante pour 116 liens (108 projets) ; 23 points tombent dans plusieurs parcelles et 12 dans aucune ; parmi les 116, quatre parcelles font moins de 0,2 ha et plusieurs dépassent 14 ha (plans d'ensemble). Karim a choisi le 26 octobre la règle ci-dessus ([B06](../tasks/B06.md)) : elle retient aujourd'hui **7 projets sur 7 parcelles** (5 liens à un point du registre, 4 à une emprise de bâtiment, certains pour le même projet). Les 67 points de courtier qui tombent dans une seule parcelle de 0,2 à 10 ha restent exclus.

## Rejeu dans le contrôle de reconstruction

Le contrôle `rebuild-check` ([REBUILD.md](REBUILD.md#mesures-dactivité-de-chantier-b06)) refait chaque mesure sans réseau :

- **Export.** Une étape `construction_activity` par exécution réussie ou en quarantaine de la source `sentinel-2-l2a-earth-search` : toutes ses captures (pages de recherche puis fenêtres, chacune avec l'indice de sa capture parente) et, pour chaque mesure, le projet (slug), la parcelle (espace de noms et identifiant source), les captures des deux dates et les valeurs à reproduire (base de surface, méthode de position, surface, tuile, scènes, dates de prise de vue, version de méthode, pixels, part, différence médiane, niveau).
- **Rejeu.** Après les fiches projet et leurs liens, une nouvelle exécution recrée les captures depuis leurs octets vérifiés ; la parcelle doit être une cible de `measurement_targets` dans la base reconstruite **pour la même raison** ; le signal est recalculé par `replay_signal` de l'ingestion depuis les deux fenêtres, puis enregistré par `record_measurement`. Les valeurs relues en base (décimales arrondies) doivent être identiques ; sinon l'étape échoue avec le détail `measurements` (attendu, obtenu, ou `not_a_measurement_target`). Rien n'est recopié de la base de référence.
- L'API ne lit jamais de raster : le worker de reconstruction (ingestion) fournit `replay_signal` à `replay_archive(..., activity_signal=...)` ; sans lui, l'étape échoue.

## Limites à afficher

- 10 m par pixel : une petite parcelle compte peu de pixels ; une parcelle de moins de 0,2 ha ne peut pas être mesurée.
- Un changement n'est pas un avancement ; une absence de changement n'est pas un arrêt (travaux intérieurs, finitions).
- Saison, poussière, ombres d'immeubles voisins et angle solaire modifient la réflectance.
- Une scène par mois au plus ; les dates affichées sont celles des prises de vue.

## Fiche projet (B07)

Section « Changement au sol vu par satellite » de la fiche projet, après la vérification ; lecture seule par `evidence.activity_sheet.project_activity` (une requête), champ `construction_activity` de `GET /api/v1/preview/projects/{slug}`.

- **Une carte par parcelle mesurée**, avec sa dernière mesure (paire de scènes la plus récente) tant que le lien d'identité relu qui la justifie est actif : niveau (`low`, `moderate`, `high` → « peu de changement », « changement modéré », « changement marqué »), dates des deux prises de vue, pixels clairs sur pixels de la parcelle, raison du choix de la parcelle (lien relu, point du registre, emprise de bâtiment), surface au moment de la mesure. Une parcelle déduite d'une position le dit : le signal décrit toute la parcelle.
- **Jamais de pourcentage.** L'API n'expose ni la part de pixels changés, ni leur nombre, ni la différence médiane : seulement le niveau. Les identifiants des scènes, la version de méthode et les fenêtres capturées (adresse et empreinte SHA-256) sont dans un bloc dépliable.
- **Mesure impossible** (`insufficient_clear_pixels`) : « mesure impossible : trop peu de pixels clairs (nuages, ombres, ou parcelle trop petite) », sans niveau. Un statut ou un niveau inconnu, ou une base incohérente, n'est pas affiché.
- **Aucune mesure** : la section dit qu'il n'y a pas encore de mesure et rappelle la règle de choix des parcelles (lien relu, ou point du registre ou emprise de bâtiment dans une seule parcelle de 0,2 à 10 ha) et le rythme mensuel. Les parcelles cibles sans mesure ne sont pas listées : les calculer coûterait plusieurs requêtes géographiques à chaque fiche.
- **Méthode et limites** (bloc dépliable) : comparaison pixel par pixel avec masque nuages et ombres, seuils non calibrés, les quatre limites ci-dessus, source Copernicus Sentinel-2 L2A (Earth Search) et attribution « Contient des données Copernicus Sentinel modifiées ». Messages `Activity` en 16 langues ; identifiants en `<bdi dir="ltr">` pour l'arabe, l'ourdou et le persan.

Code web : `apps/web/src/features/projects/activity.ts` et `construction-activity.tsx`. Tests : `test_activity_sheet_postgis.py`, `tests/activity.test.mjs`, parcours `e2e/projects.spec.ts` (anglais et arabe).

## Découpage

- **B06** : flow Prefect (scènes récentes par parcelle, fenêtres conservées en captures, mesures datées en base, journal des lignes, inventaire des pipelines).
- **B07** : présentation sur la fiche projet (signal daté, méthode et limites, jamais en pourcentage), 16 langues.
