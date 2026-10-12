# Identité visuelle de Property Platform

Accueil épuré du 12 octobre 2026 : bleu encre, ivoire et sable, photographies des Émirats, titres éditoriaux et commandes d'exploration. L'accueil présente les régions et leurs alentours. Les preuves et sources immobilières restent dans la carte et les fiches ; le grand bandeau « Data & sources » de l'accueil a été retiré.

## Photographies et droits

Les photos servent d'ambiance éditoriale. Elles ne représentent pas un bien sélectionné et ne prouvent pas une couverture de données hors du pilote Al Reem. Voir [UAE_COVERAGE.md](UAE_COVERAGE.md).

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

`C:\Users\Karim\Repositories\property-platform\apps\web\src\theme\fonts.ts` possède la sélection des préchargements par langue. Le layout serveur émet les liens vers les mêmes URL publiques que le CSS, pour éviter de télécharger une seconde copie. Budget initial des fontes préchargées : 62 476 octets pour les langues latines, 60 504 pour le russe, 190 796 pour le RTL et 24 836 pour les autres écritures (marque/codes latins). Un contenu mêlant plusieurs écritures peut charger un autre sous-ensemble au besoin.

Les variables `--font-ui` et `--font-display` de `globals.css` permettent de changer les familles. Le sens RTL est conservé, les lettres arabes ne sont pas espacées artificiellement et les photos ne sont pas retournées.

## Boutons, couleurs et composition

Références visuelles consultées : [Dubai Sotheby's International Realty](https://sothebysrealty.ae/) pour les compositions photographiques et les titres serif, [Aman Residences](https://www.aman.com/residences) pour l'ivoire et l'espace. Nous conservons une composition et des assets propres au projet.

Le bouton principal associe une surface ivoire, une bordure lumineuse, des ombres superposées et une flèche dans un médaillon bleu encre. L'action secondaire permet de choisir un émirat. Le survol déplace légèrement les commandes sur pointeur précis ; le clic produit un enfoncement. Le focus clavier reste visible. Les couleurs sémantiques de la légende cartographique gardent leur signification métier.

| Couleur | Variable | Usage |
|---|---|---|
| `#0B2132` | `--ink` | Texte et fonds bleu encre |
| `#F8F5EE` | `--ivory` | Surfaces de lecture |
| `#D2B895` | `--sand` | Accents et contours |
| `#59656C` | `--muted-ink` | Texte secondaire |
| `#D9D3C9` | `--rule` | Séparateurs |

Le rayon, la durée et les ombres partagés restent dans `--control-*` de `globals.css`. Les variantes de l'accueil sont dans `home.module.css`. Aucune bibliothèque d'animation n'est ajoutée.

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
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\globals.css` : thème partagé et variables de typographie.
- `C:\Users\Karim\Repositories\property-platform\apps\web\messages\<langue>.json` : textes localisés.

La composition et les photos restent sous la responsabilité de la fonctionnalité `atlas`. La typographie partagée appartient à `theme`, sans dépendance à l'API. Aucun média décoratif n'est importé comme preuve immobilière.

## Vérification

Les tests de priorité cartographique couvrent le conflit entre RT4_TMP_PL2 et une vraie parcelle, le bâtiment devant sa parcelle, puis les secteurs/île en repli. Voir [REEM_MAP.md](REEM_MAP.md). Les contrôles HTTP du web compilé couvrent les quinze langues, les trois images et les fontes incluses dans l'artefact, leurs tailles et le budget de préchargement. Les contrôles techniques ne remplacent pas une revue linguistique ou des mesures sur appareils physiques.

Vérification navigateur du 12 octobre 2026 : accueil anglais sur ordinateur, anglais/arabe à 390 × 844 sans débordement horizontal, lien vers les régions et polices réellement appliquées. Trois clics sur la carte connectée à PostGIS ouvrent respectivement la parcelle `RT4_C119`, le bâtiment `Leaf Tower` (OSM way 409874434), puis le secteur officiel `RT4` sur une zone sans bâtiment ni parcelle. Le périmètre `RT4_TMP_PL2` ne masque plus les objets précis.

Les builds locaux utilisent les dépendances verrouillées déjà installées. Le certificat PyPI/npm de l'environnement de reconstruction reste une limite distincte décrite dans [DEVELOPMENT.md](DEVELOPMENT.md). Ni l'API ni la base ne changent pour cette évolution de présentation et de sélection.
