# Structure et règles de dépendance

Le dépôt conserve les choix de la revue V2 et du contre-audit. Un monorepo contient plusieurs applications, sans en faire des microservices. Les études sont dans `docs/product`, les décisions actuelles dans `docs/architecture` et les propositions remplacées dans `docs/archive`. Seuls README et AGENTS restent des documents Markdown de racine.

Les versions exécutables ont ensuite été actualisées ; [TOOLCHAIN.md](TOOLCHAIN.md) fait référence pour leurs versions et exceptions, tandis que les anciennes études conservent le contexte de leurs décisions.

## Comment lire l'arborescence

La **racine** est le dossier `property-platform`. Un élément terminé par `/` est un dossier ; les éléments indentés sont à l'intérieur de ce dossier. `src` contient le code source, `tests` les contrôles automatisés et `config` les réglages de l'application. Les noms qui commencent par un point, comme `.github`, sont aussi des fichiers ou dossiers ordinaires, parfois masqués par l'explorateur.

Dans les explications, les chemins des fichiers sont donnés depuis la racine du dépôt. Sur ton poste, ajoute le préfixe `C:\Users\Karim\Repositories\property-platform\` pour obtenir leur chemin Windows absolu. Dans l'arborescence, lis chaque nom avec tous ses dossiers parents.

L'arborescence ci-dessous décrit les fichiers suivis par Git aujourd'hui. Les quinze fichiers de traduction sont regroupés pour la lisibilité ; les fichiers Python `__init__.py`, qui identifient les paquets, sont omis. Les dossiers générés par les outils sont expliqués séparément.

```text
property-platform/                   Racine du monorepo : code, outils et documentation de Property Platform
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
├── .github/                         Automatisation du travail et des vérifications sur GitHub
│   └── workflows/                   Procédures de contrôle exécutées par GitHub Actions
│       └── ci.yml                    Contrôles automatiques exécutés sur GitHub
├── apps/                            Applications exécutables : site et backend, puis futur mobile
│   ├── web/                          Application web Next.js
│   │   ├── package.json              Dépendances et commandes propres au site
│   │   ├── next.config.ts            Configuration Next.js et intégration multilingue
│   │   ├── tsconfig.json             Configuration du compilateur TypeScript
│   │   ├── Dockerfile                Construction de l'image du site
│   │   ├── messages/                Traductions des textes affichés aux utilisateurs
│   │   │   └── en.json, ar.json…     Textes de l'interface dans les quinze langues
│   │   ├── public/images/uae/        Photographies éditoriales locales, variantes WebP et crédits
│   │   ├── src/                     Code source de l'interface web
│   │   │   ├── app/                 Pages, routes et structures de page Next.js
│   │   │   │   ├── api/atlas/        Relais serveur borné des lectures de l’atlas
│   │   │   │   ├── globals.css       Styles communs du site
│   │   │   │   └── [locale]/         Routes associées à une langue, par exemple /en
│   │   │   │       ├── layout.tsx    Structure de page, langue, direction et métadonnées
│   │   │   │       ├── page.tsx      Page d'accueil actuelle
│   │   │   │       └── explore/page.tsx   Exploration locale des parcelles
│   │   │   ├── features/atlas/      Accueil, carte, liste, fiche et adaptateur API de l'atlas
│   │   │   ├── components/          Éléments d'interface réutilisables
│   │   │   │   ├── brand-mark.tsx         Rendu web du symbole public configuré
│   │   │   │   └── language-switcher.tsx   Sélecteur de langue interactif
│   │   │   ├── i18n/                Gestion commune des langues et de la navigation multilingue
│   │   │   │   ├── locales.ts       Langues acceptées et direction LTR/RTL
│   │   │   │   ├── routing.ts       Règles des URL et langue par défaut
│   │   │   │   ├── request.ts       Chargement des traductions de la langue demandée
│   │   │   │   ├── navigation.ts    Navigation tenant compte de la langue
│   │   │   │   └── types.d.ts       Déclarations de types pour les traductions
│   │   │   └── proxy.ts             Traitement du routage multilingue des requêtes
│   │   └── tests/                   Vérifications automatisées de l'interface web
│   │       └── i18n.test.mjs        Contrôles des langues, textes et règles de routage
│   └── api/                          Application backend Django
│       ├── manage.py                 Entrée des commandes Django
│       ├── pyproject.toml            Dépendances Python et configuration des contrôles
│       ├── uv.lock                   Versions résolues des dépendances Python
│       ├── .python-version           Version Python attendue pour cette application
│       ├── .env.example              Exemple de variables d'environnement locales
│       ├── Dockerfile                Image Python, Django et bibliothèques géographiques
│       ├── src/                     Code source du backend Python
│       │   └── property_platform/                 Paquet Python de notre backend
│       │       ├── config/          Assemblage et réglages techniques de Django
│       │       │   ├── urls.py       Branchement des URL API et administration
│       │       │   ├── wsgi.py       Entrée du serveur Python pour servir Django
│       │       │   └── settings/    Paramètres adaptés au développement, aux tests et à la production
│       │       │       ├── base.py          Réglages communs
│       │       │       ├── local.py         Réglages du développement local
│       │       │       ├── testing.py       Réglages des tests
│       │       │       └── production.py    Réglages et exigences de production
│       │       ├── api/             Réception des demandes HTTP et formats des réponses
│       │       │   └── router.py     API HTTP et contrôles de santé actuels
│       │       ├── modules/         Domaines métier séparés, chacun propriétaire de ses règles
│       │       │   ├── catalog/      Identité des biens et relations acceptées
│       │       │   │   ├── apps.py   Déclaration de l'application Django
│       │       │   │   ├── models.py Parcelles, rues, bâtiments, lieux et territoires typés
│       │       │   │   ├── services.py  Conversion des géométries et mutations du catalogue
│       │       │   │   ├── queries.py   Lectures spatiales bornées et identité
│       │       │   │   ├── map_queries.py   Couches de contexte et proximité dans PostGIS
│       │       │   │   ├── territories.py   Registre national de navigation pays/émirat/zone
│       │       │   │   ├── migrations/  Évolution du schéma du catalogue
│       │       │   │   └── README.md Responsabilités et dépendances du module
│       │       │   ├── evidence/     Sources, assertions et rapprochements
│       │       │   │   ├── apps.py
│       │       │   │   ├── models.py Sources, acquisitions, captures, observations et audit
│       │       │   │   ├── onwani.py Protocole parcellaire officiel
│       │       │   │   ├── map_sources.py, map_import.py  Couches officielles et OSM
│       │       │   │   ├── research_sources.py, research_import.py  Pages et repères déclarés
│       │       │   │   ├── project_sources.json  Registre de références à collecter
│       │       │   │   ├── services.py  Orchestration de l'import et de sa transaction
│       │       │   │   ├── queries.py   Provenance limitée destinée à l'affichage
│       │       │   │   ├── migrations/  Évolution du schéma des preuves
│       │       │   │   ├── management/commands/  Imports Onwani, couches Reem, références et satellite
│       │       │   │   └── README.md
│       │       │   └── publication/  Validation et versions publiées
│       │       │       ├── apps.py
│       │       │       ├── preview.py, map_preview.py  Projections locales bornées
│       │       │       ├── coverage.py  Profils de sources activés, couverture et navigation
│       │       │       ├── land_use.py  Catégories/couleurs, usage original conservé
│       │       │       └── README.md
│       │       └── export_openapi.py Export de la description de l'API
│       └── tests/                   Vérifications HTTP et d'intégration du backend
│           ├── test_health.py        Contrôles HTTP et test de disponibilité PostGIS
│           ├── test_onwani_protocol.py  Contrôles des réponses, identifiants et territoire
│           └── test_onwani_postgis.py   Transactions, géométries, audit et quarantaine
├── packages/                        Paquets réutilisables, dont les contrats partagés avec les clients
│   ├── contracts/                    Contrat entre le backend et les clients TypeScript
│   │   ├── package.json              Commandes de génération et de vérification
│   │   ├── tsconfig.json             Réglages de vérification des types
│   │   ├── openapi.json              Description exportée de l'API Django
│   │   ├── territories.json          Navigation nationale générée depuis le backend
│   │   └── src/                     Types utilisables par le site et le futur mobile
│   │       └── generated.ts          Types TypeScript générés depuis OpenAPI
│   └── branding/                     Configuration publique de marque, partagée par les clients
│       ├── package.json              Paquet @property-platform/branding, sans dépendance runtime
│       └── src/brand.ts              Nom affiché et chemin du symbole web
├── infra/                           Configuration des environnements d'exécution de la plateforme
│   └── local/                       Services et stockage nécessaires sur le poste de développement
│       └── compose.yaml              Services API et PostGIS, réseau et volume local
├── docs/                            Cadrage produit, décisions d'architecture et guides de travail
│   ├── README.md                     Index et enchaînement des décisions
│   ├── product/                     Besoins utilisateurs, marché et stratégie du produit
│   │   ├── ETUDE_PRODUIT_PROPERTY_PLATFORM.md       Besoins, marché et périmètre envisagé
│   │   └── STRATEGIE_PRODUIT_PROPERTY_PLATFORM.md   Approfondissement et différenciation
│   ├── architecture/                Choix techniques de référence et justification des décisions
│   │   ├── REVUE_ARCHITECTURE_PROPERTY_PLATFORM_V2.md   Architecture de référence
│   │   └── AUDIT_DECISION_STACK_PROPERTY_PLATFORM.md    Contre-audit réalisé après V2
│   ├── archive/                     Propositions remplacées, conservées pour leur historique
│   │   └── ARCHITECTURE_STACK_PROPERTY_PLATFORM.md     Proposition précédente remplacée
│   └── engineering/                 Guides pour installer, développer et maintenir le projet
│       ├── REPOSITORY.md              Ce guide de structure et de responsabilités
│       ├── DEVELOPMENT.md             Commandes de démarrage et explications
│       ├── REEM_MAP.md                Couverture, sources et correspondance avec le HTML
│       ├── VISUAL_DESIGN.md           Thème de l'accueil, crédits photos et animation accessible
│       ├── BRANDING.md               Identité technique stable, marque configurable et reprise locale
│       ├── UAE_COVERAGE.md           Couverture des Émirats et activation d'une nouvelle zone
│       ├── TOOLCHAIN.md               Versions exécutables et compatibilités
│       ├── INTERNATIONALIZATION.md    Politique des langues et du RTL
│       ├── DATA_PROVENANCE.md          Collecte directe, sources par information et audit
│       ├── DATABASE_DESIGN.md          Noms du domaine immobilier, audit SQL et trajectoire d'évolution
│       └── STRUCTURE_REVIEW.md        Revue critique de l'organisation
└── scripts/                         Utilitaires de vérification, préparation du site et acquisitions isolées
    ├── acquire_reem_imagery.py        Acquisition et recadrage Sentinel hors du runtime API/web
    ├── imagery-requirements.txt      Dépendances verrouillées de cet environnement raster isolé
    ├── check-doc-links.mjs            Vérification des liens locaux dans les documents
    ├── prepare-web-runtime.mjs        Préparation des ressources de l'artefact web autonome
    ├── migrate-local-identity.mjs     Sauvegarde et reprise vérifiée vers une nouvelle identité locale
    └── smoke-web.mjs                  Vérification du site construit et des routes de langue
```

## Pourquoi séparer ces dossiers ?

### Extension de l'atlas : couches géographiques typées

Le module `catalog` possède aussi `Street` (tracé multiligne), `Building` (empreinte multipolygone), `Place` (repère ponctuel) et `AdministrativeArea` (district/secteur multipolygone), dans `real_estate`. Ces objets conservent leurs identités par fournisseur : un bâtiment OSM n'est pas un permis, un repère n'est pas une identité commerciale approuvée. `evidence` possède leur observation avec exactement une cible typée, une capture, une version de mapping et un audit de révision. La direction reste `publication → evidence → catalog`. Les connecteurs Onwani et OSM sont séparés ; l'API lit PostgreSQL et ne collecte rien à l'ouverture de la carte. Un rapprochement spatial reste calculé et signalé comme tel, sans renommer une parcelle. Le HTML utilisateur est une référence de fonctions et une piste de recherche, jamais une source cadastrale. `evidence` possède aussi ResearchReference et ImageryScene ; le premier est une référence capturée, le second un petit dérivé satellite du pilote. Le traitement Rasterio est isolé dans `scripts/acquire_reem_imagery.py`, avec dépendances séparées dans `scripts/imagery-requirements.txt`. Les captures retraitées conservent une clé étrangère parent et leurs dates originales. Les rapprochements spatiaux sont réversibles et ne fusionnent aucune identité de projet.

### Couverture nationale : configuration et données réelles

Le produit vise les sept émirats, avec Al Reem comme premier jeu de données. `catalog.territories` possède le registre typé de navigation pays → émirat → zone ; ses rectangles approximatifs ne sont pas des frontières cadastrales. `publication.coverage` possède les profils de sources explicitement activés et compose les nombres via `catalog.queries`, sans modifier ses tables. Les collecteurs `evidence` conservent leur vraie portée et leurs clés stables. La direction `publication → evidence → catalog` reste inchangée.

L'export backend génère `packages/contracts/territories.json` avec OpenAPI. Le web utilise ce snapshot pour son accueil statique et l'API pour les nombres actuels de la zone ; il ne recopie pas une liste d'émirats indépendante. `territory-explorer.tsx` possède les sélecteurs et l'historique de l'URL, réinitialise l'exploration entre zones et affiche les couvertures non activées. Une nouvelle zone requiert ses sources, mappings et contrôles, pas seulement une case dans le menu. Voir [UAE_COVERAGE.md](UAE_COVERAGE.md) pour la procédure et les limites du prototype GeoJSON.

### `apps/web` : ce que l'utilisateur voit

Ce dossier possède les pages et interactions du site. `apps/web/src/app/` définit les routes ; les crochets de `[locale]` indiquent un paramètre variable, pas un dossier à créer pour chaque langue. Le même `apps/web/src/app/[locale]/page.tsx` peut donc servir `/en`, `/ar` ou `/fr`, avec des textes différents dans `apps/web/messages/`.

`apps/web/src/components/` accueille les composants réellement réutilisables. `apps/web/src/i18n/` centralise les règles de traduction et de navigation pour éviter que chaque page réinvente la gestion des langues. Le site ne doit pas accéder directement aux tables PostgreSQL : les demandes métier passent par l'API.

### `apps/api` : les données et les règles métier

`config` règle le fonctionnement de Django ; `api` reçoit les demandes HTTP ; `modules` organise le métier. Cette séparation permet à une future application mobile, à l'administration et à un import de réutiliser les mêmes règles sans les recopier.

| Module | Ce qu'il possédera | Exemple dans notre produit |
|---|---|---|
| [catalog](../../apps/api/src/property_platform/modules/catalog/README.md) | Identité des territoires, parcelles, bâtiments et logements, relations acceptées | Déterminer à quel bâtiment appartient un logement |
| [evidence](../../apps/api/src/property_platform/modules/evidence/README.md) | Sources, acquisitions, assertions et décisions de rapprochement | Conserver qu'un document daté annonce une livraison, avec sa provenance |
| [publication](../../apps/api/src/property_platform/modules/publication/README.md) | Validation, projections et versions publiées | Publier une version validée du dossier en passant par les services des autres modules |

**Le catalogue et les preuves possèdent les modèles de parcelles, empreintes de bâtiments, rues, lieux et acquisitions.** Le module publication assemble les projections de lecture sans modèle propre. Les logements, prix et dossiers publics approuvés restent à implémenter. Les `apps.py` déclarent les modules à Django ; les `README.md` précisent leurs frontières.

Le domaine immobilier utilise le schéma SQL `real_estate` et la table `real_estate.parcel` ; les preuves utilisent `evidence.source`, `evidence.ingestion_run`, `evidence.capture`, `evidence.parcel_observation`, `evidence.audit_event` et `evidence.quarantined_observation`. Les tables techniques Django et fonctions PostGIS restent dans `public`. Les migrations déplacent les tables existantes et leurs relations, sans recopier les données. Le module Django installé conserve son nom `catalog`, pour préserver ses identifiants de migrations et de modèles. [DATABASE_DESIGN.md](DATABASE_DESIGN.md) décrit ce choix et les contrôles d'intégrité.

Le `search_path` de la connexion Django est fixe : `public,real_estate,evidence`. Les modèles utilisent des noms de tables simples et uniques sur ce chemin, ce qui permet de conserver le backend Django/PostGIS standard, son introspection et ses outils de test. Les migrations SQL utilisent des noms explicitement qualifiés. Ne pas créer dans `public` ou un autre schéma du chemin une table homonyme qui masquerait une table métier ; les migrations refusent ces collisions. Les rôles de production ne doivent pas pouvoir créer arbitrairement de nouveaux objets sur ce chemin. Un nouveau schéma ou nom de table nécessite une revue de ces règles, des permissions, des migrations et des tests.

Lors de l'ajout d'un modèle métier, une migration générée peut créer sa table dans `public`, premier schéma du chemin : prévoir explicitement son placement dans le schéma propriétaire avec des opérations SQL et un état Django cohérent. Le test PostGIS `test_domain_tables_have_unique_names_and_their_owned_schema` contrôle l'emplacement effectif des modèles gérés de `catalog` et `evidence` et l'unicité de leurs noms. Une nouvelle table ou un nouveau domaine doit étendre ces contrôles ; ne pas supposer que `db_table` simple choisit son schéma de création.

`apps/api/src/property_platform/config/settings/base.py` est partagé, puis complété par `apps/api/src/property_platform/config/settings/local.py`, `apps/api/src/property_platform/config/settings/testing.py` ou `apps/api/src/property_platform/config/settings/production.py`. La présence de ce dernier ne signifie pas que le site est déployé. `apps/api/manage.py` sert notamment à lancer les migrations ou à créer un administrateur ; ce n'est pas une page web.

### `packages/contracts` : l'accord entre le site et l'API

Le backend exporte ses routes et formats de réponse dans `packages/contracts/openapi.json`. Le générateur produit ensuite `packages/contracts/src/generated.ts`, utilisé pour vérifier les types côté TypeScript. Ces deux fichiers sont suivis par Git et mis à jour ensemble via les commandes documentées dans [DEVELOPMENT.md](DEVELOPMENT.md) ; ils ne se corrigent pas manuellement.

Ce paquet contient des descriptions de données, pas une copie des modèles Django ni des règles métier. Il pourra aussi être consommé par le futur mobile.

### `packages/branding` : présentation publique indépendante du métier

Ce paquet possède le nom commercial affiché et le chemin du symbole web. L'en-tête, les titres, l'accueil et les signatures PNG le consomment ; le futur mobile pourra réutiliser le nom. Il ne contient ni secret, ni territoire, ni fournisseur, ni identité d'infrastructure. La direction est `web → branding` et, plus tard, `mobile → branding` ; `branding` ne dépend d'aucun autre module. L'adaptateur `apps/web/src/components/brand-mark.tsx` possède le rendu web du symbole, dont le fichier et l'icône d'onglet sont sous `apps/web/public/brand/`.

Les identités techniques restent `property-platform`, `property_platform`, `@property-platform/*` et `PROPERTY_PLATFORM_*` lors d'un changement commercial. Les labels Django `catalog`, `evidence`, `publication`, les schémas SQL et les preuves gardent leur identité. Voir [BRANDING.md](BRANDING.md) pour les fichiers à modifier et la reprise contrôlée d'une installation locale précédente. `scripts/migrate-local-identity.mjs` est un outil de maintenance explicite : il ne s'exécute jamais au démarrage, refuse une cible préexistante et conserve la source pour récupération.

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
| `apps/api/.venv/` | Environnement Python local créé par uv si tu utilises ce parcours | Non, le code du projet reste dans `apps/api/src/property_platform/` |
| `__pycache__/`, `.pytest_cache/`, `.ruff_cache/` | Caches des outils Python | Non, ils ne sont pas des sources |
| `.cache/`, `.tools-env/` | Éventuels caches et outils locaux utilisés pendant la préparation | Non, leur présence dépend du poste et ils ne sont pas requis comme dossiers source |
| `.idea/` | Réglages locaux de PyCharm | Ne pas y placer le code ; vérifier les exclusions Git avant tout partage de réglages |

Les caches de code ne sont pas le stockage de PostgreSQL. **Supprimer un volume Docker peut supprimer les données ; recréer un cache Next.js ou réinstaller des dépendances ne remet pas la base à zéro.**

## Où ajouter une nouvelle fonctionnalité ?

| Besoin | Emplacement prévu | État actuel |
|---|---|---|
| Modifier les textes d'accueil | `apps/web/messages/<langue>.json` | Existe |
| Modifier la page d'accueil | `apps/web/src/app/[locale]/page.tsx` | Existe |
| Modifier l'atlas ou ajouter une fiche immobilière | `apps/web/src/features/atlas/` pour le pilote parcellaire ; un module `property/` viendra avec les dossiers immobiliers | Atlas local créé, dossiers bâtiment/unité à créer |
| Ajouter un composant partagé entre plusieurs fonctionnalités | `apps/web/src/components/` | Dossier existant ; y placer seulement les composants réutilisables |
| Ajouter les modèles de bâtiments et leurs règles | `apps/api/src/property_platform/modules/catalog/` | Parcel, Street, Building, Place, AdministrativeArea existants ; logements à ajouter |
| Ajouter les sources et preuves | `apps/api/src/property_platform/modules/evidence/` | Premiers modèles d'acquisition et observations Onwani existants |
| Ajouter une route métier HTTP | `apps/api/src/property_platform/api/`, branchée au routeur | À créer avec les services métier qu'elle appelle |
| Ajouter des migrations Django | `migrations/` dans le module propriétaire | À générer avec Django lorsque les modèles arrivent |
| Ajouter un domaine prix, avis ou documents | Module dédié sous `apps/api/src/property_platform/modules/` | À créer quand ses responsabilités et dépendances sont définies |
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
   Voir [la collecte directe et la provenance](DATA_PROVENANCE.md) pour les acquisitions, les dates de chaque information et l'audit des décisions. Le HTML de référence n'est pas un jeu de données à importer.
3. Une opération sensible conserve auteur, raison et version ; les permissions couvrent HTTP, administration, fichiers et futurs traitements.
4. Toute évolution d'API conserve sa compatibilité ou documente une rupture. Les types générés ne sont jamais édités manuellement.
5. Les migrations sont revues et exécutées explicitement, pas au démarrage concurrent de chaque processus. Les comptes base de migration/exécution seront séparés au déploiement.
6. Les durées, montants et identifiants sont validés côté serveur. UTC en stockage ; fuseau et format d'affichage côté client.
7. L'anglais est la langue par défaut. Les traductions d'interface restent séparées des traductions documentaires ; les preuves originales et identifiants restent stables. Les layouts utilisent des propriétés CSS logiques pour le RTL.

## Première exploration locale — 11 octobre 2026

`apps/web/src/features/atlas/` possède l'accueil, l'exploration, la carte et les types consommés depuis les contrats générés. Les routes localisées assemblent ces écrans ; `apps/web/src/app/api/atlas/` relaie uniquement les lectures fixes de l’atlas vers une origine configurée côté serveur, avec délai et budget de réponse. Aucune clé ni URL amont configurable par un visiteur n'est envoyée au client. MapLibre est chargé uniquement dans l'exploration ; l'accueil est rendu côté serveur sans ce moteur.

`catalog/queries.py` possède les lectures géographiques bornées ; `evidence/queries.py` possède la projection de provenance autorisée ; `publication/preview.py` les assemble sans mutation. L'API `api/parcels.py` valide les entrées et expose un contrat limité. La direction reste publication → evidence/catalog. Les migrations ajoutent les objets cartographiques typés dans leurs schémas propriétaires. Les originaux, opérateurs, attributs bruts et historiques internes ne sont pas exposés.

Les endpoints `/api/v1/preview/parcels` et `/api/v1/preview/parcels/{id}` sont un aperçu de recherche **local**, pas une publication approuvée. Django exige DEBUG et PROPERTY_PLATFORM_PARCEL_PREVIEW ; hors DEBUG ils refusent même un flag activé. Un web compilé exige aussi l'opt-in PROPERTY_PLATFORM_ENABLE_LOCAL_PREVIEW=1. Ce flag ne permet pas de contourner Django. Les droits de diffusion, rôles, authentification du personnel, limitation de trafic distribuée et CSP complète avec nonces restent à définir avant publication.

La carte affiche les usages colorés, secteurs, rues et noms, empreintes 2D, lieux, références et vues satellite ; voir [la couverture et les limites](REEM_MAP.md). Les volumes 3D ne sont pas générés. La liste paginée fournit une alternative si WebGL ne fonctionne pas. La couverture d'une source, la validité de géométrie et l'approbation d'un dossier sont trois notions distinctes.

## Ce que le socle ne prétend pas fournir

Le premier import manuel Onwani alimente les parcelles et conserve captures, observations et audit. Il ne publie pas automatiquement un dossier. L'accueil et la carte proposent désormais un aperçu local. Auth Supabase, stockage objet, queue et génération ne sont pas encore intégrés. L'administration Django est locale à ce stade ; elle ne doit pas être ouverte en production avant le parcours d'accès du personnel et ses règles métier. Les nouveaux modèles n'ont pas d'éditeur Django Admin qui contourne leurs services.
