# Lisibilité de la carte et comparaison cadastrale — 22 octobre 2026

## Valeurs initiales

Explore conserve les projets, parcelles, rues, bâtiments, noms et équipements utiles.
Les commerces, cafés, restaurants, bureaux et lieux non classés sont désactivés dans
une option distincte « Commerces, cafés et services ». Les équipements apparaissent
au zoom 14,5, leurs noms au zoom 15. Les projets gardent leurs groupes et repères
indépendamment du réglage Lieux. Les cartes des fiches projets partagent ce filtre.
Les noms génériques d'usage cadastral et les suggestions de nom par parcelle restent
dans les fiches sans saturer le fond de carte. Les secteurs et codes sont facultatifs.

Sur le plan, l'eau passe au-dessus des surfaces **et** des contours cadastraux.
Un clic sur l'eau ne sélectionne plus une parcelle invisible. L'option « Limites
cadastrales en zone d'eau » restaure les contours et leur sélection. Sur satellite,
les limites restent consultables au-dessus de l'image. Les géométries stockées ne
sont jamais découpées, déplacées ou supprimées sur la seule foi du trait de côte OSM.
Un cadastre peut inclure un terrain futur, une marina ou un périmètre marin ; deux
sources de dates différentes peuvent aussi diverger. La légende signale cette limite.

**Parcelles sur l'eau cartographiée — 23 octobre 2026.** Le masquage complet coupait de
vraies parcelles : à Saadiyat, le polygone « océan » OSM couvre 240 parcelles du secteur
du Cultural District, dont 152 entièrement (villas prévues, parcs, postes électriques,
« non construits »), car le trait de côte OSM ne suit pas encore les terrains gagnés sur
la mer. L'eau couvre toujours les surfaces et contours pleins, mais deux couches
discrètes au-dessus (`parcel-water-fill`, teinte à 28 %, et `parcel-water-line`, contour
en pointillés) gardent ces parcelles lisibles et sélectionnables, sans peindre la mer.
Les périmètres de projet (`overlay`) restent invisibles et non sélectionnables sur
l'eau. Ces couches sont masquées sur satellite ; l'option « Limites cadastrales en zone
d'eau » remplace le pointillé par le contour plein.

## Source AD-SDI

Le connecteur utilise exclusivement la publication officielle
[Plots, couche 10](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/Pub/Generic_Search_WM/MapServer/10).
Les trois districts proviennent des profils examinés, sans URL ni clause SQL libre.
La métadonnée doit décrire des polygones WGS84 et le dictionnaire de sous-types
`PRIMARYUSEENG`. **2 = Commercial et 13 = Residential dans cette publication** :
ce ne sont pas les codes Onwani. Les usages originaux restent stockés ; la taxonomie
d'affichage `land-use-v3` reconnaît les familles générales sans inventer un équipement
précis. Aucun propriétaire, occupant ou contact personnel n'est collecté.

Chaque snapshot vérifie deux listes d'OBJECTID identiques et des lots complets de
100 objets. Les plafonds sont 8 Mio par réponse et 64 Mio par acquisition (256 Mio et
503 réponses pour un district de l'émirat, F05). Les
réponses et leurs empreintes sont conservées avec leurs horloges d'acquisition et
d'ingestion. `PLOTID` est l'identité source durable, distincte de l'OBJECTID technique.

La comparaison utilise PLOTID + municipalité + district, puis une intersection sur
union calculée en UTM 40N. À partir de 98 %, une observation SDI peut corroborer une
parcelle Onwani sans remplacer ses attributs plus riches. Une divergence, une identité
ambiguë ou des identifiants différents portant une géométrie presque identique sont
mis en quarantaine. Ils ne créent pas une fusion implicite. Un nouveau lot non ambigu
complète le catalogue sous son propre namespace SDI. Les absences dans un nouveau
snapshot n'effacent aucune parcelle historique.

## Propriétaires et exécution

`evidence/maps/sdi_protocol.py` possède le protocole pur et les sous-types ;
`evidence/maps/sdi_import.py` possède les captures, observations, quarantaines et mutations
via les services du catalogue. `ingestion/collectors/sdi.py` acquiert hors transaction
puis rejoue les mêmes réponses dans la passerelle durable. Direction : ingestion →
evidence → catalog ; publication lit les deux namespaces. Aucun nouveau schéma ou
modèle universel. Les écritures Onwani et SDI partagent le verrou parcellaire.

La migration additive `0030_sdi_parcels` étend les opérations autorisées, sans changer
les tables métier. Trois déploiements **manuels** portent le registre à 56 :

| Flow | Déploiement | Territoire |
| --- | --- | --- |
| property-platform-sdi-parcels | reem-parcels-adsdi | al-reem-island |
| property-platform-sdi-parcels | saadiyat-parcels-adsdi | saadiyat-island |
| property-platform-sdi-parcels | maryah-parcels-adsdi | al-maryah-island |

Reconstruire API et ingestion, appliquer explicitement la migration puis remplacer
les services ; reconstruire le web et rattacher le connecteur privé après son
remplacement. Les horaires antérieurs restent conservés. Exécuter les trois
déploiements depuis Prefect, avec `actor` identifiant l'opérateur. Le rebuild projet
optionnel `include_geography=true` appelle aussi SDI après Onwani ; il rapporte
séparément toute source indisponible. Une base neuve peut importer les parcelles via
ce même flow, après migrations. Les reçus SDI sont conservés dans la DB ; le rejeu
autonome hors ligne de ces reçus depuis un volume externe n'est pas encore fourni.
Ne pas confondre cela avec le rebuild hors ligne déjà disponible pour les projets.

## Qualification

Ce service public interrogable ne suffit pas à établir une licence commerciale de
republication. Cette intégration reste dans l'aperçu privé de recherche existant.
La fraîcheur et la position du littoral ne sont pas certifiées. Voir
[l'enquête](../product/ENQUETE_FONCIER_PERMIS_20261022.md) et ses limites.

La validation comprend les imports PostGIS, la conservation des preuves, le refus
des snapshots incomplets et des changements de dictionnaire, l'indépendance des
filtres de lieux et la validation des styles par MapLibre. Les résultats réels sont
consignés ci-dessous après les imports.

## Exécutions vérifiées

Le run Prefect `6ce63498-c0bf-4a7d-b1b6-84688e8d6509` a créé les 73 parcelles Maryah,
avec 4 captures et 73 observations. Le relais web les sert toutes avec le nom de
source AD-SDI et `classification_version=land-use-v3`.

Le run `72738c54-3900-4ff1-b546-dd3ed4945edb` a examiné 2 506 lots Reem :
83 créations, 2 416 correspondances géométriques cohérentes et 7 quarantaines,
dont 5 géométries divergentes à identifiant égal. Les formes Onwani sont préservées.
Reem contient ensuite 2 514 parcelles actives, contre 2 431 auparavant.

Le run `e8484735-e441-44bf-bac0-0d1da6b5d9c3` examine 5 456 lots Saadiyat :
292 créations, 4 987 correspondances cohérentes et 177 quarantaines, dont 10
géométries divergentes à identifiant égal. Saadiyat atteint 5 790 parcelles actives.
Au total : **448 ajouts**, **7 403 correspondances**, **184 quarantaines** et
**8 377 parcelles actives** sur les trois îles. Les trois snapshots représentent
91 captures et 7 851 observations acceptées ; les lignes écartées restent en preuve.
Les 184 quarantaines comprennent 167 géométries quasi identiques avec identifiants
différents, 15 géométries divergentes pour un même identifiant, 1 géométrie invalide
et 1 cas de recouvrements trop nombreux. Ce ne sont pas 184 parcelles supprimées.

Une cible PostGIS éphémère **distincte**, initialement sans parcelles, a exécuté
le même flow Prefect Maryah : `d13b592b-40c7-4e93-b7b4-b1d30104b923` crée 73 parcelles ;
`7991e5af-cd7e-48dd-9369-84f1197ba2ba` rejoue la collecte, crée zéro parcelle et en
confirme 73 inchangées. L'histoire atteint 8 captures et 146 observations, sans
doublon canonique. Cette preuve utilise la source en ligne, et non une archive hors
ligne, et porte sur ce nouveau connecteur, pas sur toute la base nationale.

Validation : 398 tests API complets sur PostGIS, puis 25 tests ciblés après extension
de la classification ; 179 tests ingestion, puis 6 ciblés après ajout au rebuild ;
94 tests web. Types et compilation Linux, smoke dans les 16 langues, Ruff, Biome et
liens documentaires passent. Les tests GIS et la preuve Prefect utilisent une base
isolée ; aucun test pytest ne cible la DB de la plateforme.

Le navigateur confirme les commerces réactivables, les projets sélectionnables
avec Lieux désactivé, la légende cohérente, le masque des contours à Reem Hills,
leur restauration par l'option marine et l'absence de sélection invisible sur
l'eau. Le contrôle d'inventaire ne trouve aucune table métier sans audit/pipeline.
Le site privé et l'API Prefect répondent HTTP 200 via Tailscale avec certificat TLS
vérifié ; le connecteur rejoint bien le nouvel espace réseau web.
