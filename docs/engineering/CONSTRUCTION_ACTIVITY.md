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

Table `evidence.construction_activity_measurement` (modèle `ConstructionActivityMeasurement`, migration `0035`), journalisée comme les autres tables de preuves et rattachée au flow `property-platform-construction-activity` dans `pipeline_inventory.py`. Une ligne par parcelle, paire de scènes et version de méthode ; une seconde lecture de la même paire garde la première mesure. Chaque ligne cite le projet, la parcelle, le lien d'identité relu qui place le projet sur cette parcelle, l'exécution, les captures des fenêtres des deux dates, la tuile MGRS, les identifiants et dates de prise de vue, puis les nombres de pixels, la part changée et le niveau. La base refuse une part hors de [0, 1], un niveau autre que `low`, `moderate` ou `high`, une date « après » qui ne suit pas la date « avant », et un niveau sur une mesure `insufficient_clear_pixels`.

Seuls les liens actifs vers une parcelle cadastrale courante sont mesurés (`activity_import.measurable_links`) : un point déclaré ou une emprise de bâtiment ne donne pas de limite de parcelle. Code : `apps/api/src/property_platform/modules/evidence/activity_import.py`.

## Limites à afficher

- 10 m par pixel : une petite parcelle compte peu de pixels ; une parcelle de moins de 0,2 ha ne peut pas être mesurée.
- Un changement n'est pas un avancement ; une absence de changement n'est pas un arrêt (travaux intérieurs, finitions).
- Saison, poussière, ombres d'immeubles voisins et angle solaire modifient la réflectance.
- Une scène par mois au plus ; les dates affichées sont celles des prises de vue.

## Découpage

- **B06** : flow Prefect (scènes récentes par parcelle, fenêtres conservées en captures, mesures datées en base, journal des lignes, inventaire des pipelines).
- **B07** : présentation sur la fiche projet (signal daté, méthode et limites, jamais en pourcentage), 16 langues.
