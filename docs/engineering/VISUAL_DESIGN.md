# Identité visuelle de Property Platform

Refonte de l'accueil du 12 octobre 2026 : photographies plein écran, bleu encre, ivoire, sable et titres éditoriaux. Le défilement relie le paysage, la découverte des couches et les sept émirats. L'exploration garde des fonds clairs pour lire les données et la légende.

## Photos et droits

Les trois photographies montrent Dubai et Abu Dhabi. Elles servent d'ambiance éditoriale ; elles ne représentent pas une parcelle sélectionnée et ne prouvent ni l'état actuel d'un bâtiment ni une couverture de données hors Al Reem. L'accueil présente les sept émirats depuis le 12 octobre ; voir [la couverture nationale](UAE_COVERAGE.md).

| Fichier, sous `apps/web/public/images/uae/` | Photographe | Page source |
|---|---|---|
| `dubai-night-768.webp`, `dubai-night-1920.webp` | Alla Rome | [Dubai JBR, lumières à la tombée du jour](https://unsplash.com/photos/the-skyline-of-a-large-city-at-night-lODmPrkAxM8) |
| `abu-dhabi-coast-768.webp`, `abu-dhabi-coast-1920.webp` | Hanks K | [Plage et palmiers à Abu Dhabi](https://unsplash.com/photos/beach-palm-trees-and-resort-under-a-hazy-sky-_c08bbHy-xg) |
| `abu-dhabi-sunset-768.webp`, `abu-dhabi-sunset-1920.webp` | Yulia Evtushenko | [Palmiers au coucher du soleil, Corniche Beach](https://unsplash.com/photos/a-couple-of-palm-trees-sitting-next-to-each-other-MhpX3VgaG4U) |

Licence gratuite [Unsplash](https://unsplash.com/license), vérifiée sur les pages des trois photos le 12 octobre 2026. Les crédits cliquables restent visibles dans le bandeau. Les variantes WebP sont des exports optimisés du fournisseur ; les photos ne sont pas générées par IA. Les images et leur manifeste `credits.json` sont suivis dans Git pour rendre le site indépendant d'un serveur de photos tiers lors de la navigation.

## Où modifier le thème

Le nom affiché et le symbole sont indépendants des styles : [BRANDING.md](BRANDING.md) décrit leur configuration commune sous `packages/branding/` et le fichier `apps/web/public/brand/mark.svg`.

- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home.tsx` : contenu serveur, boutons vers la carte et section sources.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home-gallery.tsx` : diaporama léger, sélection et pause.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home-experience.tsx` : gestion du défilement, apparitions, préférences et nettoyage des écouteurs.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home-motion.ts` : déplacements bornés des photos et du texte, avec amplitudes plus faibles sur téléphone.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home-scenes.ts` : ordre des photos, cadrage, auteur et URL source.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home.module.css` : styles propres à l'accueil.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\globals.css` : en-tête et styles partagés avec la carte.
- `C:\Users\Karim\Repositories\property-platform\apps\web\messages\<langue>.json` : textes du namespace `Home` dans les quinze langues.

Le propriétaire reste la fonctionnalité web `atlas`. Ces médias décoratifs n'entrent pas dans les tables de preuves immobilières. Aucun nouveau service ou domaine backend n'est nécessaire.

## Boutons et références de design

Références visuelles consultées le 12 octobre 2026 : [Dubai Sotheby's International Realty](https://sothebysrealty.ae/) pour sa composition photographique, le contraste bleu/blanc et les titres serif ; [Aman Residences](https://www.aman.com/residences) pour les fonds ivoire, la typographie éditoriale et les espaces généreux. [Knight Frank](https://www.knightfrank.com/) a aussi été consulté comme référence de navigation immobilière internationale. Il s'agit d'observations de leurs sites officiels, sans classement prétendant établir lesquels seraient « les meilleurs du monde ». Nous ne reprenons ni leurs photos, ni leurs logos, ni leurs textes.

Property Platform utilise une finition propre : bouton principal ivoire avec bord sable, petit médaillon pour la flèche, ombres superposées et action secondaire translucide. Les rayons plus courts et les traits fins remplacent les contours très arrondis de l'ancien accueil. Les commandes du diaporama montrent leur sélection avec un fond et un contour. Les boutons de la carte gardent un relief plus léger, adapté à la lecture des données ; sélectionner une fiche ne change pas son épaisseur de bordure et ne déplace donc pas les fiches voisines.

| Couleur | Variable de l'accueil | Usage |
|---|---|---|
| `#0B2132` | `--ink` | Texte, fonds bleu encre, carte du territoire pilote |
| `#F8F5EE` | `--ivory` | Grandes surfaces de lecture |
| `#D2B895` | `--sand` | Accents sur photos et contours |
| `#59656C` | `--muted-ink` | Texte secondaire sur fond clair |
| `#D9D3C9` | `--rule` | Séparateurs et bordures |

Ces variables sont regroupées au début de `home.module.css`. Le thème partagé utilise `--accent`, `--muted` et `--line` dans `globals.css`. Les couleurs sémantiques de la légende parcellaire conservent leur sens métier.

Les variables `--control-*` de `globals.css` centralisent le rayon, la durée, la courbe de transition et les ombres partagées. Les variantes propres à l'accueil restent dans `home.module.css`. Aucun paquet d'animation n'est ajouté. Le verre conserve un fond coloré lorsque le navigateur ne prend pas en charge le flou.

Les effets de survol qui déplacent les boutons sont réservés aux pointeurs précis disposant du survol. Le clic produit un léger enfoncement ; le focus clavier garde un contour visible, y compris sur les photos. Les contrôles désactivés ne prennent pas l'effet de survol. Avec `prefers-reduced-motion`, les déplacements sont supprimés et les transitions de contrôle deviennent immédiates. Les dimensions, espacements logiques et libellés traduits restent compatibles avec le mobile et le RTL.

## Animation, accessibilité et transfert

Le bandeau ne monte que la photo de Dubai au départ, prioritaire : 71 904 octets sur mobile ou 381 392 octets sur ordinateur. Les autres scènes du diaporama sont montées à leur première sélection ou à leur premier passage automatique. La photo côtière de la section suivante est présente dans le HTML avec `loading="lazy"` ; le navigateur décide quand la charger et réutilise la même ressource si elle est sélectionnée dans le bandeau. La variante 768 pixels est choisie jusqu'à une largeur de 700 pixels. Il n'y a ni vidéo automatique, ni bibliothèque d'animation, ni téléchargement de police externe.

Le paysage du bandeau glisse jusqu'à 150 pixels sur ordinateur, 80 sur mobile ; le texte se déplace moins vite et s'atténue légèrement. La photo côtière a son propre déplacement, jusqu'à 60 pixels sur ordinateur et 28 sur téléphone. Sur ordinateur, son cadre utilise `position: sticky` pendant une partie de la section. Sur téléphone, le cadre reste dans le flux normal. Le zoom du diaporama va de 1,01 à 1,06 et se suspend avec la lecture, le survol, le focus ou un onglet masqué.

Le défilement reste celui du navigateur. Le lien « Scroll to discover », traduit dans les quinze langues, utilise une ancre native ; le défilement fluide est désactivé avec la réduction des animations. Les apparitions utilisent [Intersection Observer](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API), puis cessent d'observer l'élément révélé. Un focus clavier révèle immédiatement le contenu concerné. Tous les contenus sont visibles dans le HTML initial ; seuls les éléments encore sous l'écran sont préparés pour une apparition après activation du script.

Les déplacements sont calculés dans une seule tâche `requestAnimationFrame` déclenchée par un défilement ou redimensionnement, avec lecture des deux cadres avant écriture des variables CSS. Il n'y a pas de boucle JavaScript permanente ni de rendu React à chaque pixel. Les déplacements utilisent `transform` et l'atténuation `opacity`. Le calcul borne les valeurs pour garder les photos dans leurs cadres. La préférence de réduction des animations et, quand disponible, l'économie de données arrêtent la parallaxe et les apparitions. Un changement de préférence est appliqué immédiatement ; écouteurs et observateur sont retirés au démontage. Le rendu statique reste disponible sans Intersection Observer. Nous n'exigeons pas `animation-timeline` : sa [compatibilité reste limitée](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/animation-timeline).

Le passage automatique attend le chargement de la photo et 8,5 secondes de lecture. Le visuel précédent reste affiché pendant le chargement suivant. Une sélection manuelle arrête la lecture automatique ; le bouton lecture permet de la reprendre. Le focus dans la galerie, son survol et un onglet masqué suspendent la rotation. `prefers-reduced-motion` et, lorsqu'il est disponible, le mode économie de données désactivent le démarrage automatique. Les changements de préférence et le retour d'une image déjà en cache sont pris en compte.

Les images de fond ont un texte alternatif vide, avec une légende et un crédit accessibles à côté. Les commandes sont de vrais boutons avec noms traduits et état de sélection. Les photos ne sont pas retournées en RTL. Les marges, contrôles et textes suivent le sens de lecture ; les noms des photographes sont isolés avec `bdi`.

La page reste précompilée. L'enveloppe d'effets, la galerie et le sélecteur de langue sont interactifs ; le texte et les sections viennent du serveur. Ouvrir l'accueil ne charge ni MapLibre ni les données géographiques. Tester téléphone, RTL, boutons, défilement, lien vers la carte et fichiers statiques après une modification. `apps/web/tests/home-motion.test.mjs` vérifie les limites de déplacement, les valeurs sur téléphone et les cadres de taille nulle ; le smoke test du site compilé vérifie les quinze langues, l'ancre et la seule image prioritaire. Les tests techniques ne remplacent pas la relecture linguistique ou une revue d'accessibilité complète.

## Vérification de cette refonte

Le 12 octobre 2026 : TypeScript, Biome et les huit tests web passent ; le site compilé passe le smoke test dans les quinze langues. La compilation Next a utilisé les dépendances verrouillées déjà installées dans le runtime local, sans téléchargement. Cela ne constitue pas une nouvelle validation de leur installation depuis zéro ; les limites de certificats du poste restent décrites dans [DEVELOPMENT.md](DEVELOPMENT.md).

Dans le navigateur : accueil anglais sur ordinateur, changement de photo, ancre de découverte et déplacement effectif du fond ; arabe sur un écran de 390 × 844, image de 768 pixels et absence de débordement horizontal ; navigation vers Sharjah avec sa couverture en préparation et retour vers le pilote Al Reem avec 2 431 parcelles et sa légende. La réduction des animations est prévue dans le code et le CSS ; l'émulation de cette préférence et une mesure de fluidité sur téléphones physiques restent à faire. Les contrôles backend/GIS n'ont pas été relancés pour cette modification de présentation, qui ne change ni l'API ni la base.
