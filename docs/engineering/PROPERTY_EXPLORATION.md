# Exploration immobilière et premières fiches documentées

Évolution du 12 octobre 2026. L'exploration ouvre maintenant l'onglet **Properties**, avec les 188 empreintes de bâtiments et les 29 repères de projets déjà collectés pour Al Reem. Cela donne 217 objets cartographiques, pas 217 projets uniques ni un inventaire d'appartements à vendre. Les identités de fournisseurs restent séparées ; un point de courtier peut décrire le même projet qu'un autre point.

## Ce que fait le clic

Un clic affiche la fiche et met le contour ou le repère en évidence, sans changer la caméra. Le choix précis est **bâtiment → repère explicite de projet → parcelle réelle → autre lieu → rue**. Les secteurs, l'île et les parcelles `ProjectLimits` restent du contexte visuel et ne prennent plus le clic. Les boutons Whole area / Focus area / Neighbourhood et **Locate on map** sont les seules commandes de cadrage ; cette dernière est volontaire.

La fiche est placée avant la recherche dans le panneau. Sur ordinateur, seul ce panneau défile pour la lire ; sur téléphone, la page rejoint la fiche située sous la carte, sans changer sa caméra. Fermer la fiche ou utiliser Locate on map ramène la carte à l'écran mobile. La légende cadastrale est repliée dans Properties et reste accessible ; les filtres cadastraux apparaissent seulement dans Parcels. Les bâtiments cachés par une couche ou absents des sources ne sont pas inventés.

### Titres des fiches et des listes — 13 octobre 2026

Même en sélectionnant une parcelle, le titre privilégie le nom de projet ou de bâtiment disponible à cet emplacement, y compris un repère de courtier non confirmé. Sans nom, un promoteur documenté puis un éditeur documenté peuvent servir de titre ; sans ces informations, le libellé traduit « Land parcel » remplace un code technique en titre. Un café ou un banc présent sur la parcelle ne devient pas son identité immobilière. La recherche couvre également les noms de présentation, promoteurs et éditeurs.

Par exemple, la sélection de `RT3_C53_to_C56` présente **The District**, Reportage Properties et le lien du projet, avec « Possible association ». La référence secondaire se lit **RT3 · C53–C56**. Le code exact reste dans les détails cadastraux, les recherches et les exports ; aucune parcelle n'est renommée en base. L'association reste spatiale, pas une confirmation d'identité commerciale ou de propriété. En cas de plusieurs candidats, un nom disponible prime sur un fournisseur sans nom de bien, puis une présentation documentée et un repère de projet priment ; l'ordre alphabétique départage les autres. Les alternatives restent consultables et aucune identité n'est fusionnée.

`C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\presentation.ts` centralise ce choix et le format de référence pour les fiches et listes. Une empreinte et un point OSM peuvent partager exactement la même URL de way : la présentation de l'empreinte peut alors enrichir ce point pour l'affichage. Une ressemblance de nom ou un bâtiment simplement voisin ne suffit pas. Le changement concerne le web ; aucune migration ni réimportation n'est nécessaire.

## Informations effectivement disponibles

| Objet | Présentation ajoutée en base | Photo |
|---|---|---|
| Sun Tower | Aldar Properties, résumé du groupe Sun/Sky, lien de projet Aldar | Vue commune des deux tours, datée du 21 mars 2011 |
| Sky Tower | Aldar Properties, résumé du groupe Sun/Sky, lien de projet Aldar | Même photographie historique, avec licence et auteur |
| Leaf Tower | Résumé et brochure officielle MAAM Group ; MAAM est présenté comme éditeur de cette information | Aucune photo approuvée ajoutée |
| The District | Reportage Properties, résumé et site officiel | Pas de photo copiée sans droits établis |
| Vista 3 | Reportage Properties, résumé et site officiel | Pas de photo copiée sans droits établis |
| Radisson Residences | Royal Development Holding, résumé et site officiel | Pas de photo copiée sans droits établis |

Sources primaires : [projet Sun/Sky chez Aldar](https://www.aldar.com/en/explore-aldar/businesses/development/residential/reem-island/sun-and-sky-towers), [article Aldar sur Shams Abu Dhabi](https://www.aldar.com/en/news-and-media/residents-and-investors-look-to-shams-abu-dhabi), [brochure Leaf Tower chez MAAM](https://www.maam.ae/wp-content/uploads/2020/08/Final_Flyer_LeafTower-pq-rgb_web-1.pdf).

Les étages et hauteurs affichés restent les observations OSM, avec leur lien distinct. Ils ne sont pas attribués au promoteur. La brochure Leaf Tower ne suffit pas à trancher les attributions contradictoires de promoteur trouvées ailleurs : ce champ reste vide. The District, Vista 3 et Radisson ont également leur présentation liée au repère exact déjà collecté, sans valider sa position commerciale par le seul clic. Les autres bâtiments ont leur nom et leurs informations OSM existantes ; les repères reliés à une référence ont son lien. Aucun prix, plan de paiement, inventaire ou promoteur n'est rempli par supposition.

La photo Sun/Sky est de **giggel**, sous **CC BY 3.0**. La page Wikimedia, les octets JPEG et leur empreinte sont conservés comme captures, avec leurs dates réelles de collecte. La légende précise qu'il s'agit d'une vue historique commune aux deux tours. Auteur, lien vers la page et lien de licence apparaissent dans la fiche ; ces mentions sont requises pour ce média, distinct des photos décoratives Unsplash de l'accueil.

## Stockage et séparation des responsabilités

- `property_platform.real_estate.building` et `place` gardent les identités et géométries d'origine.
- `property_platform.evidence.property_presentation` contient des colonnes typées : identité bâtiment ou lieu, nom d'affichage, éditeur, promoteur éventuellement renseigné, résumé, langue, lien, version de revue et date d'ingestion. Une contrainte exige exactement une identité cible.
- `property_platform.evidence.property_media` relie une présentation à une capture d'image et à une capture de licence, avec auteur, légende, langue, date de prise de vue, type MIME, licence et contrôle de diffusion.
- `evidence.capture` conserve les réponses et SHA-256 ; `ingestion_run` conserve l'acteur, les heures, la version et le résultat. L'import entier est atomique et verrouillé ; une licence manquante ou un reçu invalide annule le lot.

Les versions précédentes sont conservées. Refaire l'import crée de nouveaux reçus et observations, sans dupliquer les identités métier. La projection choisit la présentation la plus récente pour chaque identité source exacte. Aucun rapprochement bâtiment/parcelle ou fusion de projets n'est créé par proximité ou ressemblance de nom.

Les captures d'images sont limitées à 2 Mio pour ce pilote, les reçus à 4 Mio par source. Le contexte de carte renvoie seulement les métadonnées ; il ne lit ni ne sérialise les pages sources ou images binaires. Le JPEG est demandé au clic via une route fixe, bornée, avec `nosniff`, le même verrou de prévisualisation locale et aucun paramètre d'URL distante. Le média n'est plus servi lorsque `display_allowed=false`. Un service d'administration audité pour cette décision, des rôles et le stockage objet devront précéder la publication commerciale ; cette tranche n'ajoute pas une interface d'écriture publique.

Les photos sont des captures locales de pilote, pas une bibliothèque complète de médias. Un futur stockage objet pourra remplacer leur transport tout en gardant les identifiants, droits, références et contrat de présentation. OCR, génération 3D, vidéo, travaux payants et contrats de droits pour photos de promoteurs restent séparés.

## Refaire l'installation sur un autre poste

Sur le poste de Karim, migration et import ont déjà été appliqués. **Il suffit de rafraîchir l'aperçu actuel sur 3102.** Les commandes suivantes servent à installer cette évolution sur une autre base locale déjà alimentée en bâtiments Reem.

Toutes les commandes partent de `C:\Users\Karim\Repositories\property-platform` dans PowerShell ; attendre le succès de chacune.

1. Reconstruire l'API pour copier le code courant dans son conteneur, puis créer les deux tables additionnelles :

```powershell
docker compose -f infra/local/compose.yaml up -d --build api
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
```

La migration `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\migrations\0010_property_presentations.py` crée les tables dans `evidence`. Elle ne renomme ni ne supprime les anciennes tables et ne collecte aucune donnée. Si la reconstruction échoue sur le certificat, arrêter cette séquence et suivre [DEVELOPMENT.md](DEVELOPMENT.md#apres-maj).

2. Collecter les URL examinées du registre, depuis Windows, avec les certificats système :

```powershell
.\scripts\collect-property-presentations.ps1
```

Le script `C:\Users\Karim\Repositories\property-platform\scripts\collect-property-presentations.ps1` récupère sept réponses HTTPS : article Aldar, brochure MAAM, deux pages Reportage, page de projet RDH, page de licence Wikimedia et JPEG réduit fourni par Wikimedia. Il enregistre les octets, heures et empreintes dans `C:\Users\Karim\Repositories\property-platform\.cache\acquisition\property-presentations.json`. Ce reçu de source est ignoré par Git ; ce n'est pas un export de base. Si une collecte échoue, ne pas lancer l'import avec un ancien reçu sans examiner ses dates.

3. Copier le reçu dans le conteneur API et importer les observations validées :

```powershell
docker compose -f infra/local/compose.yaml cp .cache/acquisition/property-presentations.json api:/tmp/property-presentations.json
docker compose -f infra/local/compose.yaml exec api python manage.py import_property_presentations --actor Karim --receipt /tmp/property-presentations.json
```

Cette étape vérifie empreintes, heures avec fuseau, URL attendues, identité exacte, présence des éléments de revue, licence/auteur et type JPEG. Elle insère six présentations et deux observations photo ; une seule photographie distincte est réutilisée pour les deux tours. Les dates de publication inconnues restent nulles ; aucune heure de publication n'est inventée.

4. Pour le web sur 3000, utiliser `pnpm.cmd dev:web`. Pour la version compilée sur 3102, reconstruire web selon [DEVELOPMENT.md](DEVELOPMENT.md#apres-maj). Aucun import Onwani ou OSM supplémentaire n'est nécessaire si ces objets existent déjà.

## Où étendre les fiches

- `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\property_presentations.json` : références examinées et identités fournisseur exactes. Ajouter un bâtiment exige d'examiner son identité et sa page, pas seulement d'ajouter son nom.
- `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\property_media.json` : médias dont le sujet et les droits ont été vérifiés. Une photo publiée par un promoteur n'est pas automatiquement autorisée à être copiée.
- `property_protocol.py` valide les reçus sans modèle Django ; `property_import.py` orchestre leur enregistrement ; `queries.py` projette les champs autorisés ; `publication/map_preview.py` assemble cette projection sans mutation.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\property-card.tsx` : présentation du bien ; `inspector.tsx` : informations secondaires et parcelle ; `explorer.tsx` : sélection/liste ; `parcel-map.tsx` : mise en évidence et cadrage explicite.

Les registres ne sont pas injectés directement dans le site : ils décrivent une revue et une acquisition ; l'interface consomme la base par l'API. Les noms de projet ne sont pas codés dans les composants. Les textes d'interface sont traduits dans quinze langues ; résumés et légendes gardent leur langue originale, indiquée avec `lang` et `dir`.

## Validation locale

Pour l'évolution des titres du 13 octobre : 19 tests web, TypeScript, Biome, liens documentaires, compilation et contrôles HTTP des quinze langues passent. La fiche et la liste réelles montrent The District à la place du code en titre ; la référence exacte reste consultable et une sélection conserve l'échelle de 1 km. RT4_C119 vérifie le secours « Land parcel ». Le rendu mobile à 390 × 844 est contrôlé en anglais et arabe, sans débordement horizontal ni erreur console. Seul le conteneur web a été remplacé ; aucune migration, collecte ou modification de données n'a été exécutée. Les contrôles PostGIS ci-dessous proviennent de la tranche initiale, dont le backend n'a pas changé.

140 tests backend sur une base PostGIS de test isolée, 13 tests web, contrats générés et deux règles de dépendance passent. Le build et les contrôles HTTP couvrent les quinze langues et le refus d'accès aux médias hors de la prévisualisation autorisée. Les tests vérifient aussi qu'une lecture de contexte ne sélectionne pas les payloads binaires, qu'un média retiré n'est plus exposé et qu'un lot invalide ou interrompu ne laisse pas de mutations partielles.

Les clics réels sur Leaf Tower, RT4_C119 et The District conservent le cadrage de 300 m ; un clic dans le secteur RT4 vide ne crée aucune sélection. Locate on map est testé séparément. La photo locale charge ses 960 pixels ; anglais et arabe sont vérifiés à 390 × 844 sans débordement horizontal. La fiche devient visible sur mobile et sa fermeture ramène la carte, sans modifier son zoom. Ces contrôles ne remplacent pas une revue linguistique ou des mesures sur appareils physiques.

La base locale conserve ses 2 431 parcelles et 188 bâtiments. Elle contient six présentations courantes, neuf observations de présentation avec leur historique et quatre observations photo (deux versions pour les deux tours ; une photographie distincte). Les reconstructions ont réutilisé les dépendances verrouillées déjà installées ; le problème de certificats d'une installation complète reste la limite décrite dans [DEVELOPMENT.md](DEVELOPMENT.md).
