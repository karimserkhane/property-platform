# Langues, traduction et mise en page

## Décision

L'anglais est la langue par défaut demandée par l'utilisateur. L'interface initiale propose quinze langues : anglais, arabe, espagnol, allemand, russe, hindi, ourdou, bengali, malayalam, tamoul, filipino, persan, chinois simplifié, français et portugais.

Cette liste est une sélection de couverture et de marché, **pas un classement statistique des langues les plus parlées aux Émirats**. Le guide officiel Visit Dubai atteste l'usage de l'arabe et de l'anglais, et mentionne notamment russe, tagalog, hindi, ourdou et portugais. Un document Emirates Driving Institute fournit un autre indice de besoins linguistiques, notamment bangla, chinois, farsi, hindi, malayalam, russe et tamoul ; il est ancien et ne mesure pas le nombre de locuteurs. Espagnol et allemand sont ajoutés à la demande de l'utilisateur ; français complète les publics visés. Le filipino est ici la variante d'interface choisie pour le public philippin, sans assimiler toutes ses langues au tagalog.

[Visit Dubai — langues](https://www.visitdubai.com/plan-your-trip/practical-information), [EDI — interprétation des tests, document historique](https://edi-uae.com/public/uploads/editor-images/files/RIS.pdf).

Les textes de l'accueil, de l'exploration locale et du sélecteur sont traduits. Ce sont des traductions initiales à faire relire par des locuteurs compétents avant publication commerciale, notamment pour les termes immobiliers. Les tests vérifient cohérence et rendu, pas la qualité linguistique d'une traduction. Les codes de parcelles et noms officiels restent dans leur forme d'origine ; leur présence dans une interface arabe ne signifie pas qu'une traduction documentaire a été validée.

## Implémentation

- `C:\Users\Karim\Repositories\property-platform\apps\web\src\i18n\locales.ts` : registre des codes, noms dans leur langue, sens de lecture et langue par défaut.
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

Les cinq fichiers WOFF2, les licences SIL Open Font License et leur provenance sont sous `C:\Users\Karim\Repositories\property-platform\apps\web\public\fonts\`. Le fichier `fonts.css` y définit les familles et leurs plages Unicode ; `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\globals.css` l'importe et expose les variables `--font-ui` et `--font-display`. `font-display: swap` permet de lire le texte avant que la police soit chargée. Les fichiers sont servis par le site : la navigation n'appelle pas Google Fonts.

`C:\Users\Karim\Repositories\property-platform\apps\web\src\theme\fonts.ts` choisit les préchargements du layout selon la langue : sous-ensembles latins pour les langues latines, cyrilliques pour le russe, arabe pour `ar`, `ur` et `fa`. Les autres langues préchargent seulement Manrope latin pour la marque et les codes. Le CSS peut charger un autre sous-ensemble lorsque le texte affiché le nécessite ; un préchargement ne définit donc pas à lui seul toutes les polices utilisées dans la page. Le manifeste `credits.json` contient les versions, tailles et empreintes exactes ; le [guide du thème](VISUAL_DESIGN.md) donne les budgets initiaux.

## RTL et accessibilité

Arabe (`ar`), ourdou (`ur`) et persan (`fa`) utilisent `dir="rtl"` ; les autres utilisent `ltr`. `html.lang` correspond à la route. Utiliser marges/paddings/dimensions logiques et `text-align: start`, pas une inversion arbitraire de toute l'interface. Ne pas espacer les lettres arabes comme un titre latin.

Les noms des langues sont affichés dans leur propre écriture, sans drapeaux assimilant langue et nationalité. Le sélecteur possède un libellé accessible et reste utilisable au clavier. Les marques, références de parcelle, nombres et codes doivent être isolés avec `bdi` ou un sens explicite lorsque nécessaire. La carte, les photos et les plans ne sont pas retournés horizontalement en RTL ; les panneaux et contrôles seront adaptés séparément.

Les contrôles techniques actuels vérifient toutes les routes, le sens de lecture, les textes traduits, le sélecteur et les fichiers CSS du serveur compilé. Ils ne certifient pas encore la navigation assistée, tous les appareils ni les futures interactions cartographiques. Ces parcours feront l'objet de tests avec la tranche pilote.

## Interface et contenu immobilier sont deux problèmes distincts

La marque affichée est une valeur publique de `packages/branding/src/brand.ts`, isolée avec `bdi` et commune aux langues. Les textes d'interface et les noms de lieux restent traduits dans les dictionnaires ; aucune copie du nom commercial dans les quinze fichiers n'est nécessaire. Un éventuel nom commercial différent par langue nécessitera une configuration explicite, sans modifier les identités métier.

Traduire l'interface ne traduit pas automatiquement les brochures, plans, avis ou preuves. Conserver le texte original, son code de langue BCP 47, sa version et ses droits. Une traduction dérivée référence le document ou l'assertion d'origine, sa méthode/modèle, sa date, son statut de revue et la version traduite. Une nouvelle source invalide les traductions qui ne correspondent plus à sa version.

Les identifiants de projet/bâtiment/unité restent communs à toutes les langues. Les noms officiels sont conservés ; alias et noms d'affichage validés facilitent la recherche. Les résumés IA indiquent leur langue et leur provenance. Un texte original peut être présenté avec `lang` et `dir="auto"` sans inventer une traduction manquante.

Les messages d'API utilisent des codes stables et des paramètres typés ; l'interface les traduit. Les données numériques restent des nombres/montants décimaux, les dates machine au format défini et en UTC. Affichage avec Intl/next-intl ; la langue ne convertit pas implicitement la devise AED ni les conventions de surface. Les caches de texte dérivé doivent être séparés par langue, version et droits.

Le prototype reste `noindex`. Le routage fournit les alternatives linguistiques ; domaine canonique, sitemap et politique de publication des traductions validées seront définis avant mise en ligne. Ajouter une langue consiste à ajouter son registre et un dictionnaire complet, puis valider les tests et la traduction ; une clé manquante bloque la CI.
