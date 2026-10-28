# Sélection immobilière, environs et parcelles superposées

État du 16 octobre 2026. Le parcours est **carte → fiche courte → page projet complète**. Les bâtiments, lieux, rues et parcelles restent sélectionnables dans leur ordre de précision ; aucun zoom ne se produit au clic. La recherche générale et la grille de tous les bâtiments sont retirées de l’exploration. La recherche de projets/promoteurs reste dans l’annuaire ; le marché et le contexte gardent leurs propres filtres.

## Ce que voit le visiteur

La fiche projet résume le nom, le promoteur, la livraison annoncée et les types de logements disponibles dans les preuves. Un total de programme est intitulé « logements prévus », jamais « disponibles ». Le bouton de détails ouvre une vraie page `/[locale]/projects/[slug]`, avec les documents, équipements, informations d’achat et sources. Une photographie d’ambiance est signalée comme telle ; un lien média ne donne pas un droit de republication.

Sur une parcelle, un nom potentiel de projet/bâtiment provenant des rapprochements spatiaux enregistrés peut être affiché sur le plan, précédé de **≈**. À défaut, la carte affiche l’usage traduit quand il existe, sinon son texte original. Les noms apparaissent selon le zoom et la place disponible, pour ne pas couvrir toutes les rues. Le réglage **Names** commande aussi ces libellés ; les codes restent une couche séparée. Les titres ne renomment pas les parcelles SQL et ne créent aucun lien commercial accepté.

Les noms de lieux OSM restent ceux de leur source. Un café dans une grande parcelle n’en devient pas le projet. Un projet de l’annuaire sans localisation examinée ne reçoit pas de marqueur à partir du centre du quartier.

## Pourquoi école et centre de données au même endroit ?

La [couche officielle PLOT d’Onwani](https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/0) vérifiée le 16 octobre 2026 contient deux enregistrements distincts :

| Référence | Usage publié | Propriété publiée | Date d’approbation enregistrée |
|---|---|---|---|
| RT4_P22 | Schools | PERMANENT | 26 janvier 2024 |
| RT4_TMP4 | Data Center | TEMPORARY | 11 mai 2022 |

Les empreintes se superposent presque entièrement dans la base actuelle. Les deux portent « Not Constructed ». Ces champs décrivent les enregistrements publiés ; ils ne permettent pas d’affirmer ce qui est construit aujourd’hui, de trancher une validité juridique ni de déclarer une fiche remplacée par l’autre. La date d’approbation ne devient pas une date de publication connue.

La fiche signale donc la superposition, avec un volet de comparaison permettant de sélectionner l’autre référence et de lire ses attributs, sa source et ses dates. Cette règle est générale : aucune exception codée pour RT4. Les doublons déjà rapprochés et marqués `superseded_by` sont exclus ; les grands secteurs et périmètres parents ne sont pas assimilés à une contradiction cadastrale.

La requête retient au maximum huit autres parcelles, de la portée de collecte sélectionnée, dont l’intersection représente au moins **80 % de chaque empreinte**. Ce seuil sert uniquement à détecter des contours comparables ; il ne fusionne pas les identités et ne mesure pas une probabilité d’usage. Les surfaces en m² de la fiche conservent leur calcul géodésique habituel.

## Autour de ce lieu

L’ouverture du volet déclenche une lecture bornée de PostgreSQL/PostGIS, sans collecte externe. Elle propose jusqu’à trois lieux par catégorie :

- Éducation et crèches, y compris les universités recensées.
- Commerces et alimentation.
- Santé et pharmacies.
- Transports : stations ferroviaires et arrêts/gares de bus documentés.
- Parcs, plages et loisirs.
- Cafés et restaurants.
- Lieux de culte.

Le rayon est de **1 500 mètres à vol d’oiseau**. L’origine est le point enregistré d’un lieu, ou le centroïde de l’empreinte d’un bâtiment, d’une parcelle ou d’une rue. Ce n’est pas une entrée du bâtiment ni un itinéraire. Les rues proches gardent leur volet séparé et leur limite de 120 m depuis le centroïde cadastral. La carte ne promet ni temps de marche, ni accessibilité, horaires, qualité scolaire ou exhaustivité des équipements.

La proximité est limitée aux namespaces du territoire actif. Une éducation/commerce/santé n’est pas déduite du nom ; les tags d’origine conservés dans la capture sont interprétés par `publication/uses.py`, version **source-use-v2**, avec la même capture que la provenance. Chaque résultat possède sa source, son URL, sa date de collecte, d’ingestion et sa date d’édition/publication lorsqu’elle existe. Le lien du lieu ouvre la source ; son intitulé conserve la langue originale.

Le catalogue spatial fournit jusqu’à 400 candidats à moins de 1,5 km, après préfiltre GiST puis distance sphéroïdale exacte. La projection conserve au maximum 21 équipements, élimine les répétitions d’une même identité source et indique une troncature lorsqu’un budget de candidats est dépassé. Une réponse vide signifie « aucun lieu recensé dans ce rayon », jamais « aucun service n’existe ». Les objets absents ou inactifs ne reçoivent pas une localisation de secours.

## Données et pipelines

Les lieux sont stockés dans **`real_estate.place`**, les empreintes dans **`real_estate.building`**, les parcelles dans **`real_estate.parcel`**. Leurs captures et observations restent dans **`evidence.capture`**, **`evidence.map_observation`** et **`evidence.parcel_observation`**. Les sources et exécutions gardent les tables d’audit existantes. Les rapprochements de projets suivent [PROJECTS.md](PROJECTS.md).

Il n’y a pas de nouvelle table de « proximité » : distances et superpositions dépendent de la géométrie actuelle et sont calculées à la demande. Copier ces mêmes informations dans une seconde table créerait un risque de divergence. **Aucune migration SQL n’est ajoutée par ce lot** ; le contrat HTTP change de façon additive et est régénéré depuis Django.

Les déploiements Prefect **map-osm** et **saadiyat-map-osm** réutilisent le même protocole, avec des portées et reçus distincts. Le connecteur **district-map-v5** étend la requête bornée aux commerces, équipements sans nom, tourisme et transports. L’import conserve désormais les `shop`, `railway`, `highway=bus_stop` et `public_transport` pertinents comme lieux ; les bâtiments sans nom restent des empreintes, pas des milliers de nouveaux lieux génériques. Le protocole XML de secours utilise la même règle, version **osm-api-bootstrap-v2**. Les déploiements **reem-osm-bootstrap** et **saadiyat-osm-bootstrap** effectuent quatre requêtes vers l’API officielle OSM, sur des fenêtres enregistrées, uniquement sur demande d’opérateur. Ils ne possèdent aucun calendrier et ne contournent pas un quota Overpass automatiquement. Ils portent le total à 33 déploiements, sans changer les horaires existants.

Les captures existantes ne sont pas effacées. Une nouvelle exécution conserve les observations et crée ou actualise les identités par identifiant source ; une absence du dernier extrait n’est pas une preuve de démolition. Les calendriers déjà configurés dans l’interface Prefect restent inchangés. Il n’existe pas de pipeline déclenché par un clic de visiteur.

## Où modifier le code

Préfixe Windows : `C:\Users\Karim\Repositories\property-platform\`.

| Chemin depuis ce préfixe | Responsabilité |
|---|---|
| `apps/api/src/property_platform/modules/evidence/collection_profiles.py` | Périmètres et requêtes de collecte OSM |
| `apps/api/src/property_platform/modules/evidence/maps/map_sources.py` | Protocole et choix typé des lieux OSM |
| `apps/api/src/property_platform/modules/evidence/maps/map_import.py` | Réconciliation et observations auditées |
| `apps/api/src/property_platform/modules/catalog/map_queries.py` | Géométries, distances et superpositions bornées |
| `apps/api/src/property_platform/modules/publication/surroundings.py` | Catégories et provenances des environs |
| `apps/api/src/property_platform/modules/publication/preview.py` | Fiche de parcelle et alternatives superposées |
| `apps/api/src/property_platform/api/parcels.py` | Contrats et validation des lectures HTTP |
| `apps/web/src/features/atlas/surroundings.tsx` | Volet de proximité chargé à la demande |
| `apps/web/src/features/atlas/presentation.ts` | Noms potentiels et ordre de sélection |
| `apps/web/src/features/projects/map-summary.tsx` | Fiche courte et lien de dossier indépendant |
| `apps/web/src/features/projects/detail.tsx` | Dossier complet sur sa page |
| `apps/ingestion/src/property_platform_ingestion/registry.py` | Déploiements existants Reem et Saadiyat |

Le relais web accepte uniquement les types `parcel`, `building`, `place`, `street` et un UUID. L’API refuse les territoires non configurés et les accès hors prévisualisation locale. Les requêtes ont des budgets SQL de deux à trois secondes. Ni une URL amont libre, ni les attributs bruts, ni une identité d’opérateur ne sont transmis au navigateur. Le chargement tardif du voisinage n’alourdit pas la lecture initiale des parcelles.

Pour appliquer les images et lancer les deux imports, suivre le début de [DEVELOPMENT.md](DEVELOPMENT.md). Les tests de `test_surroundings_postgis.py` vérifient les véritables distances PostGIS, les deux usages superposés, les limites de résultats et les preuves. Les tests web vérifient les noms potentiels, l’absence de mutation des codes et la priorité de clic des objets précis.

## Vérification locale du 16 octobre 2026

Les deux premiers runs Overpass ont échoué avec HTTP 406/500 ; les données antérieures sont restées intactes. Les reprises officielles Prefect ont ensuite terminé : Reem a créé 287 objets et actualisé 5 objets, Saadiyat a créé 532 objets et actualisé 11 objets. Sept et vingt-huit observations ont été mises en quarantaine respectivement, sans réparation silencieuse. Le catalogue OSM actif compte alors 454 lieux sur Reem et 734 sur Saadiyat ; ce sont des lieux, pas des projets ni des logements disponibles.

Ces totaux sont un constat daté, pas des valeurs codées dans l’interface. Les nouveaux résultats sont lus depuis PostgreSQL par le même endpoint de proximité. Le détail de RT4_TMP4 renvoie RT4_P22 comme contour comparable, avec usage Schools et provenance, sans modifier son propre usage Data Center.

Les contrôles locaux passent : 341 tests API avec PostGIS réel, 122 tests d’ingestion Linux et 45 tests web. Contrats, frontières de modules, formatage et liens documentaires sont vérifiés. Le build standalone vérifie les seize langues et les pages réelles sont contrôlées pour 57 projets dans chacune de ces langues. Aucune migration de modèle n’est détectée.
