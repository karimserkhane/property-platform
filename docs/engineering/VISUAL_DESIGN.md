# Identité visuelle de Property Platform

Refonte de l'accueil du 12 octobre 2026 : photographies plein écran, bleu profond, sable, accents dorés et titres éditoriaux. L'exploration garde des fonds clairs pour lire les données et la légende.

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
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home-scenes.ts` : ordre des photos, cadrage, auteur et URL source.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home.module.css` : styles propres à l'accueil.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\globals.css` : en-tête et styles partagés avec la carte.
- `C:\Users\Karim\Repositories\property-platform\apps\web\messages\<langue>.json` : textes du namespace `Home` dans les quinze langues.

Le propriétaire reste la fonctionnalité web `atlas`. Ces médias décoratifs n'entrent pas dans les tables de preuves immobilières. Aucun nouveau service ou domaine backend n'est nécessaire.

## Boutons et références de design

Références visuelles consultées le 12 octobre 2026 : [Apple](https://www.apple.com/), [Aman Residences](https://www.aman.com/residences) et [Emaar](https://www.emaar.com/en). Apple distingue ses actions principales pleines et secondaires à contour ; Aman privilégie des liens discrets et une composition aérée ; Emaar emploie notamment des surfaces translucides sur une photographie. Ces sites ne servent pas de modèles à copier. Le bouton principal observé chez Apple n'a pas d'ombre.

Property Platform utilise sa propre finition : dégradé sable et or, reflet ponctuel au survol, petit médaillon pour la flèche, ombres superposées et action secondaire en verre dépoli. Les commandes du diaporama montrent leur sélection avec un fond et un contour. Les boutons de la carte reprennent un relief plus léger, adapté à la lecture des données ; sélectionner une fiche ne change plus son épaisseur de bordure et ne déplace donc pas les fiches voisines.

Les variables `--control-*` de `globals.css` centralisent le rayon, la durée, la courbe de transition et les ombres partagées. Les variantes propres à l'accueil restent dans `home.module.css`. Aucun paquet ou code JavaScript d'animation n'est ajouté. Le verre conserve un fond coloré lorsque le navigateur ne prend pas en charge le flou.

Les effets de survol qui déplacent les boutons sont réservés aux pointeurs précis disposant du survol. Le clic produit un léger enfoncement ; le focus clavier garde un contour visible, y compris sur les photos. Les contrôles désactivés ne prennent pas l'effet de survol. Avec `prefers-reduced-motion`, le reflet et les déplacements sont supprimés, et les transitions de contrôle deviennent immédiates. Les dimensions, espacements logiques et libellés traduits restent compatibles avec le mobile et le RTL.

## Animation, accessibilité et transfert

Le premier écran ne monte que la photo de Dubai, prioritaire : 71 904 octets sur mobile ou 381 392 octets sur ordinateur. Les autres scènes sont chargées à leur première sélection ou à leur premier passage automatique ; la variante 768 pixels est choisie jusqu'à une largeur de 700 pixels. Les transitions changent l'opacité, sans bibliothèque d'animation, vidéo ou téléchargement de police externe.

Le passage automatique attend le chargement de la photo et 8,5 secondes de lecture. Le visuel précédent reste affiché pendant le chargement suivant. Une sélection manuelle arrête la lecture automatique ; le bouton lecture permet de la reprendre. Le focus dans la galerie, son survol et un onglet masqué suspendent la rotation. `prefers-reduced-motion` et, lorsqu'il est disponible, le mode économie de données désactivent le démarrage automatique. Les changements de préférence et le retour d'une image déjà en cache sont pris en compte.

Les images de fond ont un texte alternatif vide, avec une légende et un crédit accessibles à côté. Les commandes sont de vrais boutons avec noms traduits et état de sélection. Les photos ne sont pas retournées en RTL. Les marges, contrôles et textes suivent le sens de lecture ; les noms des photographes sont isolés avec `bdi`.

La page reste précompilée. Seule la petite galerie et le sélecteur de langue sont interactifs ; ouvrir l'accueil ne charge ni MapLibre ni les données géographiques. Tester téléphone, RTL, boutons, lien vers la carte et fichiers statiques après une modification. Les tests techniques ne remplacent pas la relecture linguistique ou une revue d'accessibilité complète.
