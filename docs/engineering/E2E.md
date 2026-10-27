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

## Contre le paquet de démonstration (CI)

Le job CI `e2e` (et n'importe quel poste) lance les mêmes parcours contre une pile
**jetable et isolée**, `infra/local/compose.e2e-demo.yaml` (projet Compose
`property-platform-e2e-demo`) : PostGIS et fichiers privés en mémoire, aucun volume,
réseau ni port partagé avec la pile locale.

```bash
docker compose -f infra/local/compose.e2e-demo.yaml build
docker compose -f infra/local/compose.e2e-demo.yaml up -d --wait api
docker compose -f infra/local/compose.e2e-demo.yaml run --rm checks-e2e
docker compose -f infra/local/compose.e2e-demo.yaml down
```

Au démarrage, l'API applique les migrations puis `load_demo_package` rejoue
`fixtures/demo-replay/` avec les importateurs actuels (aucun dump : 6 acquisitions
revues, parcelles, rues et bâtiments de Reem, un projet lu au registre ADREC) ; elle
n'est prête qu'après un rejeu sans étape échouée ni divergente (environ 1 min 30).
`E2E_REQUIRE_DATA=1` transforme tout parcours « ignoré faute de données » en **échec**,
sauf ceux dont le paquet ne peut pas contenir les données : leur raison est donnée
dans le parcours et le rapport les compte comme ignorés, jamais comme réussis.

Le dépôt est public : le paquet ne contient **aucune page de promoteur ni d'annonce**
(décision du 27/10, [A18](../tasks/A18.md)). Les pages d'Aldar qu'il contenait ont été
retirées. Or toutes les relations de projet relues citent une telle page : le parcours
« composant → programme parent » ne tourne donc que contre la base locale, et il est
ignoré en CI avec sa raison. En CI, si un parcours échoue, les journaux de
l'API sont affichés et `.cache/e2e/` (traces, captures, rapport HTML) est publié comme
artefact `e2e-traces` (14 jours). Durée mesurée en local : environ 1 min 30 de rejeu et
1 min 30 de parcours, hors construction des images.

L'API de cette pile tourne sous **gunicorn**, le serveur de l'image (`CMD` du
`Dockerfile` : un processus, quatre threads), avec la durée de chaque requête dans le
journal d'accès, et non sous `runserver`, qui exécute toutes les requêtes à la fois,
chacune avec sa session PostgreSQL. Au premier affichage de la carte, le navigateur
envoie d'un coup tuiles de parcelles et de contexte, index de contexte et quatre quarts
de `parcel-index` ; sous `runserver`, ces lectures se disputaient dans PostgreSQL les
processeurs du runner, déjà pris par le rendu WebGL logiciel, et la plus lourde (les
2 060 parcelles du quart sud-est de Reem, environ 120 ms sur une machine au repos)
dépassait parfois son `statement_timeout` de 2 s (A17). Avec quatre threads, comme en
service, les autres requêtes attendent hors de PostgreSQL, avant que leur budget ne
commence ; ce budget n'a pas changé. Mesure (rafale du run CI en échec rejouée 25 fois
sur deux processeurs, dont 10 fois saturés par une charge égale à celle du navigateur) :
43 lectures annulées et `parcel_features` jusqu'à 1,98 s sous `runserver`, aucune
annulation et 0,87 s au plus sous gunicorn ([A17](../tasks/A17.md)).

Le paquet se régénère depuis la base locale de référence avec `export_demo_package`
(lecture seule) ; la sélection, les raisons et les licences sont dans
`fixtures/demo-replay/selection.json`. Une source n'y entre que si sa copie peut
rester dans un dépôt public.

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
jamais compté comme réussi ; c'est toujours le cas en CI (voir plus haut). Le clic sur la carte sonde une grille autour du centre :
l'eau et les routes ne sont pas des parcelles, mais une parcelle doit être trouvée.

## Limites

- Ces parcours dépendent de l'état de la base locale ; ils ne remplacent ni les tests
  PostGIS ni les tests web unitaires.
- En CI GitHub, ils tournent contre le paquet de démonstration (A13), pas contre la
  base locale : un parcours qui dépend d'autres données doit enrichir le paquet.
- Le rendu WebGL logiciel ne mesure pas les performances réelles d'un téléphone.
