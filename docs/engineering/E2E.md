# Parcours navigateur (Playwright) — A05

Les tests web (`apps/web/tests/`) vérifient des fonctions pures. Les **parcours** de
`apps/web/e2e/` ouvrent le site compilé dans Chromium, comme un visiteur, et vérifient
qu'un enchaînement réel fonctionne de bout en bout avec les données locales.

## Lancer

Depuis la racine du dépôt ou d'un worktree, avec l'API locale démarrée :

```bash
docker compose -f infra/local/compose.yaml -f infra/local/compose.checks.yaml --profile checks build checks-e2e
docker compose -f infra/local/compose.yaml -f infra/local/compose.checks.yaml --profile checks run --rm --no-deps checks-e2e
```

La construction recompile le site à partir des sources du dossier courant (même
`Dockerfile` et même cache que la prévisualisation, étape `e2e`) ; elle ne remplace pas
l'image `property-platform-web-preview`. Les fichiers de parcours sont montés au
lancement : les modifier ne nécessite pas de reconstruire. Un changement du site
(`apps/web/src/`, messages, lockfile) nécessite la commande `build`.

Arguments Playwright : `... run --rm --no-deps checks-e2e node node_modules/@playwright/test/cli.js test --config playwright.config.ts -g "parcel"`.

## Ce qui tourne

- Image `mcr.microsoft.com/playwright:v1.64.0-noble`, fixée par digest, avec Node
  26.11.1 copié de l'image web et le serveur Next autonome compilé.
- Le serveur web est démarré **dans le conteneur**, sur `127.0.0.1:3101`, sans contrôle
  d'accès (`PROPERTY_PLATFORM_PREVIEW_ACCESS_REQUIRED=0`). Aucun identifiant de
  prévisualisation n'est lu ni nécessaire ; le conteneur `web` de Karim n'est pas utilisé.
- Les données viennent de l'API locale partagée (`http://api:8000`), en **lecture
  seule** : les parcours ne soumettent aucun formulaire de données et n'écrivent rien.
- Un seul worker : le rendu WebGL est logiciel (SwiftShader) et lent sur un portable.
- Échecs : traces, captures d'écran et rapport HTML dans `.cache/e2e/` (ignoré par Git).
  Ouvrir le rapport avec `pnpm exec playwright show-report .cache/e2e/report` après
  installation des dépendances, ou ouvrir `.cache/e2e/report/index.html`.

## Parcours

| Fichier | Parcours | Projet |
| --- | --- | --- |
| `explorer.spec.ts` | Explorateur de Reem → clic sur une parcelle de la carte → fiche de sélection chargée → l'URL rouvre la même parcelle | ordinateur |
| `projects.spec.ts` | Recherche dans l'annuaire → ouverture du projet trouvé ; recherche sans résultat ; fiche avec preuves dépliables et retour à l'annuaire ; composant → programme parent → liste « Bâtiments et phases » ; fiche → historique de livraison du promoteur (preuve dépliable) ; fiche d'un projet lu au registre ADREC → section « Vérification » (numéro, séquestre, preuve dépliable, liens officiels, entrée de navigation), sans défilement horizontal | ordinateur |
| `locales.spec.ts` | Arabe, persan et ourdou en `dir="rtl"` sans défilement horizontal, accueil et fiche ; anglais et français en `ltr` | ordinateur |
| `context-tiles.spec.ts` | Explorateur de Reem en 3D catalogue → tuiles `context-tiles` et index `context-index` lus, aucun `map-context` → un clic près du centre ouvre une fiche sans erreur | ordinateur |
| `mobile.spec.ts` | Accueil, annuaire, fiche et carte sur un écran Pixel 7, sans défilement horizontal | mobile |

Les parcours découvrent leurs données (premier projet de l'annuaire, première carte
portant un parent) au lieu de figer des noms. Si les données locales ne contiennent
aucune hiérarchie relue, le parcours correspondant est **marqué ignoré avec sa raison**,
jamais compté comme réussi. Le clic sur la carte sonde une grille autour du centre :
l'eau et les routes ne sont pas des parcelles, mais une parcelle doit être trouvée.

## Limites

- Ces parcours dépendent de l'état de la base locale ; ils ne remplacent ni les tests
  PostGIS ni les tests web unitaires.
- Pas encore exécutés en CI GitHub : l'intégration CI (pile API + jeu de démonstration)
  est suivie dans [A13](../tasks/A13.md).
- Le rendu WebGL logiciel ne mesure pas les performances réelles d'un téléphone.
