# Outils cartographiques et simulation solaire — 20 octobre 2026

Explore et la carte locale des fiches projets partagent le menu **Outils** : recherche, distance, zone, accessibilité piétonne, comparaison et soleil. Le menu **Vue** conserve les fonds et bâtiments 2D/3D. Marché reste une page indépendante. Les textes sont fournis dans les seize langues, les panneaux suivent le sens de lecture et les mouvements respectent la préférence de réduction des animations.

## Présentation et calculs

`map-analysis.ts` possède la recherche sur les objets déjà chargés depuis la DB, la déduplication des projets par identité catalogue, les mesures géodésiques Turf et la sélection des points de projets dans une zone. La recherche ne prétend pas être un géocodeur mondial ; sa portée est annoncée. Les groupes de marqueurs comptent des projets uniques, jamais les commerces et entrées comme des projets supplémentaires. Le clic sur un groupe zoome, puis la sélection habituelle reprend.

`map-workbench.tsx` compose ces fonctions dans les deux cartes et suspend la sélection immobilière pendant le dessin. Cent points au maximum ; Entrée termine, Retour arrière annule le dernier point, Échap quitte l'outil. Les distances sont à vol d'oiseau ; seule l'accessibilité utilise le réseau piéton. Ces dessins et simulations sont des calculs temporaires de présentation, pas de nouvelles observations de source ni des modifications cadastrales.

`map-comparison.tsx` synchronise une seconde carte raster, découpée par un curseur. Le fond choisi couvre son côté entier, sans repli silencieux vers un autre fournisseur. Les crédits et le lien source restent visibles. Sentinel WorldCover propose des mosaïques annuelles 2020/2021 à 10 m, pas des prises de vue quotidiennes ni des détails de façade ; Esri ne fournit pas une date unique garantie pour toutes ses tuiles. Le relais/archivage existant conserve ses limites de droits. Deux canvas WebGL sont nécessaires quand la comparaison est active.

## Soleil

`solar.ts` utilise SunCalc 2.1.1 : azimut en degrés depuis le nord, sens horaire, et altitude au-dessus de l'horizon. Date et heure signifient toujours **Asia/Dubai / UTC+4**, indépendamment du téléphone. Les dates 2000–2099 sont contrôlées, avec rejet des jours impossibles. L'URL peut conserver `sunlight=1`, `sun=2026-10-20T12:00` et `shadows=1`, notamment lors du changement de langue.

L'éclairage MapLibre est ancré sur la carte, suit le soleil et revient à sa valeur initiale après désactivation. Une teinte de scène représente jour/nuit. Il s'agit d'un **rendu indicatif**, pas de lux, d'irradiance, de météo, d'exposition intérieure ou d'un diagnostic de façade.

Les ombres sont une projection sur terrain plat des seules empreintes du catalogue possédant une hauteur en mètres enregistrée. Elles ne réutilisent pas les hauteurs supposées à partir d'étages. Elles sont bornées à 300 bâtiments / 10 000 sommets, plafonnées à 3 km et cachées sous 5° d'altitude solaire. L'enveloppe convexe est approximative : elle ne modélise ni toitures, ni relief, ni occultations entre immeubles. Le compteur de bâtiments et cette limite sont affichés. Une zone sans hauteur publiée peut donc avoir zéro ombre malgré des volumes 3D visibles.

Sources : [SunCalc](https://github.com/mourner/suncalc/blob/master/README.md), [lumière MapLibre](https://maplibre.org/maplibre-style-spec/light/).

## Réseau piéton : DB → Prefect → moteur local

Les migrations `0025` et `0026` ajoutent quatre tables typées dans `evidence`, avec le journal PostgreSQL habituel :

| Table | Propriétaire Prefect | Contenu |
|---|---|---|
| `routing_graph` | `property-platform-routing-graph` | Empreinte, version moteur, capture manifeste et heure d'ingestion |
| `routing_graph_part` | Même flow | Capture immuable de chaque fragment, numéro et position d'octet |
| `walking_request` | `property-platform-walking-areas` | Origine, durée, création et dernier essai |
| `walking_area` | Même flow | Géométrie PostGIS, version du graphe, capture du résultat et heure d'ingestion |

Le collecteur HTTPS est limité au PBF GCC Geofabrik et à ses redirections datées sur le même domaine. La limite spécifique est 320 Mio / 300 secondes ; la limite générale des autres collecteurs n'est pas relevée. L'extrait régional est nécessaire faute de sous-extrait UAE dans ce catalogue. Sa licence est ODbL. L'archive est plafonnée à douze versions ; atteindre cette limite bloque une nouvelle version, sans supprimer les précédentes ni empêcher leur reconstruction.

Les **octets source sont en DB**, par captures d'au plus 4 Mio, liées à un manifeste. La reprise relit chaque fragment progressivement, contrôle numérotation, positions, longueur et SHA-256 global. Le mode `refresh=False` ne télécharge jamais de source : sans archive il échoue explicitement. Les dates d'acquisition initiales sont conservées lors de la reprise. Les fichiers PBF et graphes Valhalla du volume `routing-data` sont des copies de calcul reconstruisibles.

L'image officielle Valhalla est fixée par digest ; le moteur vérifié annonce `3.9.1-618cad5eb`. Son service privé n'a ni port hôte, ni accès à Docker, ni API de téléchargement. Il tourne sous UID 1000 avec 2 CPU / 4 Gio. Prefect fournit les fichiers archivés et lance le calcul ; aucun téléchargement ni calcul de graphe dans Django ou Next.js.

`GET /preview/accessibility` enregistre une origine arrondie à cinq décimales et une durée 5/10/15 minutes, puis renvoie 202 jusqu'au traitement. Le flow traite au plus dix demandes par passage, avec reprise après cinq minutes en cas d'échec ; la file est bornée à 5 000 origines/durées. La lecture conserve un ancien résultat si le nouveau graphe n'a pas encore de résultat utilisable et indique alors `historical`. Chaque résultat référence la capture et l'empreinte de son graphe. Ce sont des contours du réseau OSM, sans trafic, horaires de transport ni garantie de franchissement effectif de tout passage.

Le graphe est recalculé chaque mois. La file piétonne passe toutes les deux minutes, aux minutes impaires ; elle passait chaque minute jusqu'à [A26](../tasks/A26.md). Comme les autres nouveaux déploiements, leurs horaires initiaux sont inactifs jusqu'à activation opérateur ; un redémarrage respecte les horaires déjà modifiés. L'aperçu installé active la file et la cadence mensuelle. Lancer une collecte manuellement depuis Prefect : `routing-osm-graph` avec `refresh=True` ; reconstruire l'archive avec `refresh=False`.

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.map-analysis.yaml --profile ingestion --profile map-analysis up -d --build routing ingestion
```

Appliquer explicitement les migrations Django avant ce démarrage. Le démarrage de service ne migre pas la DB. L'API et le web utilisent leurs overlays habituels. Voir [INGESTION.md](INGESTION.md), [DATA_HISTORY.md](DATA_HISTORY.md), [documentation Valhalla](https://valhalla.github.io/valhalla/api/isochrone/api-reference/) et [Geofabrik GCC](https://download.geofabrik.de/asia/gcc-states.html).

## Marché par quartier

`publication/market_map.py` joint les ventes du snapshot ADREC sélectionné aux limites DMT archivées par nom normalisé exact et unique. Pas de rapprochement flou, de point inventé ou de déduplication de transactions : la multiplicité source est conservée. Le filtre projet et le snapshot historique sont communs à la liste et à la carte. Les limites sont celles actuellement archivées ; une ancienne période de ventes ne prétend pas disposer d'anciennes frontières.

Les volumes et nombres de ventes sont calculés sur le snapshot entier (plafond 50 000 lignes), pas sur sa première page. La médiane des taux AED/m² publiés est montrée à partir de cinq valeurs positives ; c'est une population mixte, pas une estimation de prix d'un logement. Les quartiers ambigus/absents sont comptabilisés sans carte. Le relevé local du 20 octobre donne 82 quartiers, 6 572 ventes cartographiées et 175 sans correspondance certaine. Le rendu est chargé seulement à l'ouverture du panneau Marché, avec légende de couleurs et liens ADREC/DMT.

## 3D détaillée et performance : décisions

Les volumes catalogue/OpenFreeMap et la vue satellite 3D restent les sources disponibles, voir [BUILDINGS_3D.md](BUILDINGS_3D.md). [MapLibre Landmarks](https://github.com/am2222/maplibre-landmarks) se déclare expérimental ; les modèles détaillés examinés dans Open Landmarks n'établissent pas de couverture exploitable d'Abu Dhabi. Aucun modèle étranger, faux jumeau numérique ou nouveau fournisseur payant n'est ajouté. Un futur modèle local doit avoir identité, localisation, droits de copie/publication et pipeline d'archivage avant activation.

[Martin](https://maplibre.org/martin/) reste une option pour une charge cartographique plus importante. Pré-mesure SQL locale sur la tuile 13/5334/3520, mêmes identités/code/usage des parcelles, neuf lectures dont la première écartée :

| Projection | Médiane SQL | Octets bruts | Octets gzip |
|---|---:|---:|---:|
| GeoJSON à six décimales | 20,91 ms | 1 451 625 | 292 322 |
| MVT PostGIS avec découpage 4096 + marge 64 | 29,89 ms | 248 412 | 138 732 |

Ce n'est pas un benchmark de Martin ni une mesure de latence navigateur : le MVT change aussi la précision et le découpage. Son gain de transfert est réel sur cet échantillon, son calcul n'est pas plus rapide ici. Les lectures actuelles étant bornées, aucun nouveau serveur de tuiles n'est déployé à ce stade. Une adoption future doit mesurer plusieurs zones, zooms, concurrents et appareils, puis exposer uniquement des vues de publication en lecture seule, jamais les tables d'audit autodécouvertes.

## Vérification

Les tests purs vérifient temps UAE, dates invalides, angles solaires, sens des ombres, hauteurs manquantes, identités de recherche/groupes et mesures. Les tests PostGIS vérifient fragments/reprise hors ligne, conservation des dates, journal, file piétonne, ancienne version et jointures Marché ambiguës. Les tests de collecteurs sont sans réseau ; ils vérifient redirections, budget et reconstruction SHA-256. Les contrôles du navigateur et les résultats de build sont consignés après installation de l'aperçu.

Validation locale du 20 octobre : **363 tests API sur PostGIS, 131 ingestion et 77 web réussis** ; Ruff/formatage, Biome, trois frontières Import Linter, contrat OpenAPI identique au backend installé, génération TypeScript, migrations sans changement et liens de 43 documents vérifiés. Les images API/ingestion/routage/web sont construites et installées ; le build web exécute aussi les contrôles HTTP des seize langues. Les horaires des deux nouveaux flows sont actifs, les contours sont réellement calculés et archivés et data-history confirme 49 tables couvertes, sans table oubliée.

Le navigateur confirme recherche → fiche The District, mesure de 214,8 m, zone contenant deux projets, contour piéton renvoyé par Prefect, comparaison Esri/plan, soleil matin/nuit, modification de date et d'heure, conservation en arabe et retour français, carte Marché par ventes/taux et panneau compact de la carte projet. Les contrôles de 390 × 844 pixels sont une émulation Chrome, pas une validation physique Android ; le viewport est ensuite restauré. Les crédits restent visibles et aucune erreur console n'est observée dans ces parcours. Les accès privés web/Prefect existants sont conservés, sans exposition publique.
