# Identité visuelle de Liwa Atlas

Refonte de l'accueil du 12 octobre 2026 : photographies plein écran, bleu profond, sable, accents dorés et titres éditoriaux. L'exploration garde des fonds clairs pour lire les données et la légende.

## Photos et droits

Les trois photographies montrent Abu Dhabi. Elles servent d'ambiance éditoriale ; elles ne représentent pas une parcelle sélectionnée et ne prouvent ni l'état actuel d'un bâtiment ni une couverture de données hors Al Reem.

| Fichier, sous `apps/web/public/images/uae/` | Photographe | Page source |
|---|---|---|
| `abu-dhabi-night-768.webp`, `abu-dhabi-night-1920.webp` | Kevin JD | [Corniche Breakwater, skyline de nuit](https://unsplash.com/photos/city-skyline-during-night-time-S5SQzWdUhoE) |
| `abu-dhabi-coast-768.webp`, `abu-dhabi-coast-1920.webp` | Hanks K | [Plage et palmiers à Abu Dhabi](https://unsplash.com/photos/beach-palm-trees-and-resort-under-a-hazy-sky-_c08bbHy-xg) |
| `abu-dhabi-sunset-768.webp`, `abu-dhabi-sunset-1920.webp` | Yulia Evtushenko | [Palmiers au coucher du soleil, Corniche Beach](https://unsplash.com/photos/a-couple-of-palm-trees-sitting-next-to-each-other-MhpX3VgaG4U) |

Licence gratuite [Unsplash](https://unsplash.com/license), vérifiée sur les pages des trois photos le 12 octobre 2026. Les crédits cliquables restent visibles dans le bandeau. Les variantes WebP sont des exports optimisés du fournisseur ; les photos ne sont pas générées par IA. Les images et leur manifeste `credits.json` sont suivis dans Git pour rendre le site indépendant d'un serveur de photos tiers lors de la navigation.

## Où modifier le thème

- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home.tsx` : contenu serveur, boutons vers la carte et section sources.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home-gallery.tsx` : diaporama léger, sélection et pause.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home-scenes.ts` : ordre des photos, cadrage, auteur et URL source.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home.module.css` : styles propres à l'accueil.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\globals.css` : en-tête et styles partagés avec la carte.
- `C:\Users\Karim\Repositories\property-platform\apps\web\messages\<langue>.json` : textes du namespace `Home` dans les quinze langues.

Le propriétaire reste la fonctionnalité web `atlas`. Ces médias décoratifs n'entrent pas dans les tables de preuves immobilières. Aucun nouveau service ou domaine backend n'est nécessaire.

## Animation, accessibilité et transfert

Le premier écran ne monte que la photo de nuit, prioritaire : 65 194 octets sur mobile ou 309 022 octets sur ordinateur. Les autres scènes sont chargées à leur première sélection ou à leur premier passage automatique ; la variante 768 pixels est choisie jusqu'à une largeur de 700 pixels. Les transitions changent l'opacité, sans bibliothèque d'animation, vidéo ou téléchargement de police externe.

Le passage automatique attend le chargement de la photo et 8,5 secondes de lecture. Le visuel précédent reste affiché pendant le chargement suivant. Une sélection manuelle arrête la lecture automatique ; le bouton lecture permet de la reprendre. Le focus dans la galerie, son survol et un onglet masqué suspendent la rotation. `prefers-reduced-motion` et, lorsqu'il est disponible, le mode économie de données désactivent le démarrage automatique. Les changements de préférence et le retour d'une image déjà en cache sont pris en compte.

Les images de fond ont un texte alternatif vide, avec une légende et un crédit accessibles à côté. Les commandes sont de vrais boutons avec noms traduits et état de sélection. Les photos ne sont pas retournées en RTL. Les marges, contrôles et textes suivent le sens de lecture ; les noms des photographes sont isolés avec `bdi`.

La page reste précompilée. Seule la petite galerie et le sélecteur de langue sont interactifs ; ouvrir l'accueil ne charge ni MapLibre ni les données géographiques. Tester téléphone, RTL, boutons, lien vers la carte et fichiers statiques après une modification. Les tests techniques ne remplacent pas la relecture linguistique ou une revue d'accessibilité complète.
