# Identité visuelle de Property Platform

**Sources dans les fiches — 21 octobre, soir :** les volets publics affichent les sources et dates, une fois par capture. Les extraits d'extracteur, listes sérialisées et pointeurs n'y sont plus rendus, même dans un sous-volet. Leur conservation en base/API et le contrôle des 174 fiches sont décrits dans [l'audit des affichages](PROJECT_DISPLAY_AUDIT_20261021.md).

Refonte du 16 octobre 2026 : teal profond, ivoire et bronze discret, photographies locales des Émirats et parcours cohérent entre accueil, carte et fiches projets. La couverture détaillée actuelle concerne **Al Reem et Saadiyat** ; les autres émirats restent des régions à préparer. Les preuves et sources immobilières restent dans la carte et les fiches, sans grand bandeau technique sur l'accueil.

## Parcours et hiérarchie

L'accueil propose d'abord deux actions : explorer la carte ou consulter les projets. Le panneau suivant donne accès directement à Al Reem et Saadiyat à partir des territoires actifs du contrat, sans inventer de statistiques de marché. Les liens bâtiments, lieux et rues donnent accès à la carte et à ses couches ; les anciens onglets de listes ne sont plus proposés. Le lien vers les régions et les trois chapitres photographiques restent disponibles ; les régions sans données sont signalées en préparation.

L'annuaire `/[locale]/projects` effectue sa recherche côté serveur par formulaire GET, avec 48 fiches par page. Les filtres territoriaux conservent la recherche ; une recherche ou un changement de territoire repart à la première page. Le compteur distingue la tranche affichée du total, la navigation figure avant et après les résultats et une ancienne page devenue hors limites rejoint la dernière page disponible. Aucun clic ne lance de collecte ou de rapprochement. Les cartes mènent au dossier ; leur monogramme n'est pas une photographie du projet. Le lien de carte exige une localisation utilisable.

La fiche et l'aperçu cartographique partagent la même hiérarchie : identité du projet, promoteur, faits documentés, documents et lien officiel. Les prix, disponibilités et modalités de paiement non vérifiés restent explicitement présentés comme tels. Une référence média externe ne devient pas une image intégrée sans publication autorisée. Les noms et textes des sources conservent leur langue originale.

## Carte sur ordinateur et téléphone

Le clic sur un projet documenté ouvre une fiche compacte flottante dans la carte : photographie du projet autorisée si disponible, nom, promoteur, quartier, livraison annoncée, trois types de biens au maximum et nombre de logements du programme lorsqu’il est documenté. Le nombre annoncé n’est pas une disponibilité. Sans photographie du projet autorisée, une seule photo locale porte explicitement le libellé d'ambiance d'Abu Dhabi, y compris dans l'aperçu ; elle ne simule pas une galerie du programme. L'accès au dossier suit immédiatement le nom et le promoteur. Prix, ventes récentes, statut de livraison et rendements ne sont pas inventés lorsque ces faits manquent au contrat du projet. Le dossier complet s’ouvre sur sa page dédiée. L’annuaire privilégie cette page ; le lien secondaire retrouve la carte. Aucun inventaire de bâtiments anonymes ni recherche générale n’occupe le bas de l’exploration.

Les noms potentiels de parcelles utilisent `≈` et les rapprochements enregistrés, sans fusion d’identités. Les usages officiels restent distincts. Les détails cadastraux, rues proches et équipements autour du lieu sont dépliables. Les équipements sont lus à la demande depuis PostgreSQL, dans sept catégories utiles ; aucune durée de marche, ouverture ou note commerciale n’est inventée. Les enregistrements cadastraux presque superposés peuvent être comparés. Voir [NEIGHBOURHOOD.md](NEIGHBOURHOOD.md).

Explore occupe tout le viewport sous un en-tête compact, sans marge ni défilement du document. Les sélecteurs et réglages sont flottants. La fiche est contenue dans la carte et défile seulement lorsque son contenu dépasse la hauteur disponible ; sur téléphone elle est ancrée en bas. La carte garde sa taille lors d’une sélection. La fermeture et Échap conservent le retour clavier ; Localiser cadre explicitement l’objet, sans zoom automatique au clic. Le plan Explore affiche parcelles, rues, bâtiments, lieux et noms ; les secteurs et codes restent optionnels. La carte différée de la page projet affiche au contraire les parcelles et les couches détaillées de son île, avec légende et projet mis en évidence. Marché possède sa page dédiée ; les anciennes données de contexte et de sources restent conservées sans onglets flottants. Les exports et couches sont dans les réglages, et la légende est repliable. La pagination bornée reste utilisée pour les sources et données de marché, sans grille générale.


Les textes de ces parcours sont présents dans **toutes les langues du registre**. Les propriétés CSS logiques préservent arabe, ourdou et persan en RTL ; la photographie et la carte ne sont pas retournées. Les boutons exposent des libellés traduits même lorsqu'une icône accompagne le texte. Les commandes principales visent une hauteur tactile d'au moins 44 pixels. Les tests techniques ne remplacent pas une relecture linguistique ou des essais sur le téléphone réel.

## Photographies et droits

Les photos servent d'ambiance éditoriale. Elles ne représentent pas un bien sélectionné et ne prouvent pas une couverture nationale. Voir [UAE_COVERAGE.md](UAE_COVERAGE.md) et [la couverture détaillée des projets Reem/Saadiyat](PROJECTS.md).

| Usage | Fichiers sous `apps/web/public/images/uae/` | Auteur et page officielle |
|---|---|---|
| Premier écran, Dubai | `dubai-night-768.webp`, `dubai-night-1920.webp` | [Alla Rome](https://unsplash.com/photos/the-skyline-of-a-large-city-at-night-lODmPrkAxM8) |
| Chapitre du littoral | `abu-dhabi-coast-768.webp`, `abu-dhabi-coast-1920.webp` | [Hanks K](https://unsplash.com/photos/beach-palm-trees-and-resort-under-a-hazy-sky-_c08bbHy-xg) |
| Invitation finale | `abu-dhabi-sunset-768.webp`, `abu-dhabi-sunset-1920.webp` | [Yulia Evtushenko](https://unsplash.com/photos/a-couple-of-palm-trees-sitting-next-to-each-other-MhpX3VgaG4U) |

Les trois pages affichent la licence gratuite [Unsplash](https://unsplash.com/license), revérifiée le 12 octobre 2026. Elle permet l'usage commercial sans attribution obligatoire. Les crédits visibles ont été retirés à la demande de Karim ; auteurs, pages, droits, dates et empreintes restent dans `credits.json` et ce guide. Les photos restent des ressources locales, sans intégration API Unsplash. Les [conditions de l'API](https://unsplash.com/documentation) constituent un cas distinct et ne doivent pas être confondues avec ces téléchargements sous licence.

Une seule image est prioritaire : 71 904 octets sur mobile ou 381 392 sur ordinateur. Les deux autres portent `loading="lazy"` ; le navigateur décide quand les charger. La largeur 768 est choisie jusqu'à 700 pixels d'écran. Aucune vidéo ni rotation automatique n'est téléchargée ou lancée.

## Typographie locale

L'interface utilise **Manrope**, les titres **Cormorant Garamond**, et les écritures arabe/ourdou/persan **Noto Sans Arabic**. Les autres écritures gardent un fallback système, sans modification du texte original des preuves.

Les fichiers WOFF2 et les licences SIL Open Font License sont conservés sous `C:\Users\Karim\Repositories\property-platform\apps\web\public\fonts\`. Le manifeste `credits.json` y décrit les sources officielles, versions réelles, sous-ensembles Unicode, tailles et SHA-256. `fonts.css` contient les déclarations `@font-face`, importées dans le CSS partagé ; `font-display: swap` garde les textes visibles pendant le chargement. Les polices sont servies par le site, sans requête au fournisseur Google pendant la navigation.

`C:\Users\Karim\Repositories\property-platform\apps\web\src\theme\fonts.ts` possède les profils de préchargement ; le registre `i18n/locales.ts` associe chaque langue à son profil. Le layout serveur émet les liens vers les mêmes URL publiques que le CSS, pour éviter de télécharger une seconde copie. Budget initial des fontes préchargées : 62 476 octets pour le profil latin, 82 216 pour le vietnamien (latin et accents spécifiques), 60 504 pour le russe, 190 796 pour le RTL et 24 836 pour les autres écritures (marque/codes latins). Un contenu mêlant plusieurs écritures peut charger un autre sous-ensemble au besoin.

Les variables `--font-ui` et `--font-display` de `globals.css` permettent de changer les familles. Le sens RTL est conservé, les lettres arabes ne sont pas espacées artificiellement et les photos ne sont pas retournées.

## Boutons, couleurs et composition

Références visuelles consultées : [Dubai Sotheby's International Realty](https://sothebysrealty.ae/) pour les compositions photographiques et les titres serif, [Aman Residences](https://www.aman.com/residences) pour l'ivoire et l'espace. Nous conservons une composition et des assets propres au projet.

Le bouton principal de l'accueil associe une surface ivoire, une bordure lumineuse, des ombres superposées et une flèche dans un médaillon teal. L'action secondaire mène aux projets ; le choix d'émirat reste accessible plus bas. Les boutons capsule de l'accueil et les surfaces arrondies de l'exploration partagent une palette sobre. Le survol déplace légèrement les commandes sur pointeur précis ; le clic produit un enfoncement. Le focus clavier reste visible. Les couleurs sémantiques de la légende cartographique gardent leur signification métier.

| Couleur | Variable | Usage |
|---|---|---|
| `#103B43` | `--ink` partagé | Texte et fonds teal profond |
| `#F8F7F2` | Fond partagé | Fond ivoire du site |
| `#FFFEFA` | `--surface` | Cartes et contrôles |
| `#A78653` | `--bronze` | Accents sobres |
| `#59656C` | `--muted` | Texte secondaire |
| `#DED9CF` | `--line` | Séparateurs |

Le rayon, la durée et les ombres partagés restent dans `--control-*` de `globals.css`. Les variantes de l'accueil sont dans `home.module.css`, avec leur teal `#103B3C`, ivoire `#F8F5EE` et sable `#C7A981`. Les styles de l'explorateur sont isolés dans `explorer.module.css`, ceux des projets dans `project.module.css`. Aucune bibliothèque d'animation ou d'icônes n'est ajoutée : `components/ui-icon.tsx` rend quelques SVG décoratifs, tandis que les boutons portent leurs libellés accessibles.

## Défilement et accessibilité

Les boutons After dark / By the sea / Golden hour et lecture/pause ont été supprimés. Le premier visuel est fixe ; les autres photos occupent les sections suivantes. Le diaporama et son zoom automatique de 14 secondes ont été retirés avec leurs timers et leur composant client. Une animation automatique prolongée sans commande de pause aurait nécessité un autre mécanisme selon [WCAG 2.2.2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html).

La parallaxe suit le défilement natif : paysage jusqu'à 150 pixels sur ordinateur, 80 sur téléphone, texte plus lent ; image du littoral jusqu'à 60 ou 28 pixels. Le cadre du littoral reste brièvement en place sur ordinateur avec `position: sticky` ; il défile normalement sur téléphone. Le cadrage fixe met en valeur la plage et les palmiers.

Une tâche `requestAnimationFrame` déclenchée par scroll/resize lit les cadres puis écrit les variables CSS. Il n'y a pas de boucle JavaScript permanente ni de rendu React par pixel. Les apparitions utilisent Intersection Observer et cessent d'observer l'élément une fois visible. Les éléments atteints au clavier apparaissent immédiatement. La réduction des animations et l'économie de données arrêtent les effets ; les contenus restent visibles sans JavaScript.

Le « N » était le bouton d'outils de développement Next.js. `devIndicators: false` dans `C:\Users\Karim\Repositories\property-platform\apps\web\next.config.ts` le masque selon [la documentation officielle](https://nextjs.org/docs/app/api-reference/config/next-config-js/devIndicators). Les erreurs de compilation et journaux restent disponibles. Le badge n'est pas un élément de marque du site.

## Fichiers à modifier

La marque reste configurée séparément dans [BRANDING.md](BRANDING.md).

- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home.tsx` : sections serveur et destinations des boutons.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home-visual.tsx` : photo fixe du premier écran.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home-scenes.ts` : assets, cadrages et provenance photo.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home-experience.tsx` et `home-motion.ts` : comportement du défilement et calculs bornés.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home.module.css` : composition et boutons de l'accueil.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\explorer.tsx` et `explorer.module.css` : réglages de carte et fiche courte de sélection.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\pagination.tsx` et `page-window.ts` : pagination bornée, libellés et focus clavier.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\projects\directory.tsx` : formulaire GET et cartes de résultat.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\projects\project.module.css` : présentation commune de l'annuaire, de la fiche et de l'aperçu.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\components\ui-icon.tsx` : SVG partagés sans dépendance métier.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\globals.css` : thème partagé et variables de typographie.
- `C:\Users\Karim\Repositories\property-platform\apps\web\messages\<langue>.json` : textes localisés.

La composition de l'accueil, ses photos et l'exploration restent sous la responsabilité de la fonctionnalité `atlas`. L'annuaire et les fiches appartiennent à `projects` ; ils utilisent les contrats générés et les lectures serveur existantes. Les composants génériques et la typographie partagée n'importent aucun service métier ou client SQL. Aucun média décoratif n'est importé comme preuve immobilière.

## Vérification

Pour la refonte du 16 octobre : contrôler les parcours accueil → carte, accueil → projets, recherche/effacement/état vide de l'annuaire, sélection/fermeture/retour à la carte sur mobile, accès à la page projet et ouverture des environs. Refaire ces parcours en français et dans une locale RTL, vérifier focus et absence de débordement horizontal. Les tests unitaires de `page-window.ts`, les contrôles i18n, le typage et les vérifications HTTP du web compilé complètent cette revue. La capture d'écran ou la réussite d'un test ne certifie pas l'exactitude commerciale des sources.

Les tests de priorité cartographique couvrent le conflit entre RT4_TMP_PL2 et une vraie parcelle, le bâtiment devant sa parcelle, puis les secteurs/île en repli. Voir [REEM_MAP.md](REEM_MAP.md). Les contrôles HTTP du web compilé couvrent toutes les langues du registre, les trois images et les fontes incluses dans l'artefact, leurs tailles et le budget de préchargement. Les contrôles techniques ne remplacent pas une revue linguistique ou des mesures sur appareils physiques.

Vérification navigateur du 12 octobre 2026 : accueil anglais sur ordinateur, anglais/arabe à 390 × 844 sans débordement horizontal, lien vers les régions et polices réellement appliquées. Trois clics sur la carte connectée à PostGIS ouvrent respectivement la parcelle `RT4_C119`, le bâtiment `Leaf Tower` (OSM way 409874434), puis le secteur officiel `RT4` sur une zone sans bâtiment ni parcelle. Le périmètre `RT4_TMP_PL2` ne masque plus les objets précis.

Les builds locaux utilisent les dépendances verrouillées déjà installées. Le certificat PyPI/npm de l'environnement de reconstruction reste une limite distincte décrite dans [DEVELOPMENT.md](DEVELOPMENT.md). Ni l'API ni la base ne changent pour cette évolution de présentation et de sélection.

La sélection cartographique a ensuite évolué : secteurs et périmètres ne captent plus le clic, la caméra reste fixe à la sélection et le panneau affiche d’abord le bien. Voir [PROPERTY_EXPLORATION.md](PROPERTY_EXPLORATION.md) ; le test de secteur sélectionnable décrit plus haut correspond à l’étape précédente, remplacée par ce comportement. Les photos de bâtiments sont séparées des photographies décoratives de l’accueil.


## Pages projets et alentours — 16 octobre 2026

Depuis la revue UX du 21 octobre, l'identité, le promoteur, la livraison annoncée, le total qualifié et les types de biens précèdent une photo de taille bornée. Le dossier utilise deux colonnes au premier écran sur ordinateur, une colonne sur téléphone. Les documents et plans sont accessibles par une action interne, puis une section après les typologies ; les plans explicitement qualifiés sont distincts des brochures et fiches. L'absence de plan documenté reste visible. Une image de plan, brochure ou fiche n'est jamais traitée comme une photographie de couverture. Le repli d'ambiance utilise une seule image identifiée ; une galerie manuelle n'apparaît que pour plusieurs photographies de projet autorisées. Les photographies ne prouvent aucune vue ou prestation. Les informations d'achat non vérifiées restent visibles. Voir [la revue UX](UI_UX_REVIEW_20261021.md).

La carte d'alentours ne se charge qu'après activation et se limite au quartier de la fiche. Le [guide des fournisseurs](MAP_PROVIDERS.md) explique MapLibre, l'option Google Embed et sa clé dédiée. Les pages conservent leurs documents, faits et preuves ; cette refonte n'ajoute ni prix ni disponibilité.


Références visuelles consultées pour cette évolution : [Aldar](https://www.aldar.com/), [Modon](https://www.modon.com/) et [Emaar](https://www.emaar.com/en), pour leurs grands visuels et la hiérarchie entre destination, projet et action. Les compositions et fichiers de ces sites ne sont pas copiés ; les images de la plateforme conservent leur propre provenance.


**Confort mobile — 17 octobre 2026.** Lorsque la fiche recouvre le repère sélectionné sur téléphone, la caméra se déplace juste assez pour le rendre visible au-dessus, en conservant le niveau de zoom. Les déplacements manuels ultérieurs restent libres. Le plan Explore peut afficher son contexte dès sa réception, pendant que les pages de parcelles finissent de charger ; un échec partiel reste signalé et peut être relancé.


## Vérification de la carte immersive — 17 octobre 2026

Les 50 tests web, Biome, TypeScript et les liens des 39 documents passent. Le build Docker et les contrôles HTTP standalone couvrent les 16 langues. Le navigateur valide la fiche au clic, la fermeture avec Échap, les détails repliables, le niveau de zoom conservé et le repère visible au-dessus de la fiche mobile. Les vues française et arabe ont été contrôlées à 390 × 844, sans débordement de document ; Reem et Saadiyat sont accessibles. La carte de quartier de The District affiche les parcelles et permet de sélectionner RT3 · C50 avec son lien Onwani. Aucune erreur console n’a été observée dans ces parcours. Les adaptations de présentation réutilisent les données existantes, sans migration ni relance Prefect.

Le démarrage natif Windows reste empêché sur ce poste par la protection du cache SWC ; aucune protection n’a été abaissée. La prévisualisation compilée Docker sur 3102 et son accès privé Tailscale utilisent la dernière image web. Ces contrôles ne certifient pas tous les appareils ni une relecture linguistique de toutes les langues.


## Affinage Explore — 19 octobre 2026

Les couches par défaut sont parcelles, rues, bâtiments, lieux et noms ; secteurs et références cadastrales restent désactivés. Le clic privilégie les repères projets, puis les bâtiments/lieux/rues précis, les parcelles et enfin les secteurs activés. Le repère projet dispose d’une tolérance tactile de 8 px, indépendante du halo décoratif. Localiser conserve la fiche et recentre le bien. Le lien Marché est accessible dans l’en-tête et ouvre sa page dédiée ; les onglets flottants en bas et le bouton de retour à la sélection sont retirés. La légende devient une pastille fermée avec un panneau compact à la demande. Les données de contexte/sources et leurs anciennes URL restent disponibles.

Les fiches projets montrent d’abord une image approuvée ; à défaut, une photographie locale licenciée avec la mention explicite d’illustration, y compris pour les repères sans dossier canonique. Aucun visuel générique ne prétend représenter le projet. Les halos orange identifient des emplacements de projets ; ils ne représentent aucune transaction. Leur cycle dure 2,4 secondes, peut être désactivé dans les réglages, respecte le mouvement réduit et s’arrête en onglet masqué. Les calculs de noms possibles restent réversibles et distincts des sources ; voir la méthode dans [REPOSITORY.md](REPOSITORY.md).

Validation du lot : 54 tests web, Biome, typage/build Docker et contrôles HTTP standalone des 16 langues réussis. Le navigateur vérifie le clic projet devant sa parcelle, la localisation conservant la fiche pour The District et Rixos, le volet Market conservant la sélection, les réglages par défaut et leur pause d’animation, la légende repliable et la carte de quartier. Contrôles à 320/390 px, arabe RTL et vietnamien (Saadiyat), sans débordement de document ni erreur console observée. Les commandes RTL et le libellé accessible du sélecteur mobile ont été corrigés après revue visuelle. Aucune migration, collecte ou modification de données nécessaire pour ce lot. Ces contrôles ne remplacent pas une revue linguistique native ou des essais sur tous les appareils.


**Page Marché et menu Vue — 19 octobre 2026.** Le lien Marché ouvre une page dédiée avec les filtres Abu Dhabi/Reem/Saadiyat, une grille de ventes, la recherche et les indices déjà disponibles ; aucune lecture de marché ne reste dans Explore. Les anciennes URL `tab=market` redirigent en conservant le territoire. Le bouton Toute la zone est retiré de la carte, qui garde son sélecteur territorial. Vue ouvre un panneau au-dessus de la commande en bas à gauche : deux choix radio plan/satellite, puis source et preuves d’imagerie. Les illustrations des choix sont des pictogrammes décoratifs, pas des captures satellites. La légende occupe le coin inférieur droit. Les commandes conservent leurs coins physiques en RTL, adaptent le texte et se placent au-dessus de la fiche sur téléphone. Le menu Vue se ferme avec Échap, un clic extérieur ou l’ouverture d’un autre réglage ; ses transitions respectent le mouvement réduit.

Validation de cette évolution : 54 tests web, Biome, TypeScript et build Docker réussis. Les contrôles HTTP standalone couvrent la page Marché et les redirections historiques dans les 16 langues. Vérifications navigateur : grille ADREC, filtres Reem et recherche Radiant, passage plan/satellite, fermeture par Échap avec retour du focus, exclusivité des panneaux, maintien de la fiche projet, largeurs 320/390/820 px et arabe RTL. Aucun débordement horizontal ni erreur console observé. Vue et légende réservent la hauteur réelle du rail des crédits, mesurée par `parcel-map.tsx`, pour ne pas masquer les attributions d’imagerie. Les données et pipelines existants sont inchangés.
