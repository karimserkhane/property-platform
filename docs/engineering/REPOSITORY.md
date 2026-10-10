# Structure et règles de dépendance

Le dépôt conserve les choix de la revue V2 et du contre-audit. Un monorepo contient plusieurs applications, sans en faire des microservices. Les études sont dans `docs/product`, les décisions actuelles dans `docs/architecture` et les propositions remplacées dans `docs/archive`. Seuls README et AGENTS restent des documents Markdown de racine.

Les versions exécutables ont ensuite été actualisées ; [TOOLCHAIN.md](TOOLCHAIN.md) fait référence pour leurs versions et exceptions, tandis que les anciennes études conservent le contexte de leurs décisions.

## Comment lire l'arborescence

La **racine** est le dossier `property-platform`. Un élément terminé par `/` est un dossier ; les éléments indentés sont à l'intérieur de ce dossier. `src` contient le code source, `tests` les contrôles automatisés et `config` les réglages de l'application. Les noms qui commencent par un point, comme `.github`, sont aussi des fichiers ou dossiers ordinaires, parfois masqués par l'explorateur.

L'arborescence ci-dessous décrit les fichiers suivis par Git aujourd'hui. Les quinze fichiers de traduction sont regroupés pour la lisibilité ; les fichiers Python `__init__.py`, qui identifient les paquets, sont omis. Les dossiers générés par les outils sont expliqués séparément.

```text
property-platform/
├── README.md                         Présentation et liens pour démarrer
├── AGENTS.md                         Consignes pour les agents qui modifient le dépôt
├── package.json                      Commandes communes et outils JavaScript du dépôt
├── pnpm-workspace.yaml               Déclaration des applications et paquets du monorepo
├── pnpm-lock.yaml                    Versions résolues des dépendances JavaScript
├── biome.json                        Configuration du formatage et des contrôles de code
├── .node-version                     Version de Node.js attendue
├── .python-version                   Version de Python attendue à la racine
├── .editorconfig                     Règles de texte communes aux éditeurs
├── .gitattributes                    Règles Git, notamment les fins de ligne
├── .gitignore                        Fichiers locaux exclus de Git
├── .dockerignore                     Fichiers exclus du contexte de construction Docker
├── .github/
│   └── workflows/
│       └── ci.yml                    Contrôles automatiques exécutés sur GitHub
├── apps/
│   ├── web/                          Application web Next.js
│   │   ├── package.json              Dépendances et commandes propres au site
│   │   ├── next.config.ts            Configuration Next.js et intégration multilingue
│   │   ├── tsconfig.json             Configuration du compilateur TypeScript
│   │   ├── Dockerfile                Construction de l'image du site
│   │   ├── messages/
│   │   │   └── en.json, ar.json…     Textes de l'interface dans les quinze langues
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── globals.css       Styles communs du site
│   │   │   │   └── [locale]/         Routes associées à une langue, par exemple /en
│   │   │   │       ├── layout.tsx    Structure de page, langue, direction et métadonnées
│   │   │   │       └── page.tsx      Page d'accueil actuelle
│   │   │   ├── components/
│   │   │   │   └── language-switcher.tsx   Sélecteur de langue interactif
│   │   │   ├── i18n/
│   │   │   │   ├── locales.ts       Langues acceptées et direction LTR/RTL
│   │   │   │   ├── routing.ts       Règles des URL et langue par défaut
│   │   │   │   ├── request.ts       Chargement des traductions de la langue demandée
│   │   │   │   ├── navigation.ts    Navigation tenant compte de la langue
│   │   │   │   └── types.d.ts       Déclarations de types pour les traductions
│   │   │   └── proxy.ts             Traitement du routage multilingue des requêtes
│   │   └── tests/
│   │       └── i18n.test.mjs        Contrôles des langues, textes et règles de routage
│   └── api/                          Application backend Django
│       ├── manage.py                 Entrée des commandes Django
│       ├── pyproject.toml            Dépendances Python et configuration des contrôles
│       ├── uv.lock                   Versions résolues des dépendances Python
│       ├── .python-version           Version Python attendue pour cette application
│       ├── .env.example              Exemple de variables d'environnement locales
│       ├── Dockerfile                Image Python, Django et bibliothèques géographiques
│       ├── src/
│       │   └── liwa/                 Paquet Python de notre backend
│       │       ├── config/
│       │       │   ├── urls.py       Branchement des URL API et administration
│       │       │   ├── wsgi.py       Entrée du serveur Python pour servir Django
│       │       │   └── settings/
│       │       │       ├── base.py          Réglages communs
│       │       │       ├── local.py         Réglages du développement local
│       │       │       ├── testing.py       Réglages des tests
│       │       │       └── production.py    Réglages et exigences de production
│       │       ├── api/
│       │       │   └── router.py     API HTTP et contrôles de santé actuels
│       │       ├── modules/
│       │       │   ├── catalog/      Identité des biens et relations acceptées
│       │       │   │   ├── apps.py   Déclaration de l'application Django
│       │       │   │   └── README.md Responsabilités et dépendances du module
│       │       │   ├── evidence/     Sources, assertions et rapprochements
│       │       │   │   ├── apps.py
│       │       │   │   └── README.md
│       │       │   └── publication/  Validation et versions publiées
│       │       │       ├── apps.py
│       │       │       └── README.md
│       │       └── export_openapi.py Export de la description de l'API
│       └── tests/
│           └── test_health.py        Contrôles HTTP et test de disponibilité PostGIS
├── packages/
│   └── contracts/                    Contrat entre le backend et les clients TypeScript
│       ├── package.json              Commandes de génération et de vérification
│       ├── tsconfig.json             Réglages de vérification des types
│       ├── openapi.json              Description exportée de l'API Django
│       └── src/
│           └── generated.ts          Types TypeScript générés depuis OpenAPI
├── infra/
│   └── local/
│       └── compose.yaml              Services API et PostGIS, réseau et volume local
├── docs/
│   ├── README.md                     Index et enchaînement des décisions
│   ├── product/
│   │   ├── ETUDE_PRODUIT_LIWA_ATLAS.md       Besoins, marché et périmètre envisagé
│   │   └── STRATEGIE_PRODUIT_LIWA_ATLAS.md   Approfondissement et différenciation
│   ├── architecture/
│   │   ├── REVUE_ARCHITECTURE_LIWA_ATLAS_V2.md   Architecture de référence
│   │   └── AUDIT_DECISION_STACK_LIWA_ATLAS.md    Contre-audit réalisé après V2
│   ├── archive/
│   │   └── ARCHITECTURE_STACK_LIWA_ATLAS.md     Proposition précédente remplacée
│   └── engineering/
│       ├── REPOSITORY.md              Ce guide de structure et de responsabilités
│       ├── DEVELOPMENT.md             Commandes de démarrage et explications
│       ├── TOOLCHAIN.md               Versions exécutables et compatibilités
│       ├── INTERNATIONALIZATION.md    Politique des langues et du RTL
│       └── STRUCTURE_REVIEW.md        Revue critique de l'organisation
└── scripts/
    ├── check-doc-links.mjs            Vérification des liens locaux dans les documents
    ├── prepare-web-runtime.mjs        Préparation des ressources de l'artefact web autonome
    └── smoke-web.mjs                  Vérification du site construit et des routes de langue
```

## Pourquoi séparer ces dossiers ?

### `apps/web` : ce que l'utilisateur voit

Ce dossier possède les pages et interactions du site. `src/app` définit les routes ; les crochets de `[locale]` indiquent un paramètre variable, pas un dossier à créer pour chaque langue. Le même `page.tsx` peut donc servir `/en`, `/ar` ou `/fr`, avec des textes différents dans `messages`.

`src/components` accueille les composants réellement réutilisables. `src/i18n` centralise les règles de traduction et de navigation pour éviter que chaque page réinvente la gestion des langues. Le site ne doit pas accéder directement aux tables PostgreSQL : les demandes métier passent par l'API.

### `apps/api` : les données et les règles métier

`config` règle le fonctionnement de Django ; `api` reçoit les demandes HTTP ; `modules` organise le métier. Cette séparation permet à une future application mobile, à l'administration et à un import de réutiliser les mêmes règles sans les recopier.

| Module | Ce qu'il possédera | Exemple dans notre produit |
|---|---|---|
| [catalog](../../apps/api/src/liwa/modules/catalog/README.md) | Identité des territoires, parcelles, bâtiments et logements, relations acceptées | Déterminer à quel bâtiment appartient un logement |
| [evidence](../../apps/api/src/liwa/modules/evidence/README.md) | Sources, acquisitions, assertions et décisions de rapprochement | Conserver qu'un document daté annonce une livraison, avec sa provenance |
| [publication](../../apps/api/src/liwa/modules/publication/README.md) | Validation, projections et versions publiées | Publier une version validée du dossier en passant par les services des autres modules |

**Ces modules sont actuellement des cadres de responsabilité : leurs modèles immobiliers ne sont pas encore implémentés.** Leurs `apps.py` les déclarent à Django ; leurs `README.md` précisent leurs frontières.

`settings/base.py` est partagé, puis complété par les réglages locaux, de test ou de production. La présence de `production.py` ne signifie pas que le site est déployé. `manage.py` sert notamment à lancer les migrations ou à créer un administrateur ; ce n'est pas une page web.

### `packages/contracts` : l'accord entre le site et l'API

Le backend exporte ses routes et formats de réponse dans `openapi.json`. Le générateur produit ensuite `src/generated.ts`, utilisé pour vérifier les types côté TypeScript. Ces deux fichiers sont suivis par Git et mis à jour ensemble via les commandes documentées dans [DEVELOPMENT.md](DEVELOPMENT.md) ; ils ne se corrigent pas manuellement.

Ce paquet contient des descriptions de données, pas une copie des modèles Django ni des règles métier. Il pourra aussi être consommé par le futur mobile.

### `infra`, `.github` et `scripts` : lancer et vérifier

`infra/local/compose.yaml` décrit l'environnement local : conteneur API, base PostGIS, réseau et stockage persistant. Il ne contient pas les données de la base : celles-ci résident dans un volume Docker. Le site Next.js est lancé séparément dans le parcours local actuel.

Chaque `Dockerfile` décrit comment construire l'image d'une application. `.github/workflows/ci.yml` décrit les vérifications que GitHub exécute ; un workflow de contrôle ne publie pas automatiquement le site. Les fichiers de `scripts` sont des utilitaires du dépôt, pas des fonctionnalités accessibles aux utilisateurs.

### `docs` : comprendre le produit, les décisions et le travail quotidien

`product` explique ce que nous voulons construire, `architecture` pourquoi les composants ont été retenus, `archive` conserve les propositions remplacées et `engineering` explique comment travailler sur le socle réel. L'[index documentaire](../README.md) donne l'ordre de lecture. Les exemples d'une étude ne prouvent pas qu'une fonctionnalité existe déjà.

## Fichiers de configuration à la racine

| Fichier | Quand il intervient | Comment le traiter |
|---|---|---|
| `package.json` | Quand on lance une commande comme `pnpm.cmd dev:web` | Modifier les commandes ou outils communs ici, les dépendances propres au site dans `apps/web/package.json` |
| `pnpm-workspace.yaml` | Quand pnpm identifie les applications et paquets du monorepo | Actualiser lors de l'ajout d'un paquet si son chemin n'est pas déjà couvert |
| `pnpm-lock.yaml` et `apps/api/uv.lock` | Quand les outils installent les versions résolues | Laisser les gestionnaires les générer et les conserver dans Git |
| `.node-version` et `.python-version` | Quand un outil compatible sélectionne un runtime | Aligner avec les manifestes, Docker, CI et le guide des versions ; ces fichiers n'installent pas les runtimes à eux seuls |
| `biome.json` et `.editorconfig` | Quand les outils contrôlent ou formatent le code et le texte | Conserver des règles communes plutôt que des préférences contradictoires par développeur |
| `.gitignore`, `.dockerignore`, `.gitattributes` | Quand Git suit les fichiers ou Docker prépare une construction | Distinguer exclusion de Git, exclusion de l'image et règles de traitement du texte |

## Dossiers locaux créés par les outils

Tu peux voir ces éléments dans PyCharm après installation ou démarrage, même s'ils ne figurent pas dans l'arborescence suivie par Git.

| Élément | Rôle | Faut-il y développer ? |
|---|---|---|
| `.git/` | Historique et métadonnées du dépôt | Non, utiliser les commandes ou l'interface Git |
| `node_modules/` | Bibliothèques JavaScript installées par pnpm | Non, modifier le code dans `src` et les dépendances dans les manifestes |
| `apps/web/.next/` | Cache et fichiers générés par Next.js | Non, le prochain lancement ou build peut les recréer |
| `apps/api/.venv/` | Environnement Python local créé par uv si tu utilises ce parcours | Non, le code du projet reste dans `src/liwa` |
| `__pycache__/`, `.pytest_cache/`, `.ruff_cache/` | Caches des outils Python | Non, ils ne sont pas des sources |
| `.cache/`, `.tools-env/` | Éventuels caches et outils locaux utilisés pendant la préparation | Non, leur présence dépend du poste et ils ne sont pas requis comme dossiers source |
| `.idea/` | Réglages locaux de PyCharm | Ne pas y placer le code ; vérifier les exclusions Git avant tout partage de réglages |

Les caches de code ne sont pas le stockage de PostgreSQL. **Supprimer un volume Docker peut supprimer les données ; recréer un cache Next.js ou réinstaller des dépendances ne remet pas la base à zéro.**

## Où ajouter une nouvelle fonctionnalité ?

| Besoin | Emplacement prévu | État actuel |
|---|---|---|
| Modifier les textes d'accueil | `apps/web/messages/<langue>.json` | Existe |
| Modifier la page d'accueil | `apps/web/src/app/[locale]/page.tsx` | Existe |
| Ajouter une carte ou une fiche immobilière | `apps/web/src/features/map/` ou `src/features/property/`, branchées depuis une route de `src/app` | À créer avec la fonctionnalité |
| Ajouter un composant partagé entre plusieurs fonctionnalités | `apps/web/src/components/` | Dossier existant ; y placer seulement les composants réutilisables |
| Ajouter les modèles de bâtiments et leurs règles | `apps/api/src/liwa/modules/catalog/` | Module existant ; modèles et services à créer |
| Ajouter les sources et preuves | `apps/api/src/liwa/modules/evidence/` | Module existant ; modèles et services à créer |
| Ajouter une route métier HTTP | `apps/api/src/liwa/api/`, branchée au routeur | À créer avec les services métier qu'elle appelle |
| Ajouter des migrations Django | `migrations/` dans le module propriétaire | À générer avec Django lorsque les modèles arrivent |
| Ajouter un domaine prix, avis ou documents | Module dédié sous `apps/api/src/liwa/modules/` | À créer quand ses responsabilités et dépendances sont définies |
| Ajouter des contrôles de fonctionnalité | Tests proches du module concerné ; tests d'intégration transversaux dans `apps/api/tests/` | À ajouter avec les comportements concernés |
| Ajouter l'application mobile | `apps/mobile/`, consommant la même API | Non créé ; le pilote web vient d'abord |
| Ajouter des workers | Entrées d'exécution Python séparées, réutilisant les services métier ; image distincte pour les traitements lourds | Non implémenté ; emplacement précis à fixer avec le premier traitement |

Exemple futur : la page du site demande la fiche d'un bâtiment à une route de `api`, qui appelle un service de `catalog` et des lectures explicites de `evidence`. Django interroge PostgreSQL/PostGIS puis renvoie une réponse conforme au contrat. Le composant web l'affiche et utilise les traductions de l'interface. Chaque couche a ainsi un rôle précis ; la logique métier ne se retrouve pas recopiée dans la page.

## Ce qui rend cette organisation modulaire

- Chaque module possède ses mutations et invariants. Les appels externes passent par des services explicites ; aucun module ne modifie les tables d'un autre directement.
- Dépendances autorisées : publication → evidence → catalog, et publication → catalog. Les modules n'importent ni configuration ni HTTP. Import Linter vérifie ces directions en CI ; il ne peut pas détecter tous les accès ORM indirects, qui restent à examiner en revue.
- API, administration et futurs workers appellent les mêmes commandes métier. Les dépendances lourdes OCR/Blender ne sont pas installées dans le serveur web.
- Le backend possède schémas et migrations métier. OpenAPI est exporté, les types TypeScript sont générés et la CI détecte leur divergence.
- Le web ne connaît pas les tables ni les modèles Django. Chaque fonctionnalité future sera regroupée sous `src/features/<fonction>` ; seuls les composants réellement partagés rejoignent une bibliothèque commune.
- Les adaptations de stockage, authentification et fournisseurs seront introduites avec leur première utilisation. Aucun framework abstrait de plugins n'est créé d'avance.

Les workers légers utiliseront le même paquet Python que l'API, avec un processus distinct. Une image spécialisée sera ajoutée pour le calcul lourd. Mobile, market, reviews et scenes arrivent lorsqu'une fonctionnalité les justifie ; aucun dossier vide ne simule une application prête.

## Invariants de travail

1. Aucun secret ni original documentaire privé dans Git. Utiliser `.env.example` pour les noms et paramètres locaux ; les environnements réels utilisent leurs secrets propres.
2. Les tables métier publiées restent typées ; propositions et preuves ne remplacent pas les contraintes du catalogue.
3. Une opération sensible conserve auteur, raison et version ; les permissions couvrent HTTP, administration, fichiers et futurs traitements.
4. Toute évolution d'API conserve sa compatibilité ou documente une rupture. Les types générés ne sont jamais édités manuellement.
5. Les migrations sont revues et exécutées explicitement, pas au démarrage concurrent de chaque processus. Les comptes base de migration/exécution seront séparés au déploiement.
6. Les durées, montants et identifiants sont validés côté serveur. UTC en stockage ; fuseau et format d'affichage côté client.
7. L'anglais est la langue par défaut. Les traductions d'interface restent séparées des traductions documentaires ; les preuves originales et identifiants restent stables. Les layouts utilisent des propriétés CSS logiques pour le RTL.

## Ce que le socle ne prétend pas fournir

Les trois modules Django sont des limites de responsabilité, sans modèle métier inventé avant le dossier pilote. La page web est une page d'attente. Auth Supabase, stockage, carte, collecteurs, queue et génération ne sont pas encore intégrés. Les seuls endpoints sont liveness et readiness PostGIS. L'administration Django est locale à ce stade ; elle ne doit pas être ouverte en production avant le parcours d'accès du personnel et ses règles métier.
