# Commerces et lieux utiles : Overture Places

## Ce que fait l’import

Les deux déploiements `reem-places-overture` et `saadiyat-places-overture` utilisent le flow existant `property-platform-map`, avec `layer=overture`. Ils complètent les lieux OpenStreetMap : commerces, cafés, restaurants, équipements et autres destinations nommées. Ils ne créent aucun lien automatique avec un projet immobilier ou un propriétaire.

Version examinée : **2026-09-23.1**, classification `taxonomy`. La version reste fixée : la parution d’un nouveau jeu nécessite une vérification du schéma et une modification revue du protocole, sans suivre aveuglément `latest`. Les horaires proposés sont dimanche 09:00 pour Reem et 09:30 pour Saadiyat, fuseau `Asia/Dubai`. Le registre initialise les nouveaux horaires inactifs ; l’opérateur peut les activer dans Prefect. Un redémarrage conserve les modifications faites dans l’UI.

## Où se trouvent le code et les données

Depuis `C:\Users\Karim\Repositories\property-platform` :

| Chemin | Rôle |
|---|---|
| `apps/ingestion/src/property_platform_ingestion/collectors/overture.py` | Téléchargement de l’index STAC, sélection des fragments, lecture filtrée en flux |
| `apps/api/src/property_platform/modules/evidence/maps/overture_protocol.py` | Release, enveloppes, limites, validation et classification sans réseau ni ORM |
| `apps/api/src/property_platform/modules/evidence/maps/overture_places.py` | Captures, contrôle du contour officiel et stockage Django |
| `apps/api/src/property_platform/modules/publication/place_display.py` | Suppression conservatrice des répétitions à l’affichage |
| `apps/web/src/features/atlas/imagery-sources.ts` | Registre des fournisseurs raster examinés |

| Table PostgreSQL | Contenu |
|---|---|
| `real_estate.place` | Identité GERS, nom original/arabe disponible, catégorie interprétée et point WKB original |
| `evidence.source` | Namespace indépendant `overture:reem:places` ou `overture:saadiyat:places` |
| `evidence.capture` | Extrait régional sérialisé, hash SHA-256, release, fichiers Parquet, hash de l’index et heures de collecte |
| `evidence.map_observation` | Attributs sélectionnés, provenance amont, licences, catégorie originale, action et révision |
| `evidence.ingestion_run` / `evidence.ingestion_execution` | Résultat, opérateur et association à l’exécution Prefect |
| `evidence.quarantined_observation` | Enregistrements invalides conservés sans réparation inventée |

La capture est un **extrait dérivé de fichiers Parquet**, pas une copie prétendue d’une réponse GeoJSON officielle. `acquisition_method=overture_parquet_extract` l’identifie. Le statut 200 indique une acquisition complète ; les dates sont celles du collecteur. La date de publication propre au lieu reste nulle lorsqu’elle n’est pas établie ; les dates amont restent dans les attributs originaux. Les fichiers mondiaux et géométries raster ne sont pas copiés dans PostgreSQL.

## Qualité et limites

- Acquisition limitée aux enveloppes enregistrées, puis vérification du point contre le contour officiel Onwani de chaque île. Les contours doivent être importés avant les lieux.
- Maximum 20 fragments, 10 000 lieux et 16 Mio d’extrait ; dépassement ou troncation fait échouer l’import, sans remplacer les données par un résultat partiel. Le sous-processus reste limité à 900 secondes.
- Seuil de confiance d’existence **0,8** : il filtre une partie du bruit, sans garantir que le nom, la catégorie ou l’ouverture sont corrects. Les lieux signalés fermés ne sont pas ajoutés par cet import.
- Le point original est conservé ; la bbox sert au filtrage, pas à inventer le centre du bâtiment.
- Même nom et même catégorie à moins de 15 m peuvent être masqués dans la carte/proximité lorsqu’une autre source existe. Les deux objets restent consultables en base. Deux succursales éloignées restent distinctes.
- L’absence dans un nouvel extrait n’est pas une preuve de fermeture : aucune suppression automatique, aucun `TRUNCATE`. Une fermeture d’un lieu déjà publié nécessite une décision de retrait auditée ; le connecteur ne supprime pas les anciens points par simple absence ou baisse de confiance.
- Overture est une source agrégée, affichée avec le niveau communautaire, jamais comme une preuve cadastrale officielle. Ses erreurs de classification ne sont pas corrigées en déduisant une activité depuis le nom.

## Exécuter et vérifier

Dans [Prefect local](http://localhost:4200), ouvrir Deployments puis l’un des deux noms, choisir Run et indiquer l’opérateur. Attendre le résultat avant de rafraîchir la carte. Le bilan indique créations, mises à jour, inchangés, exclusions et quarantaines. Les autres calendriers restent indépendants.

Les points alimentent les lectures existantes `/api/v1/preview/map-context` et les équipements à proximité, ainsi que les cartes de quartier des fiches projets. Les requêtes sont bornées ; aucune requête Overture, Google ou S3 ne part depuis le navigateur. Le contrat HTTP et les tables existants sont conservés : **aucune migration SQL n’est ajoutée**.

Pour consulter les lieux dans l’outil SQL :

```sql
SELECT source_namespace, kind, COUNT(*)
FROM real_estate.place
WHERE source_namespace LIKE 'overture:%' AND active
GROUP BY source_namespace, kind
ORDER BY source_namespace, COUNT(*) DESC;
```

## Imagerie satellite

Le fond Esri existant reste le défaut du mode satellite. Les parcelles et bâtiments sont rendus plus transparents pour laisser voir la photographie. Le registre raster permet de changer de fournisseur sans modifier les données métier. Les 24 niveaux déclarés par Esri ne signifient pas que les photos ont une résolution centimétrique sur les deux îles.

Une comparaison de tuiles Esri et de l’archive Wayback du 5 août 2026 a été tentée : Esri répond, Wayback refuse les tuiles HTTP ici. Aucun choix défectueux n’est ajouté au site. Les aperçus Sentinel-2 restent à **10 m/pixel**, même agrandis ; ils servent au contexte et à l’historique. Aucun abonnement ou clé Google/MapTiler n’est créé pour cet ajout. Une meilleure imagerie doit être vérifiée localement avec ses droits, sa date réelle d’acquisition et son coût.

Sources : [Overture Places](https://docs.overturemaps.org/guides/places/), [client Python et index STAC officiels](https://github.com/OvertureMaps/overturemaps-py), [licences et attribution](https://docs.overturemaps.org/attribution/), [Sentinel-2](https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel2.html), [Esri Wayback](https://www.esri.com/arcgis-blog/products/arcgis-living-atlas/mapping/use-world-imagery-wayback).

## Résultat vérifié sur le poste Karim

Le 17 octobre 2026, les imports Prefect [Reem](http://localhost:4200/runs/flow-run/1458513c-b739-4954-83c6-1769436838f5) et [Saadiyat](http://localhost:4200/runs/flow-run/6b66684f-28ea-4b82-96d7-cd6bb28c5fae) ont terminé avec succès : **211 et 113 lieux créés**, aucune quarantaine. Les captures contiennent respectivement 805 et 1 144 candidats ; les autres sont exclus par la confiance, les statuts ou le contour officiel. Les lectures HTTP affichent 210 et 111 points Overture après suppression de trois répétitions intersources ; les 324 identités restent en base. Les volets de proximité répondent sur les deux îles. Ce sont des lieux complémentaires, pas 324 nouveaux projets immobiliers.

Les deux calendriers sont activés dimanche à 09:00 et 09:30, heure de Dubaï. Le PC, Docker et le runner doivent fonctionner à cette heure. La suite complète vérifie 350 tests API sur PostGIS, 125 tests ingestion et 50 tests web ; quatre tests PostGIS ciblés ont aussi été rejoués après le bilan final. Typage et smoke standalone passent dans le build Linux pour les seize langues. Le typage natif Windows a rencontré le problème de cache SWC connu ; le contrôle équivalent a réussi dans Linux. Aucune migration manquante.

Le contrôle navigateur final confirme les lieux sur Reem et Saadiyat, les crédits compacts, Esri sélectionné par défaut en satellite et le contraste du bouton actif au survol (fond sombre, texte blanc). Les captures de validation restent sous .cache/validation/, hors Git.
