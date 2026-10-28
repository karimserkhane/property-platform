# Vues de bâtiments en 3D

## Options disponibles

Dans **Vue**, choisir le fond plan ou satellite, puis **Bâtiments 3D**. Deux sources de bâtiments fonctionnent sur chacun des fonds existants :

- **OpenStreetMap · mondial** : volumes du thème `building` OpenMapTiles servi par OpenFreeMap. Couverture et hauteurs variables ; `render_height` peut être calculé par le fournisseur. Un clic affiche une hauteur indicative et l’attribution, sans créer d’identité catalogue ni d’association à un projet voisin.
- **Base de la plateforme** : contours déjà archivés. Vert signifie hauteur renseignée, sans promesse de mesure officielle. Sable signifie estimation d’affichage : étages × 3 m, ou volume minimal de 3 m en l’absence de hauteur/étages. **Afficher les hauteurs estimées** permet de les retirer. Ces estimations ne sont jamais écrites dans le catalogue et ne prouvent pas l’état de construction.

Une seule source de bâtiments 3D est visible à la fois. La 2D reste le défaut ; la 3D incline la caméra à 55° et rapproche la vue au minimum au zoom 15, sans dézoomer un projet déjà cadré. Le retour 2D remet la caméra à plat et au nord. Deux doigts sur téléphone ou le bouton droit glissé sur ordinateur permettent rotation et inclinaison. Le mouvement réduit est respecté.

La sélection d’un projet reste prioritaire devant les bâtiments et parcelles. Un toit 3D du catalogue ouvre le même identifiant que son contour 2D. Explore conserve les paramètres fermés `view`, `buildings3d`, `estimates` et `basemap` lors des changements de territoire/langue. La carte des pages projets possède les mêmes commandes, chargées à son activation.

## Archive et provenance

La source vectorielle déjà appelée `hydrography` contient aussi le thème `building`. Les volumes mondiaux lisent **les mêmes tuiles originales conservées en base** par `basemap-openfreemap`, via le protocole `archive://`. Aucun second accès direct au fournisseur. Heures d’acquisition, versions, empreintes et journal suivent [DATA_HISTORY.md](DATA_HISTORY.md). La limite conservatrice OpenFreeMap reste 3 000 versions / 50 Mo. Le fond Esri conserve son exception d’archivage documentée.

La source catalogue réutilise les imports OSM existants et leurs observations historiques. Aucune donnée distante nouvelle n’est créée par le calcul de hauteur ; aucune migration ou nouveau pipeline fictif n’est nécessaire pour cette projection. Les deux sources peuvent montrer des hauteurs différentes parce que leurs captures ont des dates et méthodes différentes.

Ces vues montrent des volumes, sans façades photographiques ni relief de terrain simulé. Elles ne constituent pas une mesure de vue depuis un logement, une simulation solaire vérifiée ou une maquette de promoteur.

## Autres solutions examinées — 20 octobre 2026

| Solution | Décision |
|---|---|
| [MapLibre](https://maplibre.org/maplibre-gl-js/docs/examples/display-buildings-in-3d/) et [OpenFreeMap](https://openfreemap.org/) | Intégrés : moteur ouvert, usage commercial gratuit sans clé ; attribution requise. |
| [Overture Buildings](https://docs.overturemaps.org/guides/buildings/) | Données ouvertes ODbL avec hauteurs selon les objets. Nécessitent un import Buildings qualifié ; le pipeline Places existant ne les collecte pas. Aucune couverture supplémentaire Overture n’est prétendue ici. |
| [CesiumJS](https://cesium.com/learn/cesium-foundations/) / [Cesium ion](https://cesium.com/platform/cesium-ion/pricing/) | Le moteur est ouvert mais ne fournit pas les données. Le plan ion Community gratuit est personnel et non commercial. Un second moteur sur les mêmes données n’ajouterait pas de couverture. Aucun compte ou abonnement activé. |
| [Esri 3D Buildings](https://www.arcgis.com/home/item.html?id=b8fec5af7dfe4866b1b8ac2d2800f282) | Consultation publique ne garantit pas droits d’archivage ou redistribution commerciale : pas intégré comme flux gratuit qualifié. Voir les [conditions propres aux contenus](https://doc.arcgis.com/en/arcgis-online/reference/terms-of-use.htm). |
| [Google Photorealistic 3D Tiles](https://developers.google.com/maps/documentation/tile/usage-and-billing) | Facturation et clé requises. Pas retenu comme source gratuite sans compte. Couverture de surface 3D Abu Dhabi/Reem non confirmée par ce lot. |

Aucune source gratuite de façades photogrammétriques couvrant Abu Dhabi et autorisant l’intégration ainsi que l’archivage demandé n’a été qualifiée. Les sources absentes ne sont pas remplacées par des faux modèles réalistes.

## Propriétaires et validation

`atlas/building-3d.ts` possède les expressions, règles de hauteur, choix fermés et caméra. `building-popup.ts` présente le contexte mondial sans fabriquer d’identité. `map-style.ts`, `parcel-map.tsx` et `projects/neighbourhood-map.tsx` composent les sources existantes ; `map-view-control.tsx` possède l’interface traduite et accessible au clavier. Direction : présentation → contrats/tuiles archivées existants. Aucun nouveau domaine ou dépendance.

Les tests évaluent les expressions avec le validateur réel MapLibre : valeurs manquantes, bornes, exclusion des estimations, visibilité exclusive, priorité de sélection, URL et mouvement réduit. Le build vérifie TypeScript et le serveur compilé. Les contrôles navigateur complètent ces tests : volumes visibles, sources, satellite, retour 2D, sélection, carte projet et largeur de téléphone.

Validation du 20 octobre 2026 : 65 tests web réussis, lint sur 139 fichiers, liens locaux de 42 documents et build Linux/TypeScript réussis ; contrôles HTTP du serveur compilé sur les 16 langues. Le navigateur confirme les volumes mondiaux et du catalogue sur Reem, le satellite 3D, l’ouverture directe du lien 3D, la sélection/fiche/localisation du projet, le contexte mondial avec hauteur indicative, la carte de Park View et le menu compact à 390 × 844 pixels. Ces contrôles ne certifient ni l’exhaustivité des bâtiments ni l’exactitude des hauteurs des sources.

## Couleurs du plan au zoom — 20 octobre 2026

`hydrography.ts` fixe la couleur de l’eau, sans limite de zoom de couche. Les tuiles natives s’arrêtent à 14 et sont réutilisées au-delà par MapLibre. Les géométries archivées restent inchangées.

`presentation.ts` possède les expressions partagées de couleur et d’opacité. Les usages inconnus reprennent désormais la couleur de la légende. Les grands périmètres restent à 0,15 et les parcelles normales à 0,86 sur Explore **et** sur la carte projet ; cette dernière appliquait auparavant 0,86 à tous les périmètres. Le satellite conserve 0,06. Aucune couleur ne varie avec le zoom.

Les aplats d’eau passent après les aplats d’usage des parcelles, avant leurs contours, les rues et les bâtiments. Le cas de la marina à 54,415419 / 24,501281 a été vérifié : la source vectorielle décrit de l’eau, recouverte auparavant par une parcelle grise d’usage nautique. L’ordre partagé évite ce recouvrement lors du chargement des parcelles au zoom. L’usage cadastral et sa sélection restent consultables ; cette priorité visuelle ne modifie aucune frontière ni preuve.

Le défaut exact signalé sur Android n’a pas été reproduit sur ordinateur, y compris dans un viewport de 980 × 1 700 pixels ; le recouvrement de la marina, lui, a été confirmé. Les tuiles archivées présentes ont été contrôlées et deux échantillons réels conservent leur couverture après le découpage de surzoom MapLibre 14 → 16. La validation sur le téléphone reste nécessaire. Aucun changement de table, de pipeline ou de donnée de source.

Validation du correctif : 70 tests web, lint sur 140 fichiers, liens de 42 documents, TypeScript et contrôles HTTP du build sur les 16 langues réussis. Après installation de l’image web locale, le navigateur confirme la marina bleue en 2D et 3D, au zoom rapproché puis au dézoom, avec sélection et fiche conservées, sans erreur console. Les routes Tailscale du site et de Prefect sont conservées ; l’hôte Windows de contrôle ne résout pas le DNS privé du tailnet.
