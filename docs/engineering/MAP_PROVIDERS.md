# Cartes d'exploration et cartes de quartier

## Parcours et données

Depuis le 16 octobre 2026, l'exploration affiche une carte centrale en pleine largeur et la fiche courte sélectionnée **en dessous**, sur ordinateur et téléphone. Le panneau latéral, la feuille mobile fixe et les deux barres fixes superposées ont été retirés. Le bouton du bien sélectionné retrouve sa fiche ; Localiser reste l'action explicite qui déplace la caméra.

La page projet conserve les faits et sources en base et ajoute une carte de quartier. Le territoire vient de la fiche SQL et de `C:\Users\Karim\Repositories\property-platform\packages\contracts\territories.json` : The District utilise Reem, un projet de Saadiyat utilise Saadiyat, sans condition sur le nom du projet. Un territoire inconnu ne reçoit ni carte ni position inventée.

Le bouton de chargement active la carte sur demande. Le mode local lit `/api/atlas/map-context`, borné aux limites de ce quartier : rues, bâtiments, lieux et limites. Il ne charge ni toutes les parcelles des deux îles, ni les autres émirats, ni un scraper. Un repère projet nécessite un point stocké déjà explicitement associé à son slug. Le centre du quartier ne devient jamais la position du projet.

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

Les fichiers sont sous `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\projects\` : `neighbourhood-config.ts` construit l'URL bornée ; `neighbourhood.tsx` possède l'activation et le fournisseur ; `neighbourhood-map.tsx` possède le chunk MapLibre différé, la requête API, l'annulation et le nettoyage. La route `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\[locale]\projects\[slug]\page.tsx` assemble ces composants avec la fiche et sa configuration.

Direction : route projet → configuration/présentation → carte locale → lectures API existantes. L'adaptateur réutilise les types et styles purs d'`atlas`, sans importer l'explorateur complet. Aucun nouveau service, contrat ou schéma SQL.

## Contrôles de cette refonte

Les 43 tests web comprennent les garde-fous de fournisseur, clé et limites Google, la couverture des polices et la parité des dictionnaires. Le compilateur TypeScript, le lint, les contrats et les liens documentaires sont vérifiés. Les contrôles HTTP standalone couvrent toutes les langues du registre ; le contrôle des projets vérifie aussi le quartier issu de la fiche et l'absence de carte embarquée au premier rendu.

Les parcours navigateur contrôlent la galerie, la carte locale de Reem, le lien vers la page du dossier, le vietnamien et l'arabe/RTL sur téléphone. La mise en page place bien le dossier sous la carte et ne déborde pas horizontalement. L'affichage Google réel reste à valider avec une clé de navigateur restreinte : aucune clé n'a été créée ou simulée dans le site.
