# Langues, traduction et mise en page

## Décision

L'anglais est la langue par défaut demandée par l'utilisateur. L'interface initiale propose quinze langues : anglais, arabe, espagnol, allemand, russe, hindi, ourdou, bengali, malayalam, tamoul, filipino, persan, chinois simplifié, français et portugais.

Cette liste est une sélection de couverture et de marché, **pas un classement statistique des langues les plus parlées aux Émirats**. Le guide officiel Visit Dubai atteste l'usage de l'arabe et de l'anglais, et mentionne notamment russe, tagalog, hindi, ourdou et portugais. Un document Emirates Driving Institute fournit un autre indice de besoins linguistiques, notamment bangla, chinois, farsi, hindi, malayalam, russe et tamoul ; il est ancien et ne mesure pas le nombre de locuteurs. Espagnol et allemand sont ajoutés à la demande de l'utilisateur ; français complète les publics visés. Le filipino est ici la variante d'interface choisie pour le public philippin, sans assimiler toutes ses langues au tagalog.

[Visit Dubai — langues](https://www.visitdubai.com/plan-your-trip/practical-information), [EDI — interprétation des tests, document historique](https://edi-uae.com/public/uploads/editor-images/files/RIS.pdf).

Le texte de la page d'attente et son sélecteur sont traduits. Ce sont des traductions initiales à faire relire par des locuteurs compétents avant publication commerciale, notamment pour les termes immobiliers. Les tests vérifient cohérence et rendu, pas la qualité linguistique d'une traduction.

## Implémentation

- `src/i18n/locales.ts` : registre des codes, noms dans leur langue, sens de lecture et langue par défaut.
- `src/i18n/routing.ts` et `src/proxy.ts` : routes préfixées, par exemple `/en`, `/ar`, `/ru`.
- `src/i18n/request.ts` : chargement serveur du seul dictionnaire nécessaire et fuseau d'affichage par défaut `Asia/Dubai`.
- `messages/<locale>.json` : messages organisés par fonctionnalité. Aucun texte d'interface n'est dupliqué dans chaque page.
- `src/app/[locale]` : layout et pages localisés, rendus statiquement lorsque possible.
- `src/components/language-switcher.tsx` : sélection explicite, conservation du chemin, des paramètres de recherche et de l'ancre.

`/` redirige vers `/en`, même si le navigateur préfère une autre langue. Nous désactivons la détection automatique et le cookie de langue pour respecter ce défaut explicite. Une langue choisie reste portée par l'URL ; revenir à `/` revient à l'anglais. Une éventuelle préférence persistante de compte devra être décidée et testée séparément.

Le routage et les traductions utilisent next-intl, compatible avec Next.js App Router. La configuration utilise `next/root-params`, disponible dans la version Next.js du dépôt, plutôt qu'une implémentation maison de négociation linguistique. Les messages utiles au serveur restent côté serveur ; seul le namespace du sélecteur est envoyé au client.

[Routage next-intl](https://next-intl.dev/docs/routing/setup), [configuration de la détection](https://next-intl.dev/docs/routing/configuration).

## RTL et accessibilité

Arabe (`ar`), ourdou (`ur`) et persan (`fa`) utilisent `dir="rtl"` ; les autres utilisent `ltr`. `html.lang` correspond à la route. Utiliser marges/paddings/dimensions logiques et `text-align: start`, pas une inversion arbitraire de toute l'interface. Ne pas espacer les lettres arabes comme un titre latin.

Les noms des langues sont affichés dans leur propre écriture, sans drapeaux assimilant langue et nationalité. Le sélecteur possède un libellé accessible et reste utilisable au clavier. Les marques, références de parcelle, nombres et codes doivent être isolés avec `bdi` ou un sens explicite lorsque nécessaire. La carte, les photos et les plans ne sont pas retournés horizontalement en RTL ; les panneaux et contrôles seront adaptés séparément.

Les contrôles techniques actuels vérifient toutes les routes, le sens de lecture, les textes traduits, le sélecteur et les fichiers CSS du serveur compilé. Ils ne certifient pas encore la navigation assistée, tous les appareils ni les futures interactions cartographiques. Ces parcours feront l'objet de tests avec la tranche pilote.

## Interface et contenu immobilier sont deux problèmes distincts

Traduire l'interface ne traduit pas automatiquement les brochures, plans, avis ou preuves. Conserver le texte original, son code de langue BCP 47, sa version et ses droits. Une traduction dérivée référence le document ou l'assertion d'origine, sa méthode/modèle, sa date, son statut de revue et la version traduite. Une nouvelle source invalide les traductions qui ne correspondent plus à sa version.

Les identifiants de projet/bâtiment/unité restent communs à toutes les langues. Les noms officiels sont conservés ; alias et noms d'affichage validés facilitent la recherche. Les résumés IA indiquent leur langue et leur provenance. Un texte original peut être présenté avec `lang` et `dir="auto"` sans inventer une traduction manquante.

Les messages d'API utilisent des codes stables et des paramètres typés ; l'interface les traduit. Les données numériques restent des nombres/montants décimaux, les dates machine au format défini et en UTC. Affichage avec Intl/next-intl ; la langue ne convertit pas implicitement la devise AED ni les conventions de surface. Les caches de texte dérivé doivent être séparés par langue, version et droits.

Le prototype reste `noindex`. Le routage fournit les alternatives linguistiques ; domaine canonique, sitemap et politique de publication des traductions validées seront définis avant mise en ligne. Ajouter une langue consiste à ajouter son registre et un dictionnaire complet, puis valider les tests et la traduction ; une clé manquante bloque la CI.
