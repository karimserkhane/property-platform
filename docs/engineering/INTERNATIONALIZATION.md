# Langues, traduction et mise en page

**Actualisation du 15 octobre 2026 :** les identités promoteur/projet, snapshots typés, typologies, équipements et références PDF/vidéo sont implémentés. Le [guide PROJECTS.md](PROJECTS.md) décrit les nouvelles tables, sources et pipelines, les captures externes pour gros fichiers et les pages traduites. Les offres de logements, plans de paiement, transcodages et traductions automatiques restent un lot ultérieur.

## Décision

L'anglais est la langue par défaut demandée par l'utilisateur. Le registre propose seize langues : anglais, arabe, espagnol, allemand, russe, hindi, ourdou, bengali, malayalam, tamoul, filipino, persan, chinois simplifié, français, portugais et vietnamien. Le vietnamien, ajouté le 16 octobre 2026 à la demande de l'utilisateur, utilise le code `vi`, le nom **Tiếng Việt** et le sens `ltr`.

Cette liste est une sélection de couverture et de marché, **pas un classement statistique des langues les plus parlées aux Émirats**. Le guide officiel Visit Dubai atteste l'usage de l'arabe et de l'anglais, et mentionne notamment russe, tagalog, hindi, ourdou et portugais. Un document Emirates Driving Institute fournit un autre indice de besoins linguistiques, notamment bangla, chinois, farsi, hindi, malayalam, russe et tamoul ; il est ancien et ne mesure pas le nombre de locuteurs. Espagnol et allemand sont ajoutés à la demande de l'utilisateur ; français complète les publics visés. Le filipino est ici la variante d'interface choisie pour le public philippin, sans assimiler toutes ses langues au tagalog.

[Visit Dubai — langues](https://www.visitdubai.com/plan-your-trip/practical-information), [EDI — interprétation des tests, document historique](https://edi-uae.com/public/uploads/editor-images/files/RIS.pdf).

Les textes de l'accueil, de l'exploration locale et du sélecteur sont traduits. Ce sont des traductions initiales à faire relire par des locuteurs compétents avant publication commerciale, notamment pour les termes immobiliers. Les tests vérifient cohérence et rendu, pas la qualité linguistique d'une traduction. Les codes de parcelles et noms officiels restent dans leur forme d'origine ; leur présence dans une interface arabe ne signifie pas qu'une traduction documentaire a été validée.

## Implémentation

- `C:\Users\Karim\Repositories\property-platform\apps\web\src\i18n\locales.ts` : registre unique des codes, noms dans leur langue, sens de lecture, profils de police et langue par défaut. Le sélecteur, les routes statiques et les contrôles HTTP en dérivent leur liste ; aucune liste de langues n'est recopiée dans les pages.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\i18n\routing.ts` et `C:\Users\Karim\Repositories\property-platform\apps\web\src\proxy.ts` : routes préfixées, par exemple `/en`, `/ar`, `/ru`.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\i18n\request.ts` : chargement serveur du seul dictionnaire nécessaire et fuseau d'affichage par défaut `Asia/Dubai`.
- `C:\Users\Karim\Repositories\property-platform\apps\web\messages\<locale>.json` : messages organisés par fonctionnalité. Aucun texte d'interface n'est dupliqué dans chaque page.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\[locale]\` : layout et pages localisés, rendus statiquement lorsque possible.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\components\language-switcher.tsx` : sélection explicite, conservation du chemin, des paramètres de recherche et de l'ancre.

`/` redirige vers `/en`, même si le navigateur préfère une autre langue. Nous désactivons la détection automatique et le cookie de langue pour respecter ce défaut explicite. Une langue choisie reste portée par l'URL ; revenir à `/` revient à l'anglais. Une éventuelle préférence persistante de compte devra être décidée et testée séparément.

Le routage et les traductions utilisent next-intl, compatible avec Next.js App Router. La configuration utilise `next/root-params`, disponible dans la version Next.js du dépôt, plutôt qu'une implémentation maison de négociation linguistique. Les messages utiles au serveur restent côté serveur ; le provider client reçoit seulement le namespace du sélecteur. Les titres, textes et liens de l'accueil sont traduits lors du rendu serveur. Les trois photographies décoratives restent dans leurs sections respectives, sans galerie à commandes ni libellés de lecture/pause à envoyer au client. L'accueil privilégie l'exploration et les régions ; les sources immobilières restent traduites et consultables dans la carte et les fiches.

[Routage next-intl](https://next-intl.dev/docs/routing/setup), [configuration de la détection](https://next-intl.dev/docs/routing/configuration).

## Polices et couverture des écritures

Les textes d'interface utilisent **Manrope**, les titres **Cormorant Garamond** et les interfaces arabe, ourdou et persan **Noto Sans Arabic**. Les autres écritures utilisent les polices de secours du système. Ce choix ne traduit pas le contenu immobilier : les codes et textes d'origine restent conservés.

Les fichiers WOFF2, les licences SIL Open Font License et leur provenance sont sous `C:\Users\Karim\Repositories\property-platform\apps\web\public\fonts\`. Le fichier `fonts.css` y définit les familles et leurs plages Unicode ; `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\globals.css` l'importe et expose les variables `--font-ui` et `--font-display`. `font-display: swap` permet de lire le texte avant que la police soit chargée. Les fichiers sont servis par le site : la navigation n'appelle pas Google Fonts.

`C:\Users\Karim\Repositories\property-platform\apps\web\src\theme\fonts.ts` définit les profils de préchargement. Le registre associe une langue à un profil ; le layout transmet ce profil à `getFontPreloads`, sans condition spécifique à une langue dans les pages. Les profils latin, cyrillique, arabe, système et vietnamien réutilisent les mêmes fichiers. Le vietnamien ajoute les sous-ensembles officiels Manrope et Cormorant Garamond couvrant notamment `ă`, `đ`, `ơ`, `ư` et les voyelles accentuées : le latin de base seul ne suffit pas. Les autres écritures préchargent seulement Manrope latin pour la marque et les codes. Le CSS peut charger un autre sous-ensemble lorsque le texte affiché le nécessite ; un préchargement ne définit donc pas à lui seul toutes les polices utilisées dans la page. Le manifeste `credits.json` contient les versions, tailles et empreintes exactes ; le [guide du thème](VISUAL_DESIGN.md) donne les budgets initiaux.

## RTL et accessibilité

Arabe (`ar`), ourdou (`ur`) et persan (`fa`) utilisent `dir="rtl"` ; les autres utilisent `ltr`. `html.lang` correspond à la route. Utiliser marges/paddings/dimensions logiques et `text-align: start`, pas une inversion arbitraire de toute l'interface. Ne pas espacer les lettres arabes comme un titre latin.

Les noms des langues sont affichés dans leur propre écriture, sans drapeaux assimilant langue et nationalité. Le sélecteur possède un libellé accessible et reste utilisable au clavier. Les marques, références de parcelle, nombres et codes doivent être isolés avec `bdi` ou un sens explicite lorsque nécessaire. La carte, les photos et les plans ne sont pas retournés horizontalement en RTL ; les panneaux et contrôles seront adaptés séparément.

Les commandes natives MapLibre (zoom, retour au nord et crédits) reçoivent aussi les messages du namespace `Map`, via l'adaptateur partagé de `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\map-style.ts`. Le canvas reçoit le titre traduit. Chaque instance de carte est liée à sa locale pour que les libellés natifs soient repris lors d'un changement de langue, sans modifier les noms géographiques de la source.

Les contrôles techniques actuels vérifient toutes les routes, le sens de lecture, les textes traduits, le sélecteur et les fichiers CSS du serveur compilé. Ils ne certifient pas encore la navigation assistée, tous les appareils ni les futures interactions cartographiques. Ces parcours feront l'objet de tests avec la tranche pilote.

## Interface et contenu immobilier sont deux problèmes distincts

La marque affichée est une valeur publique de `packages/branding/src/brand.ts`, isolée avec `bdi` et commune aux langues. Les textes d'interface et les noms de lieux restent traduits dans les dictionnaires ; aucune copie du nom commercial dans les dictionnaires n'est nécessaire. Un éventuel nom commercial différent par langue nécessitera une configuration explicite, sans modifier les identités métier.

Traduire l'interface ne traduit pas automatiquement les brochures, plans, avis ou preuves. Conserver le texte original, son code de langue BCP 47, sa version et ses droits. Une traduction dérivée référence le document ou l'assertion d'origine, sa méthode/modèle, sa date, son statut de revue et la version traduite. Une nouvelle source invalide les traductions qui ne correspondent plus à sa version.

Les identifiants de projet/bâtiment/unité restent communs à toutes les langues. Les noms officiels sont conservés ; alias et noms d'affichage validés facilitent la recherche. Les résumés IA indiquent leur langue et leur provenance. Un texte original peut être présenté avec `lang` et `dir="auto"` sans inventer une traduction manquante.

Les messages d'API utilisent des codes stables et des paramètres typés ; l'interface les traduit. Les données numériques restent des nombres/montants décimaux, les dates machine au format défini et en UTC. Affichage avec Intl/next-intl ; la langue ne convertit pas implicitement la devise AED ni les conventions de surface. Les caches de texte dérivé doivent être séparés par langue, version et droits.

Le prototype reste `noindex`. Le routage fournit les alternatives linguistiques ; domaine canonique, sitemap et politique de publication des traductions validées seront définis avant mise en ligne.

Les premières fiches de biens utilisent les libellés Map traduits dans toutes les langues du registre. Les résumés et légendes de sources gardent leur langue d’origine (`lang` et `dir="auto"`) ; ils ne sont pas présentés comme des traductions validées. Les identifiants, crédits de licence et noms de fournisseurs restent communs à toutes les langues. Voir [PROPERTY_EXPLORATION.md](PROPERTY_EXPLORATION.md).

## Ajouter une langue sans disperser sa configuration

1. Ajouter une entrée au registre `C:\Users\Karim\Repositories\property-platform\apps\web\src\i18n\locales.ts` : code BCP 47, nom natif, direction et `fontProfile`. Les routes, alternatives, sélecteur et métadonnées utilisent ensuite cette entrée.
2. Créer `C:\Users\Karim\Repositories\property-platform\apps\web\messages\<locale>.json` avec exactement les mêmes clés que `en.json`, en conservant les paramètres ICU. Traduire tous les namespaces utilisés, dont carte, usages, marché, contexte et projets ; laisser les preuves originales inchangées.
3. Vérifier la couverture des caractères et des majuscules dans les polices. Si un sous-ensemble manque, ajouter le fichier sous `C:\Users\Karim\Repositories\property-platform\apps\web\public\fonts\`, ses plages officielles dans `fonts.css` et sa licence/provenance/empreinte dans `credits.json`. Réutiliser ou compléter un profil dans `C:\Users\Karim\Repositories\property-platform\apps\web\src\theme\fonts.ts` ; ne pas ajouter de conditions de langue dans les composants.
4. Depuis `C:\Users\Karim\Repositories\property-platform`, lancer `pnpm.cmd test:web`, `pnpm.cmd lint`, `pnpm.cmd docs:check`, puis le build et `pnpm.cmd smoke:web` décrits dans [DEVELOPMENT.md](DEVELOPMENT.md). Les tests contrôlent les clés et le format ICU de chaque dictionnaire ; ils vérifient aussi la normalisation NFC du vietnamien, la couverture de ses accents et les fichiers de police. Le contrôle HTTP parcourt toutes les langues du registre. Si les données sont importées et le site compilé est démarré sur 3102, `node scripts/smoke-projects.mjs` vérifie aussi chaque fiche dans toutes ces langues.
5. Contrôler dans le navigateur l'accueil, l'annuaire, une fiche peuplée dans la carte et sur sa page, les dates/nombres, le sélecteur conservant recherche/ancre, le clavier et une largeur de téléphone. Faire relire la traduction avant publication commerciale. Actualiser ce guide et les descriptions courantes ; les comptes rendus de tests datés restent historiques.

Une langue d'interface supplémentaire ne nécessite ni migration SQL, ni réimportation, ni nouveau pipeline Prefect. En développement, le serveur web lit les fichiers modifiés ; pour l'aperçu Docker sur 3102 et l'accès distant, reconstruire le web puis reprendre la procédure du [guide de prévisualisation](REMOTE_PREVIEW.md). L'anglais reste le défaut et le contenu des sources n'est pas traduit implicitement.

## Validation du vietnamien — 16 octobre 2026

Les 282 messages couvrent les neuf namespaces de l'interface. Les 41 tests web, TypeScript, Biome, contrats générés et liens des 36 documents passent. Le build Linux et les contrôles HTTP standalone réussissent pour les seize langues ; le contrôle sur les données locales vérifie les 57 projets dans chacune d'elles. Les deux sous-ensembles de police ajoutés représentent 19 740 octets et leur intégrité est contrôlée.

Le navigateur confirme l'accueil et la fiche cartographique en vietnamien, les commandes MapLibre, la recherche par promoteur, le format `Quý 2 · 2029`, les noms de sources conservés, et le passage vietnamien → français → vietnamien avec projet/territoire/ancre conservés. L'accueil, l'annuaire et la fiche agrandie ont été contrôlés à une largeur de téléphone de 390 pixels, sans débordement de page ni erreur console observée. Les pages vietnamiennes répondent aussi en HTTPS sur la prévisualisation privée existante. Ces contrôles techniques ne constituent pas une certification de la traduction par un locuteur natif.
