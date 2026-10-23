# Cartes d'exploration et cartes de quartier

**Vues 3D — 20 octobre 2026 :** [BUILDINGS_3D.md](BUILDINGS_3D.md) décrit les volumes du catalogue et OpenStreetMap mondial, sur plan ou satellite, leurs estimations et les solutions externes examinées. Les tuiles mondiales réutilisent l’archive Prefect existante ; aucun fournisseur payant ajouté.

## Parcours et données

Depuis le 17 octobre 2026, Explore occupe tout le viewport sous l’en-tête, sans marge de page. Les contrôles flottent sur la carte. Une fiche compacte apparaît au clic, dans la carte sur ordinateur et en bas sur téléphone ; son lien ouvre le dossier complet. Localiser reste une action explicite : le clic ne zoome pas automatiquement. Les parcelles, rues, bâtiments, lieux et noms sont visibles par défaut dans Explore ; les secteurs et codes sont facultatifs. Leurs données restent conservées.

La page projet conserve les faits et sources en base et ajoute une carte de quartier. Le territoire vient de la fiche SQL et de `C:\Users\Karim\Repositories\property-platform\packages\contracts\territories.json` : The District utilise Reem, un projet de Saadiyat utilise Saadiyat, sans condition sur le nom du projet. Un territoire inconnu ne reçoit ni carte ni position inventée.

Le bouton de chargement active la carte sur demande. Le mode local lit `/api/atlas/map-context` et les pages bornées de `/api/atlas/parcels`, pour la seule île du projet : parcelles colorées, usages, rues, bâtiments, commerces, équipements et lieux de transport déjà ingérés. La lecture couvre cette île pour permettre de déplacer la carte ; elle ne charge ni les deux îles ensemble, ni les autres émirats, ni un scraper. Les objets sont sélectionnables selon la priorité bâtiment → lieu → rue → parcelle spécifique → grand périmètre ; les secteurs restent non interactifs. La légende est repliable. Une ligne de métro ou un arrêt non acquis n’est pas créé pour la présentation. Un repère projet nécessite un point stocké déjà explicitement associé à son slug. Le centre du quartier ne devient jamais la position du projet.

**Tuiles de parcelles dans Explore — 23 octobre 2026.** Explore lit `/api/atlas/parcel-index` (lignes publiées sans géométrie) et dessine les contours depuis `/api/atlas/parcel-tiles/{z}/{x}/{y}`. Couleurs, filtre d'usage, sélection, libellés et export CSV restent fondés sur les lignes publiées ; voir [la feuille de route technique](ENGINEERING_ROADMAP.md#tuiles-vectorielles-des-parcelles--23-octobre-2026). La carte de quartier des fiches projet garde la lecture `/api/atlas/parcels` décrite ci-dessous.

**Cadrage de tous les projets — 17 octobre 2026.** La fiche API fournit `map_locations`, lu directement depuis les liens actifs du projet vers ses bâtiments, lieux ou parcelles. Le cadrage ne dépend plus des points présents dans une réponse de carte générale tronquée, ni d’une présentation commerciale distincte. À l’ouverture de la carte locale, la caméra cadre ces géométries avec un zoom maximal de 16,5 : points orange avec halo, contours de bâtiments/parcelles orange, nom du projet. Plusieurs bâtiments du même programme sont cadrés ensemble, notamment Park View. Le cadrage initial reste centré sur le projet ; les couches détaillées sont chargées pour son île et le projet garde son accent orange. Les informations supplémentaires d’une parcelle sélectionnée dans Explore se déplient à la demande.

Ce comportement ne contient aucune exception par nom de projet. Un lien révoqué, un objet inactif ou une géométrie hors de l’île sont exclus. Sans localisation admissible, un message traduit indique que la position exacte n’est pas encore documentée ; le centre de l’île ne devient jamais le point du projet. Les clics de l’explorateur général ne déclenchent toujours pas de zoom automatique.

Les imports Prefect `project-details` et `saadiyat-project-details` extraient aussi les positions des cartes de promoteurs reconnues par `research_sources.py`. Les repères restent **déclarés et non vérifiés**, séparés d’une propriété cadastrale. Un centre de caméra Google embarquée n’est jamais utilisé comme position du projet : seuls des marqueurs explicitement positionnés et identifiés sont admissibles. Les bureaux de vente, attractions voisines, noms discordants et positions ambiguës ne sont pas acceptés. Les preuves vont dans les tables existantes `evidence.capture`, `evidence.map_observation` et `evidence.project_identity_link`, avec le point dans `real_estate.place`. Aucun nouveau schéma ni migration. Voir [PROJECTS.md](PROJECTS.md).

## MapLibre et Google Maps

MapLibre est notre moteur de rendu ; Onwani et OpenStreetMap sont des sources et PostgreSQL/PostGIS conserve nos données. Changer de fond ne remplace donc ni les parcelles, ni les preuves, ni les imports.

La [page Proprobin examinée](https://proprobin.com/abu-dhabi/project?slug=talay-beach-villas-at-marsa-al-saadiyat) possède une carte Google interactive avec des projets voisins. Le nombre de champs affichés ne permet pas de déduire ses choix de performances internes. Ici, le premier affichage reste léger en différant la carte et en bornant sa lecture au quartier.

| Usage | Fournisseur | Option Google |
|---|---|---|
| Atlas avec parcelles, sélection et exports | MapLibre et nos lectures API | Un remplacement complet demanderait un adaptateur Maps JavaScript, la facturation et la reprise des interactions/exports ; ce lot ne prétend pas le réaliser |
| Carte des alentours sur une page projet | MapLibre local sur demande | Maps Embed API, prête à configurer et également activée sur demande |

Google annonce [Maps Embed sans frais d'utilisation et sans limite de requêtes](https://developers.google.com/maps/documentation/embed/usage-and-billing), avec une clé obligatoire. Le [parcours de configuration](https://developers.google.com/maps/documentation/embed/get-api-key) demande un projet Google Cloud, les prérequis de compte/facturation et l'activation de l'API. [Maps JavaScript possède une facturation distincte](https://developers.google.com/maps/documentation/javascript/usage-and-billing). Aucun compte, abonnement ou service payant n'a été activé ici.

## Activer Google pour les pages projets

1. Dans Google Cloud, préparer le projet et activer **Maps Embed API**. Vérifier les prérequis proposés par Google et ses conditions avant validation.
2. Créer une **clé de navigateur dédiée**, restreinte à Maps Embed API et aux référents HTTP nécessaires : par exemple `http://localhost:3000/*`, `http://localhost:3102/*` et l'hôte HTTPS privé utilisé sur téléphone. Ne pas utiliser une clé serveur ou sans restrictions.
3. Pour le site sur 3000, ajouter ces variables au fichier local ignoré `C:\Users\Karim\Repositories\property-platform\apps\web\.env.local` :

   ```dotenv
   PROJECT_NEIGHBOURHOOD_PROVIDER=google
   GOOGLE_MAPS_EMBED_BROWSER_KEY=REMPLACER_PAR_LA_CLE_NAVIGATEUR_RESTREINTE
   ```

   Redémarrer `pnpm.cmd dev:web`. L'exemple versionné est `C:\Users\Karim\Repositories\property-platform\apps\web\.env.example`.

4. Pour Docker, fournir les mêmes variables dans le terminal PowerShell ou dans le fichier `.env` ignoré à la racine, puis recréer le web avec la composition habituelle. `C:\Users\Karim\Repositories\property-platform\infra\local\compose.yaml` les transmet au web. La configuration se lit côté serveur à l'exécution ; aucun import ou migration n'est nécessaire. Reprendre aussi le connecteur partageant le réseau du web selon [REMOTE_PREVIEW.md](REMOTE_PREVIEW.md).
5. Ouvrir une page projet, puis sa carte de quartier. Le lien **Utiliser notre carte détaillée** revient au mode local, notamment si Google refuse une restriction de clé. `PROJECT_NEIGHBOURHOOD_PROVIDER=local` rétablit le défaut.

Cette clé précise est **visible dans l'URL de l'iframe**, conformément au fonctionnement de Google ; ses restrictions assurent sa protection. Les identifiants serveur et autres clés restent privés. Les vraies valeurs restent hors Git, des journaux et des captures de configuration. Google n'est contacté qu'après l'action de chargement ; sa réception de l'IP et du référent devra être décrite avant publication publique.

Le mode Google utilise l'endpoint fixe `https://www.google.com/maps/embed/v1/view`, centré sur les limites du quartier, avec la locale de la page. Il ne géocode pas le nom du projet et n'invente aucun repère. Le CSP autorise les frames uniquement depuis `https://www.google.com` et conserve les protections contre l'intégration de notre site par des tiers.

## Propriétaires du code

Les fichiers sont sous `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\projects\` : `neighbourhood-config.ts` construit l'URL bornée ; `neighbourhood.tsx` possède l'activation et le fournisseur ; `neighbourhood-map.tsx` possède le chunk MapLibre différé, la requête API, l'annulation et le nettoyage. `neighbourhood-focus.ts` calcule le cadrage des localisations typées et fournit aussi un calcul pur de fenêtre de contexte, sans dépendance de rendu ni écriture. La route `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\[locale]\projects\[slug]\page.tsx` assemble ces composants avec la fiche et sa configuration.

Direction : route projet → configuration/présentation → carte locale → lectures API existantes. L'adaptateur réutilise les types et styles purs d'`atlas`, sans importer l'explorateur complet. Aucun nouveau service, contrat ou schéma SQL.

## Contrôles historiques de la refonte du 16 octobre 2026

Les 43 tests web comprennent les garde-fous de fournisseur, clé et limites Google, la couverture des polices et la parité des dictionnaires. Le compilateur TypeScript, le lint, les contrats et les liens documentaires sont vérifiés. Les contrôles HTTP standalone couvrent toutes les langues du registre ; le contrôle des projets vérifie aussi le quartier issu de la fiche et l'absence de carte embarquée au premier rendu.

Les parcours navigateur contrôlent la galerie, la carte locale de Reem, le lien vers la page du dossier, le vietnamien et l'arabe/RTL sur téléphone. La mise en page place bien le dossier sous la carte et ne déborde pas horizontalement. L'affichage Google réel reste à valider avec une clé de navigateur restreinte : aucune clé n'a été créée ou simulée dans le site.

## Lieux et lisibilité satellite — 17 octobre 2026

Les cartes locales lisent aussi les lieux [Overture](OVERTURE_PLACES.md), avec attribution distincte et niveau communautaire. Les sources raster examinées sont regroupées dans `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\imagery-sources.ts`. Le satellite Esri reste le défaut ; les aplats de parcelles/bâtiments sont allégés pour ne plus masquer la photo. Les aperçus historiques Sentinel restent limités à 10 m/pixel. L’archive Wayback testée refuse ses tuiles ici ; elle n’est pas proposée comme fond fonctionnel. Aucun nouveau fournisseur payant n’est activé.


**Confort mobile — 17 octobre 2026.** Lorsque la fiche recouvre le repère sélectionné sur téléphone, la caméra se déplace juste assez pour le rendre visible au-dessus, en conservant le niveau de zoom. Les déplacements manuels ultérieurs restent libres. Le plan Explore peut afficher son contexte dès sa réception, pendant que les pages de parcelles finissent de charger ; un échec partiel reste signalé et peut être relancé.


## Eau et couverture des aperçus — 19 octobre 2026

Le plan utilise les couches vectorielles `water` et `waterway` du TileJSON public [OpenFreeMap](https://tiles.openfreemap.org/planet), suivant le [guide officiel](https://openfreemap.org/quick_start/). Elles montrent mer, canaux et plans d’eau connus, sans remplacer les limites cadastrales Onwani. Les tunnels et cours d’eau intermittents ne sont pas peints comme eau de surface permanente. Ce contexte externe est chargé directement par MapLibre dans Explore et dans la carte de quartier, après son activation. Il n’est ni une preuve cadastrale importée ni une nouvelle identité en base ; aucune collecte Prefect, table ou migration n’est ajoutée. Les crédits OpenFreeMap/OpenMapTiles/OpenStreetMap proviennent du TileJSON et sont conservés à l’écran ; l’export PNG les reprend explicitement. Le service public reste une dépendance réseau extérieure, sans clé ni abonnement activé.

`atlas/hydrography.ts` possède la configuration et les couches hydrologiques ; les deux cartes dépendent de ce module de présentation et de `map-style.ts`. Le bleu est réservé à l’eau. La palette partagée `presentation.COLORS` conserve la taxonomie publiée : ocre commerce/mixte, crème résidentiel, vert espaces verts, rose équipements, gris réseaux, violet rail, taupe périmètres, gris clair usages inconnus. L’eau a une entrée de légende distincte, sans être présentée comme une catégorie cadastrale filtrable. La palette est commune aux légendes, cartes locales et exports.

Les deux scènes Sentinel enregistrées couvrent uniquement un rectangle autour de Reem : ce sont des PNG recadrés à 10 m de résolution source, pas des tuiles satellite mondiales. Cette première tentative plaçait Esri en dessous et hors de ce rectangle ; elle est désormais remplacée par la politique de source unique ci-dessous. Le menu de cette première tentative indiquait des dates différentes hors de l’aperçu et affichait les crédits Copernicus/Esri ; ces indications sont remplacées avec les fonds mondiaux. La couverture et la date Sentinel ne sont jamais attribuées aux autres îles. Le raccourci Projects près des sélecteurs de territoire est retiré ; la navigation principale Projets reste disponible.


## Sources satellite homogènes — 19 octobre 2026

La [recherche et décision satellite](SATELLITE_IMAGERY.md) remplace le mélange des aperçus Reem et d’Esri. Le menu propose désormais des fonds mondiaux : Esri ou mosaïques annuelles Sentinel-2 ESA WorldCover 2020/2021. Un seul fond est visible ; la même source s’applique aux deux îles et au-delà. Les anciens reçus 2026 restent conservés en base mais ne sont plus présentés comme un fond couvrant les autres régions. Un relais WMTS fixe, borné et protégé par l’activation d’aperçu, rend les PNG publics Terrascope utilisables par WebGL sans CORS externe. Les noms de couches, niveaux et années viennent du registre ; aucun calcul raster ou nouvel import n’entre dans le runtime. Les crédits et exports suivent la source choisie. Les limites de résolution, de couverture et d’historique sont documentées dans le comparatif.

Le paramètre de page `basemap` conserve la source choisie lors du passage Reem → Saadiyat et des changements de langue. Seuls les identifiants du registre sont acceptés ; la sélection ne déclenche ni géocodage ni import.
