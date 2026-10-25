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

## Limites à afficher

- 10 m par pixel : une petite parcelle compte peu de pixels ; une parcelle de moins de 0,2 ha ne peut pas être mesurée.
- Un changement n'est pas un avancement ; une absence de changement n'est pas un arrêt (travaux intérieurs, finitions).
- Saison, poussière, ombres d'immeubles voisins et angle solaire modifient la réflectance.
- Une scène par mois au plus ; les dates affichées sont celles des prises de vue.

## Découpage

- **B06** : flow Prefect (scènes récentes par parcelle, fenêtres conservées en captures, mesures datées en base, journal des lignes, inventaire des pipelines).
- **B07** : présentation sur la fiche projet (signal daté, méthode et limites, jamais en pourcentage), 16 langues.
