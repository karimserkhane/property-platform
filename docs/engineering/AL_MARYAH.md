# Al Maryah Island — 22 octobre 2026

## Périmètre et sources

`al-maryah-island` possède un profil distinct, préfixe `maryah`. Le district
Onwani examiné est **AL MARYAH ISLAND**, identifiant **74**. Ses limites viennent
de la couche officielle ; les enveloppes de navigation ne sont pas cadastrales.
Cet identifiant Onwani n'est pas un identifiant du registre de projets ADREC.

Neuf fiches sont enregistrées : Al Maryah Vista 1 et 2, W Residences, St. Regis,
Ritz-Carlton, Jumeirah, Four Seasons Private Residences, Rosewood Residences et
One&Only Private Residences. Le catalogue contient 183 fiches nommées au total,
dont programmes, résidences et phases, sans garantie d'exhaustivité.

Les sources examinées viennent de Reportage, Taraf, SAAS et ses sites dédiés,
Emirates Developments, Four Seasons et Mubadala. PSI reste une source d'agence.
URLs, rôles, alias et raisons de revue sont dans `evidence/project_registry.json`.
Les catalogues PSI et SAAS gardent les candidats sans créer automatiquement des
identités. L'article de marque Jumeirah indisponible pour le collecteur reste une
piste de revue, séparée des sources actives et des faits servis au public.

La page Vista 1 reprend le point de Vista 2 : ce point est exclu. Les fiches sans
emplacement justifiable restent dans l'annuaire sans point artificiel. Le PDF
Stellar by Elie Saab du pied de page Jumeirah est exclu avec une raison durable.
`project_maryah.py` complète seulement des couples projet/URL exacts et distingue
les **124 résidences Four Seasons des 200 chambres d'hôtel**. Aucun prix, statut
livré ou croisement implicite type/chambres n'est inventé.

## Pipelines et histoire

Onze déploiements s'ajoutent aux 42 précédents : `maryah-parcels-onwani`,
`maryah-map-district`, `maryah-map-community`, `maryah-map-street`, `maryah-map-osm`,
`maryah-osm-bootstrap`, `maryah-places-overture`, `maryah-project-references`,
`maryah-project-details`, `maryah-project-discovery`, `adrec-maryah-sales`.
Le district public des ventes est exactement « Al Maryah Island ».

Les nouveaux calendriers sont initialement inactifs, selon la règle commune ;
leur état effectif est visible dans Prefect. Les calendriers existants sont
conservés et le runner reste limité à un traitement. Références, présentations
et photos Maryah ont des registres initiaux vides ; aucune donnée Reem n'est
recyclée. Les fonds archivés et le rebuild géographique couvrent les trois îles.

Les imports utilisent le gateway audité, les captures, les snapshots typés et le
journal PostgreSQL existants. Les dates d'acquisition et d'ingestion restent
distinctes. Les projections récupèrent les anciens champs non vides sans effacer
les preuves d'une source disparue. Les échecs restent des exécutions en échec.

Le flow `property-platform-project-rebuild` accepte le paramètre facultatif
`territory` : `null` conserve les trois îles ; `al-maryah-island` limite fiches,
catalogues et géographie optionnelle à Maryah. La cible `DATABASE_URL` doit être
une base PostGIS distincte sans projets. Le flow applique les migrations et refuse
une cible peuplée, sans la vider. Pour un rejeu sans sites d'origine :
`mode=archive`, `include_geography=false`, `include_catalogues=true`,
`territory=al-maryah-island`, avec le volume privé d'ingestion sauvegardé et le
serveur Prefect configuré. Voir [la reconstruction](PROJECT_CATALOGUE.md).
Cette preuve concerne les fiches et catalogues ; les couches GIS, ventes, graphes
et tuiles nécessitent leurs pipelines et archives propres.

## Couverture et limites

La couche PLOT publique Onwani ne renvoie actuellement aucun objet pour le filtre
Maryah examiné ; la requête spatiale contrôlée est aussi vide. L'import reste en
échec explicite plutôt que d'inventer des parcelles ou vider un catalogue existant.
Les districts, secteurs, rues et bâtiments sont indépendants et restent affichables.
Cela ne signifie pas que l'île ne possède pas de parcelles cadastrales.

**Recherche complémentaire du 22 octobre :** une autre publication officielle,
AD-SDI `Pub/Generic_Search_WM/MapServer/10`, a renvoyé 73 objets Maryah avec
73 `PLOTID` distincts et leurs polygones. Cette découverte ne change pas le résultat
du test Onwani ci-dessus. Classification/licence, fraîcheur, réconciliation et
nouvel import Prefect ont ensuite été examinés : les 73 parcelles sont maintenant
servies dans l'aperçu privé avec captures et audit. Les droits de republication
commerciale et la fraîcheur restent à établir. Voir [la comparaison](MAP_DATA_QUALITY.md).
Voir [l'enquête et ses preuves techniques](../product/ENQUETE_FONCIER_PERMIS_20261022.md).

Les points d'agence ne certifient ni propriété ni limites de programme. Les fichiers
externes restent des références sans licence implicite de republication.

## Repères et légende

`atlas/map-markers.ts` projette `use_types` puis les types source exacts vers des
formes, couleurs et pictogrammes locaux partagés par MapLibre et la légende.
Les noms et la proximité ne changent aucune identité. Les projets ont un losange
cuivre ; les groupes comptent uniquement des projets distincts. Les lieux
secondaires utiles apparaissent à partir du zoom 14,5, leurs noms au zoom 15,
avec collisions gérées. Les commerces et cafés sont facultatifs et masqués au départ.

Explore et les cartes de quartier partagent `map-legend.tsx` : catégories présentes,
usages parcellaires repliables et filtrables, hauteurs 3D séparées. La légende reste
disponible sans parcelles, se ferme par Échap avec reprise du focus et respecte le
conteneur et le RTL. Les crédits restent accessibles dans le contrôle compact.

## Résultats vérifiés

Les imports réels ont créé 1 district, 24 secteurs, 84 rues (Onwani et OSM),
36 bâtiments OSM, 81 lieux OSM et 233 lieux Overture. Le snapshot ADREC Maryah
contient 150 ventes du 24 juillet au 21 octobre 2026. Neuf projets sont servis,
quatre avec localisation déclarée d'agence et cinq en attente de point fiable.

Le run Prefect `87144870-b6b8-46f2-ab5e-b104a1febc18` (`realistic-echidna`)
a reconstruit la base neuve `property_platform_maryah_rebuild_20261022` avec
15 portées de sources, 16 versions de fiches et 3 versions de catalogues,
sans source manquante ni échouée et sans collecte aux sites d'origine.
Le run `61ed23b6-d84b-4bd0-ae32-07296125a5b2` a ensuite réconcilié l'histoire
Maryah du site, notamment une capture Jumeirah acquise avant un échec corrigé.

Comparaison en lecture seule, hors IDs techniques et nouveaux instants d'ingestion :

| Ensemble | Éléments dans chaque base | Différences |
| --- | ---: | ---: |
| Identités de projets et promoteurs | 9 | 0 |
| Preuves, URLs, empreintes et dates d'acquisition | 16 | 0 |
| Snapshots de faits typés avec provenance | 16 | 0 |
| Observations de typologies avec provenance | 24 | 0 |
| Observations d'équipements avec provenance | 6 | 0 |

Empreinte des preuves : `1f0f0bfe20c3ce45ab40cf69b433c28824586c427814681413122a31a67b7e3c`.
Empreinte des faits : `d84e430a8f34b2a85ac984704b7c850fc3a6921f131f1bf98fe9cf6dc3b870fc`.
La comparaison ne prétend pas reconstruire les couches géographiques du site.

Validation : 392 tests API sur PostGIS, puis 14 tests PostGIS ciblés après ajout
de l'isolation Maryah ; 175 tests ingestion et 93 tests web. Types, contrats,
frontières de modules, format et liens vérifiés. Le web compilé passe son smoke
dans les 16 langues. Le contrôle des données servies passe sur les 183 contrats,
549 dossiers (anglais, français, arabe) et leurs pages d'annuaire. Le navigateur
confirme le filtre Maryah, le parcours annuaire → carte et la légende mobile en
français/arabe, sans débordement horizontal à 390 pixels.

Le contrôle Prefect d'histoire `7e52bb31-1343-47fe-981d-2753ac1056e1` confirme
49 tables couvertes, aucune sans propriétaire de pipeline/audit. L'exception
existante d'archivage permanent Esri reste explicite, faute de droits établis.
Les relais web du marché et de sa carte retournent chacun les 150 ventes Maryah.
