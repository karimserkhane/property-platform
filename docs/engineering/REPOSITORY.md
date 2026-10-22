# Structure et règles de dépendance

**Accès d'aperçu sans VPN — 22 octobre 2026.** `web/src/preview-access.ts` possède la vérification d'une clé temporaire à forte entropie, comparée en temps constant à une empreinte SHA-256. `proxy.ts` l'applique avant les pages, API et fichiers statiques, puis conserve le middleware de langue existant. L'aperçu de recherche compilé refuse les requêtes si son secret manque ; le développement ordinaire reste indépendant. Les secrets opérateur restent hors Git et hors images. Direction : contrôle HTTP web → présentation, sans identité métier, migration ou nouvelle dépendance. Voir [REMOTE_PREVIEW.md](REMOTE_PREVIEW.md).

**Qualité cartographique — 22 octobre 2026.** `evidence/sdi_protocol.py` possède le protocole public AD-SDI et son dictionnaire propre ; `sdi_import.py` possède les preuves et la comparaison métrique au catalogue existant. Le collecteur `ingestion/collectors/sdi.py` acquiert hors transaction et rejoue les reçus via le gateway. Direction : ingestion → evidence → catalog ; `publication/coverage.py` lit les namespaces des deux sources. Aucun nouveau modèle métier ; migration additive 0030 sur les opérations autorisées. `atlas/map-markers.ts` possède les filtres indépendants des lieux utiles et commerces ; `map-style.ts` possède le masque d'eau partagé avec les cartes de quartier. Les géométries originales restent intactes. Voir [MAP_DATA_QUALITY.md](MAP_DATA_QUALITY.md).

**Al Maryah et repères — 22 octobre 2026.** `catalog/territories.py`, `evidence/collection_profiles.py` et `publication/coverage.py` possèdent le périmètre Maryah. `evidence/project_maryah.py` complète seulement les couples source/projet examinés, sans réseau ou ORM. `atlas/map-markers.ts` possède la projection des types enregistrés vers les symboles ; `map-legend.tsx` partage leur présentation entre Explore et quartier, sans changer les identités. Direction : web → contrats ; ingestion → protocoles/gateway evidence → catalog. Aucun nouveau modèle ou service. Voir [les pipelines et limites](AL_MARYAH.md).

**Sources publiques des projets — 21 octobre, soir.** `projects/evidence.tsx` n'accepte et n'affiche que des métadonnées de source ; les extraits d'extracteur et pointeurs restent hors du parcours public. `presentation.ts` groupe les citations par capture et formate les dates sans erreur sur une métadonnée invalide. `scripts/smoke-projects.mjs` contrôle les pages réellement compilées, les volets et toutes les pages de l'annuaire ; il ne déclenche aucune acquisition ni écriture. Voir [l'audit de tous les affichages projet](PROJECT_DISPLAY_AUDIT_20261021.md).

**Revue UI/UX — 21 octobre 2026.** `components/site-navigation.tsx` possède la navigation commune ordinateur/mobile, sans dépendance métier. `projects/directory-navigation.ts` possède les liens, la taille de page et la reprise de pagination ; l'annuaire est un composant serveur avec formulaire GET. `projects/presentation.ts` groupe les typologies sans perdre les assertions, qualifie les rôles documentaires et sélectionne les photographies publiables. `documents.tsx`, `media-card.tsx` et `evidence.tsx` présentent les plans, médias et preuves ; `directory.module.css` et `dossier.module.css` isolent leurs compositions. Direction inchangée : pages → présentation → contrats, sans SQL ni collecte. Voir [la revue UI/UX](UI_UX_REVIEW_20261021.md).

**Revue critique — 21 octobre 2026.** `evidence/project_queries.py` partage les règles de publication/exclusion et de géométries utilisables entre dossier, annuaire et carte. L'API `/projects` possède la recherche bornée et la pagination (`q`, `offset`, `limit`, `total`) ; la route serveur de l'annuaire la consomme et `directory.tsx` possède le formulaire GET et ses liens de navigation localisés. `projects/presentation.ts` possède la qualification d'une URL de promoteur à partir des preuves exactes, partagée par couverture et dossier. Aucun nouveau modèle ou pipeline ; contrats régénérés. Voir [les défauts corrigés et les priorités restantes](PLATFORM_REVIEW_20261021.md).

**Catalogue et reconstruction — 21 octobre 2026.** `evidence/project_psi.py`, `project_adrec.py`, `project_propertyfinder.py` et les adaptateurs HTML possèdent l'extraction pure des sources examinées ; `project_models.py` conserve leur origine, la partie déclarée/enregistrée et la nature du total. `project_queries.py` arbitre les sources avec leur histoire. `ingestion/project_archive.py` possède les reçus privés des fiches et catalogues, adressés par empreinte ; `project_bootstrap.py` orchestre l'initialisation explicite d'un catalogue vide et leur rejeu par le gateway. Direction : ingestion → protocoles/services evidence → catalog ; aucune dépendance evidence → ingestion ni modèle métier JSON universel. Les migrations 0027–0029 ajoutent l'origine, étendent les portées et distinguent unités annoncées et logements enregistrés. Le registre atteint 174 fiches nommées, 117 Reem et 57 Saadiyat. Voir [la couverture, les limites et la reconstruction](PROJECT_CATALOGUE.md).

**Analyses de carte — 20 octobre 2026.** `atlas/map-analysis.ts`, `project-clusters.ts`, `solar.ts`, `map-workbench.tsx` et `map-comparison.tsx` possèdent les calculs de présentation et outils partagés avec les cartes projet. `publication/market_map.py` et `atlas/market-district-map.tsx` possèdent l'agrégation et le rendu sur la page Marché. `evidence/accessibility_models.py` et `accessibility.py` possèdent les graphes routiers archivés, fragments, demandes et contours PostGIS ; `api/accessibility.py` les expose sans acquisition réseau. `ingestion/collectors/accessibility.py` possède le transport borné et les appels au moteur Valhalla privé de `infra/local/routing/`, isolé pour ses calculs natifs lourds. Direction : web/API → publication/evidence ; ingestion → evidence + moteur privé. Le moteur ne dépend pas du catalogue et ne télécharge pas de source. Migrations 0025/0026, audit uniforme et deux flows dédiés. Voir [MAP_ANALYSIS.md](MAP_ANALYSIS.md).

**Bâtiments 3D — 20 octobre 2026.** `atlas/building-3d.ts` possède la projection des hauteurs, les expressions et la caméra ; `building-popup.ts` présente les volumes mondiaux sans créer d’identité catalogue. `map-view-control.tsx` compose perspective, source de bâtiments et fond existant pour Explore et la carte projet. Les couches lisent le catalogue ou les tuiles OpenFreeMap déjà archivées par Prefect, avec une seule source 3D visible. Direction : présentation → contrats/tuiles archivées ; aucune nouvelle dépendance, table ou collecte parallèle. Voir [BUILDINGS_3D.md](BUILDINGS_3D.md).

**Historique uniforme — 20 octobre 2026.** `evidence/history_models.py`, `history.py`, `catalogue_history.py` et `pipeline_inventory.py` possèdent le journal technique PostgreSQL, les exclusions réversibles, les reprises de champs et la couverture des tables. `evidence/basemap_models.py`/`basemap_archive.py` possèdent la file et les versions typées des tuiles ; `ingestion/collectors/basemaps.py` possède leur transport borné. `api/basemaps.py` lit l’archive et enregistre une demande sans acquisition réseau ; `web/atlas/archived-tiles.ts` attend son traitement Prefect. La direction reste `publication/API → evidence → catalog`, `ingestion → evidence`. Aucun traitement raster/OCR dans le runtime web/API. Le JSON du journal est technique et ne remplace pas les modèles métier. Voir [DATA_HISTORY.md](DATA_HISTORY.md).

Le dépôt conserve les choix de la revue V2 et du contre-audit. Un monorepo contient plusieurs applications, sans en faire des microservices. Les études sont dans `docs/product`, les décisions actuelles dans `docs/architecture` et les propositions remplacées dans `docs/archive`. Seuls README et AGENTS restent des documents Markdown de racine.

Les versions exécutables ont ensuite été actualisées ; [TOOLCHAIN.md](TOOLCHAIN.md) fait référence pour leurs versions et exceptions, tandis que les anciennes études conservent le contexte de leurs décisions.

**Extension projets du 15 octobre 2026.** `catalog` possède `Developer`, `Project` et `project_services.py` pour les identités stables. `evidence` possède `project_models.py`, `project_registry.json`, `project_protocol.py` (extraction pure), `project_import.py` (snapshots et rapprochements réversibles), `project_queries.py` (projection bornée) et `project_media_storage.py` (fichiers privés, revue des droits, publication explicite). Les modèles sont réexportés par `evidence/models.py` pour Django. La direction reste `API/publication → evidence → catalog` et `evidence → object_storage` ; aucun accès réseau pendant la transaction d'import. `object_storage/downloads.py` gère les plages d'octets sans importer Django. `apps/ingestion/collectors/projects.py` acquiert les pages et `media_files.py` contrôle les manifestes privés ; les deux appellent les services métier hors du thread async Prefect. `apps/web/src/features/projects/` possède les fiches, `app/[locale]/projects/[slug]/page.tsx` leur route et `app/api/atlas/project-media/[id]/route.ts` le relais par flux. La carte conserve ses règles de sélection. Le [guide des projets](PROJECTS.md) décrit les trois nouveaux déploiements, les tables et l'exploitation.

## Comment lire l'arborescence

**Carte immersive et pages projets — 17 octobre 2026.** L’explorateur occupe le viewport sous l’en-tête. `atlas/selection-preview.tsx` possède le résumé compact des bâtiments/parcelles et l’ouverture des détails existants ; `projects/map-summary.tsx` possède la lecture de la fiche projet flottante. Les parcelles, rues, bâtiments, lieux et noms sont visibles par défaut ; les secteurs et codes restent facultatifs. La carte différée de quartier réutilise les lectures bornées de parcelles, la priorité de sélection et les styles d’atlas pour la seule île du projet. Les dictionnaires `Use` sont fournis par la route serveur, sans nouvelle collecte ni identité déduite. `projects/cover.tsx` possède la galerie manuelle avec transitions, médias approuvés et photos d'ambiance identifiées. `projects/neighbourhood.tsx` possède l'activation de la carte du quartier ; `neighbourhood-map.tsx` réutilise les couches API et les styles purs d'`atlas`, sans importer son explorateur complet. `neighbourhood-config.ts` construit l'URL Google Embed facultative ; la route serveur lit la configuration et fournit le territoire de la fiche. Direction : route → présentation/configuration → lecture API ; aucune collecte, table ou migration. Voir [MAP_PROVIDERS.md](MAP_PROVIDERS.md).

**Refonte de présentation — 16 octobre 2026.** `features/atlas/home.tsx` possède le parcours d'accueil et les entrées Reem/Saadiyat ; `explorer.tsx` et `explorer.module.css` possèdent la sélection cartographique, les réglages et la fiche courte, sans recherche générale ni grille de bâtiments. `atlas/pagination.tsx` possède le rendu/focus de la pagination et dépend du calcul pur `atlas/page-window.ts`, qui ne dépend ni de React ni de l'API. `features/projects/directory.tsx` possède le formulaire de recherche et les liens de pagination ; depuis la revue du 21 octobre, la route serveur lit les pages filtrées de l’API, sans créer d’identité ni déclencher de collecte. `components/ui-icon.tsx` possède des SVG décoratifs réutilisables et ne dépend d'aucun module métier. La direction reste `route serveur → lecture API/contrat → composants de présentation` et `fonctionnalités → composants génériques`. Les dictionnaires des langues activées restent propriétaires des libellés ; les preuves conservent leur langue originale. Aucun changement de table, d'ingestion ou de contrat HTTP pour cette refonte. Voir [les parcours et la présentation](VISUAL_DESIGN.md).

**Prévisualisation distante facultative — 16 octobre 2026.** `infra/local/compose.remote-preview.yaml` possède le connecteur Tailscale userspace, isolé des modules applicatifs et sans dépendance Python/JavaScript supplémentaire. Il partage uniquement l'espace réseau du web et relaie son port 3000 par Serve privé ; aucun port de base ou d'administration n'est déclaré. L'identité du connecteur est un secret de volume Docker, jamais un fichier versionné. Les instructions et limites sont dans [REMOTE_PREVIEW.md](REMOTE_PREVIEW.md). La CI valide la composition YAML sans créer de compte ou d'accès distant.

**Extension des deux îles — 16 octobre 2026.** Le registre examiné contient 57 projets/programmes de 10 promoteurs. Dans `evidence`, `project_adapters.py` possède les extracteurs propres aux éditeurs, `project_catalogues.json` borne les 13 catalogues et `project_discovery.py` possède les candidats de découverte. Leur table `evidence.project_source_candidate` conserve capture, URL, statut et opérateur ; elle ne crée ni projet canonique ni localisation. Le territoire de collecte n'est pas une preuve de localisation. Chaque projet et catalogue a une identité d'exécution et des reçus distincts. Ces fichiers suivent les mêmes dépendances que les autres services `evidence`. La route web `app/[locale]/projects/page.tsx` possède l'annuaire filtré, alimenté par la projection bornée `project_queries.project_directory` et le contrat API généré. Voir [la couverture et les limites](PROJECTS.md#8-extension-reem-et-saadiyat--16-octobre-2026).

**Sélection, proximité et dossiers — 16 octobre 2026.** `features/projects/map-summary.tsx` possède la lecture client annulable et la fiche courte de carte ; `detail.tsx` possède uniquement le dossier indépendant. L’annuaire ouvre la page projet et propose un lien secondaire vers la carte. `atlas/surroundings.tsx` possède le volet de proximité, chargé à son ouverture via le relais fixe `app/api/atlas/surroundings/[target]/[id]/route.ts`. `catalog/map_queries.py` possède les requêtes PostGIS indexées et bornées de voisinage/superposition ; `publication/surroundings.py` assemble les provenances et classe les équipements via les tags conservés, sans modifier les identités. La direction reste `API/publication → evidence/catalog`. `atlas/presentation.ts` possède les noms potentiels d’affichage, précédés de `≈`, sans mutation cadastrale. Le connecteur `evidence/map_sources.py` définit `osm_place_kind`, partagé avec l’import XML ; le profil OSM acquiert commerces, équipements et transports. Les déploiements Prefect réutilisent ce collecteur ; `reem-osm-bootstrap` complète la reprise XML manuelle déjà disponible pour Saadiyat, avec quatre fenêtres enregistrées et sans calendrier. Contrats régénérés ; aucune nouvelle table ni migration. Voir [NEIGHBOURHOOD.md](NEIGHBOURHOOD.md).

`features/projects/neighbourhood-focus.ts` possède le calcul pur de cadrage des points et contours explicitement liés au projet. La fiche API fournit ces `map_locations` via `evidence/project_queries.py`, indépendamment des limites des couches générales. `neighbourhood-map.tsx` les consomme pour son zoom initial et son accent visuel ; il ne déduit aucune identité par nom ou proximité et ne change pas la caméra de l’explorateur général. Direction : route → contrat projet → carte de quartier → calcul pur. `evidence/project_locations.py` possède la validation territoriale et la matérialisation atomique des positions déclarées extraites par `research_sources.py`, appelée par l’import projet après acquisition, sans réseau pendant la transaction. Les liens révoqués restent révoqués. Les géométries, captures, observations et liens réutilisent leurs tables propriétaires existantes. `publication/coverage.py` ajoute les namespaces des projets enregistrés à leur île ; la présentation de lecture peut utiliser le lien projet sans exiger de ligne `PropertyPresentation`. Aucun nouveau module de domaine ni migration. Voir [MAP_PROVIDERS.md](MAP_PROVIDERS.md).

**Extension stockage du 15 octobre 2026.** `property_platform.object_storage` est le paquet d’infrastructure des adaptateurs disque/S3. Il ne dépend ni des modules métier, ni de l’API, ni de la configuration Django ; Import Linter vérifie cette frontière. Le module **evidence** possède `StoredObject`, `CaptureObject`, `MediaPublication` et `media_storage.py`. La direction reste `publication/API → evidence → object_storage`, avec `evidence → catalog` pour les identités. L’application ingestion appelle ce service après l’import et hors transaction SQL ; elle ne possède pas les tables. Les secrets ne passent jamais dans les contrats clients. Voir [MEDIA_STORAGE.md](MEDIA_STORAGE.md) pour la reprise, les droits, le stockage persistant et le passage facultatif à R2/CDN.

La **racine** est le dossier `property-platform`. Un élément terminé par `/` est un dossier ; les éléments indentés sont à l'intérieur de ce dossier. `src` contient le code source, `tests` les contrôles automatisés et `config` les réglages de l'application. Les noms qui commencent par un point, comme `.github`, sont aussi des fichiers ou dossiers ordinaires, parfois masqués par l'explorateur.

Dans les explications, les chemins des fichiers sont donnés depuis la racine du dépôt. Sur ton poste, ajoute le préfixe `C:\Users\Karim\Repositories\property-platform\` pour obtenir leur chemin Windows absolu. Dans l'arborescence, lis chaque nom avec tous ses dossiers parents.

L'arborescence ci-dessous décrit les fichiers suivis par Git aujourd'hui. Les fichiers de traduction sont regroupés pour la lisibilité ; les fichiers Python `__init__.py`, qui identifient les paquets, sont omis. Les dossiers générés par les outils sont expliqués séparément.

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
├── apps/                            Applications exécutables : site, backend et ingestion, puis futur mobile
│   ├── web/                          Application web Next.js
│   │   ├── package.json              Dépendances et commandes propres au site
│   │   ├── next.config.ts            Configuration Next.js et intégration multilingue
│   │   ├── tsconfig.json             Configuration du compilateur TypeScript
│   │   ├── Dockerfile                Construction de l'image du site
│   │   ├── messages/                Traductions des textes affichés aux utilisateurs
│   │   │   └── en.json, ar.json…     Textes de l'interface par langue activée
│   │   ├── public/images/uae/        Photographies éditoriales locales, variantes WebP et crédits
│   │   ├── public/fonts/             Fontes WOFF2 locales, plages Unicode, licences et provenance
│   │   ├── src/                     Code source de l'interface web
│   │   │   ├── app/                 Pages, routes et structures de page Next.js
│   │   │   │   ├── api/atlas/        Relais serveur borné des lectures de l’atlas
│   │   │   │   ├── globals.css       Styles communs du site
│   │   │   │   └── [locale]/         Routes associées à une langue, par exemple /en
│   │   │   │       ├── layout.tsx    Structure de page, langue, direction et métadonnées
│   │   │   │       ├── page.tsx      Page d'accueil actuelle
│   │   │   │       └── explore/page.tsx   Exploration locale des parcelles
│   │   │   ├── features/projects/   Annuaire paginé avec recherche serveur, fiches projets, promoteurs, documents et vidéos
│   │   │   ├── features/atlas/      Accueil, carte, liste, fiche et adaptateur API de l'atlas
│   │   │   │   ├── explorer.tsx, explorer.module.css  Carte centrale et fiche de sélection
│   │   │   │   └── pagination.tsx, page-window.ts    Commandes de pagination et calcul borné indépendant
│   │   │   ├── theme/fonts.ts        Profils de préchargement des polices locales, sans réseau tiers
│   │   │   ├── components/          Éléments d'interface réutilisables
│   │   │   │   ├── brand-mark.tsx         Rendu web du symbole public configuré
│   │   │   │   ├── ui-icon.tsx            SVG décoratifs partagés, sans dépendance métier
│   │   │   │   └── language-switcher.tsx   Sélecteur de langue interactif
│   │   │   ├── i18n/                Gestion commune des langues et de la navigation multilingue
│   │   │   │   ├── locales.ts       Registre des langues, noms, direction LTR/RTL et profil de police
│   │   │   │   ├── routing.ts       Règles des URL et langue par défaut
│   │   │   │   ├── request.ts       Chargement des traductions de la langue demandée
│   │   │   │   ├── navigation.ts    Navigation tenant compte de la langue
│   │   │   │   └── types.d.ts       Déclarations de types pour les traductions
│   │   │   └── proxy.ts             Traitement du routage multilingue des requêtes
│   │   └── tests/                   Vérifications automatisées de l'interface web
│   │       └── i18n.test.mjs        Contrôles des langues, textes et règles de routage
│   ├── ingestion/                    Collectes et imports programmés, exécutés séparément du site/API
│   │   ├── pyproject.toml            Prefect, HTTPX et dépendance locale au paquet métier Django
│   │   ├── uv.lock                   Versions Python résolues pour le runtime d'ingestion
│   │   ├── Dockerfile                Image d'ingestion avec bibliothèques GIS, sans runtime raster/OCR
│   │   ├── src/property_platform_ingestion/   Code de planification et acquisition
│   │   │   ├── __main__.py           Commandes serve, check et datasets
│   │   │   ├── registry.py           Trente-cinq déploiements, portées fixes et identités d'exécution
│   │   │   ├── deployments.py        Enregistrement et conservation des horaires modifiés dans l'UI
│   │   │   ├── flows.py              Flows/tâches Prefect : exécuter, superviser et signaler les résultats
│   │   │   ├── runtime.py            Sous-processus Django borné, hors du thread async de Prefect
│   │   │   ├── domain.py             Assemblage des collecteurs et appel de la passerelle métier
│   │   │   ├── storage.py            Checkpoints privés de reçus pour rejouer une acquisition
│   │   │   └── collectors/           Transport HTTPS borné et adaptateurs sans mutation de base
│   │   │       ├── http.py           URLs enregistrées, certificats, cadence et limites de réponse
│   │   │       ├── map.py            Transport des protocoles Onwani parcelles et couches ArcGIS/OSM
│   │   │       ├── references.py     Captures des références publiques examinées
│   │   │       ├── properties.py     Reçus des présentations et photographies autorisées
│   │   │       ├── projects.py       Acquisition des pages officielles de projets et conditions
│   │   │       └── snapshots.py      Précollecte puis replay exact, sans réseau dans la transaction SQL
│   │   └── tests/                    Contrôles sans réseau : collecte, reprise et horaires de déploiement
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
│       │       ├── object_storage/  Adaptateurs de fichiers locaux et S3/R2, indépendants du métier
│       │       │   ├── core.py       Flux bornés, SHA-256, formats et clés immuables
│       │       │   └── adapters.py   Disque persistant et SDK S3, sans création de ressources cloud
│       │       ├── modules/         Domaines métier séparés, chacun propriétaire de ses règles
│       │       │   ├── catalog/      Identité des biens et relations acceptées
│       │       │   │   ├── apps.py   Déclaration de l'application Django
│       │       │   │   ├── models.py Parcelles, rues, bâtiments, lieux et territoires typés
│       │       │   │   ├── collection_profiles.py  Requêtes et identités examinées, distinctes par territoire
│       │       │   │   ├── osm_api_protocol.py, osm_bootstrap.py  Import XML OSM initial, borné et manuel
│       │       │   │   ├── saadiyat_*.json  Références et présentations examinées de Saadiyat
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
│       │       │   │   ├── property_protocol.py, property_import.py  Reçus validés et premières présentations de biens
│       │       │   │   ├── property_presentations.json, property_media.json  Identités examinées et médias autorisés
│       │       │   │   ├── services.py  Import officiel des parcelles et transaction propriétaire
│       │       │   │   ├── orchestration.py  Passerelle d'import, identité durable et résultat atomique
│       │       │   │   ├── media_storage.py  Captures archivées, licences et copies publiques contrôlées
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
│   ├── local/                       Services et stockage nécessaires sur le poste de développement
│   │   ├── compose.yaml              Services API et PostGIS, réseau et volumes locaux
│   │   ├── compose.ingestion.yaml    Profil facultatif : serveur Prefect, métadonnées PostgreSQL et runner
│   │   ├── compose.storage.s3.yaml   Surcharge facultative R2/S3, après les deux fichiers Compose
│   │   └── .env.example              Modèle des réglages R2 et CDN, sans secrets
│   └── storage/                     Exemples de configuration du stockage externe
│       └── r2-public-cors.json        Lectures GET/HEAD depuis un domaine web à configurer
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
│       ├── INGESTION.md               Interface Prefect, activation des horaires et exécution des imports
│       ├── PROPERTY_DATA_PIPELINES.md  Extension prévue des informations commerciales des fiches
│       ├── REEM_MAP.md                Couverture, sources et correspondance avec le HTML
│       ├── VISUAL_DESIGN.md           Thème de l'accueil, crédits photos et animation accessible
│       ├── MAP_PROVIDERS.md           Carte centrale, alentours par quartier et Google Embed facultatif
│       ├── BRANDING.md               Identité technique stable, marque configurable et reprise locale
│       ├── UAE_COVERAGE.md           Couverture des Émirats et activation d'une nouvelle zone
│       ├── TOOLCHAIN.md               Versions exécutables et compatibilités
│       ├── INTERNATIONALIZATION.md    Politique des langues et du RTL
│       ├── DATA_PROVENANCE.md          Collecte directe, sources par information et audit
│       ├── DATABASE_DESIGN.md          Noms du domaine immobilier, audit SQL et trajectoire d'évolution
│       ├── MEDIA_STORAGE.md            Stockage local et R2/S3, fichiers, licences, CDN et sauvegardes
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

Le produit vise les sept émirats, avec Al Reem comme premier jeu de données. `catalog.territories` possède le registre typé de navigation pays → émirat → zone ; ses rectangles approximatifs ne sont pas des frontières cadastrales. `publication.coverage` possède les profils de sources explicitement activés et compose les nombres via `catalog.queries`, sans modifier ses tables. La vue Toute la zone d’Abu Dhabi réunit seulement les profils Reem et Saadiyat : leurs namespaces, références et aperçus restent ceux des acquisitions originales. `member_territory_ids` et `collection_bounds` rendent cette portée explicite dans le contrat ; ajouter une limite officielle en base n’active pas sa carte immobilière. Les collecteurs `evidence` conservent leur vraie portée et leurs clés stables. La direction `publication → evidence → catalog` reste inchangée.

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

Les UUID internes de parcelles et communautés survivent au renouvellement des `OBJECTID` Onwani. `evidence/identity_resolution.py` possède les décisions typées de rapprochement, leur capture et révocation ; les services `catalog` possèdent la mutation de l'objet canonique et `superseded_by`. Les décisions ne suppriment ni captures ni anciennes identités. Les queries propriétaires excluent les objets remplacés des listes et résolvent leurs anciens liens. Un rapprochement requiert une correspondance exacte non ambiguë des identifiants métier/attributs et de la géométrie ; les noms seuls ou distances ne suffisent pas. Les collecteurs ne prennent pas ces décisions.

Lors de l'ajout d'un modèle métier, une migration générée peut créer sa table dans `public`, premier schéma du chemin : prévoir explicitement son placement dans le schéma propriétaire avec des opérations SQL et un état Django cohérent. Le test PostGIS `test_domain_tables_have_unique_names_and_their_owned_schema` contrôle l'emplacement effectif des modèles gérés de `catalog` et `evidence` et l'unicité de leurs noms. Une nouvelle table ou un nouveau domaine doit étendre ces contrôles ; ne pas supposer que `db_table` simple choisit son schéma de création.

`apps/api/src/property_platform/config/settings/base.py` est partagé, puis complété par `apps/api/src/property_platform/config/settings/local.py`, `apps/api/src/property_platform/config/settings/testing.py` ou `apps/api/src/property_platform/config/settings/production.py`. La présence de ce dernier ne signifie pas que le site est déployé. `apps/api/manage.py` sert notamment à lancer les migrations ou à créer un administrateur ; ce n'est pas une page web.

### `apps/ingestion` : programmer, acquérir et suivre les imports

Ce dossier est une application Python exécutable séparément. Il possède les flows Prefect, leur enregistrement, le transport HTTPS, les checkpoints de reçus et l'adaptateur vers Django. Le serveur et son interface permettent de modifier les horaires, lancer les jobs et consulter les états/logs. Le runner exécute un flow à la fois dans le profil local. Les horaires initiaux sont créés inactifs ; un redémarrage conserve les horaires, paramètres et activations déjà modifiés dans l'interface, y compris un horaire supprimé. Le guide [INGESTION.md](INGESTION.md) décrit les commandes et l'UI.

Le registre contient désormais **vingt-six déploiements** : neuf procédures initiales Reem, huit Saadiyat, trois ADREC des îles/indices, puis six nouvelles procédures Abu Dhabi décrites dans [ABU_DHABI.md](ABU_DHABI.md). Les ventes enregistrées ADREC et les observations de quartier sont désormais structurées. Les prix demandés, stocks de logements, avis et génération vidéo restent à implémenter. L’import historique Sentinel, le contrôle de disponibilité et le bootstrap OSM restent manuels ; l’actualisation ADEK refusée reste inactivée.

La direction est **`ingestion → services/protocoles evidence → catalog`**. `collectors/` utilise les constantes et protocoles portables du paquet API, sans ORM, sans copie des modèles et sans collecte d'une URL libre. Les acquisitions ont des budgets par réponse et par lot ; un replay conserve les octets et dates réelles de collecte. `domain.py` initialise Django dans un sous-processus synchrone et transmet les captures préparées à `evidence/orchestration.py`. Cette passerelle possède l'identité durable, les transactions et les liens vers les acquisitions ; les collecteurs ne modifient aucune table directement. Le réseau est utilisé avant la transaction de mutation canonique.

**Le paquet API et ses migrations restent propriétaires des données métier.** `apps/ingestion/pyproject.toml` installe ce paquet depuis `../api` ; le serveur API n'installe ni Prefect ni HTTPX et n'importe pas `property_platform_ingestion`. Le registre métier des URLs et présentations reste dans `apps/api/src/property_platform/modules/evidence/`, tandis que `ingestion/registry.py` décrit seulement les jobs déployés et leurs paramètres. Une nouvelle source doit avoir protocole, identité, tests et propriétaire documentés avant d'être ajoutée à un horaire.

Le profil `infra/local/compose.ingestion.yaml` ajoute un PostgreSQL **distinct pour les métadonnées Prefect**, sur un réseau privé et sans port publié vers Windows. Son volume `prefect-postgres18-data` conserve horaires, déploiements et historique opérationnel ; `ingestion-data` conserve les reçus privés du runner. La base métier `property_platform` conserve catalogue, captures et `evidence.ingestion_execution`. S3 n'est pas installé par ce profil. Les traitements Rasterio restent dans leur environnement isolé ; le runner ne télécharge pas périodiquement les deux scènes historiques et n'intègre aucune dépendance lourde OCR/rendu.

### `packages/contracts` : l'accord entre le site et l'API

Le backend exporte ses routes et formats de réponse dans `packages/contracts/openapi.json`. Le générateur produit ensuite `packages/contracts/src/generated.ts`, utilisé pour vérifier les types côté TypeScript. Ces deux fichiers sont suivis par Git et mis à jour ensemble via les commandes documentées dans [DEVELOPMENT.md](DEVELOPMENT.md) ; ils ne se corrigent pas manuellement.

Ce paquet contient des descriptions de données, pas une copie des modèles Django ni des règles métier. Il pourra aussi être consommé par le futur mobile.

### `packages/branding` : présentation publique indépendante du métier

Ce paquet possède le nom commercial affiché et le chemin du symbole web. L'en-tête, les titres, l'accueil et les signatures PNG le consomment ; le futur mobile pourra réutiliser le nom. Il ne contient ni secret, ni territoire, ni fournisseur, ni identité d'infrastructure. La direction est `web → branding` et, plus tard, `mobile → branding` ; `branding` ne dépend d'aucun autre module. L'adaptateur `apps/web/src/components/brand-mark.tsx` possède le rendu web du symbole, dont le fichier et l'icône d'onglet sont sous `apps/web/public/brand/`.

Les identités techniques restent `property-platform`, `property_platform`, `@property-platform/*` et `PROPERTY_PLATFORM_*` lors d'un changement commercial. Les labels Django `catalog`, `evidence`, `publication`, les schémas SQL et les preuves gardent leur identité. Voir [BRANDING.md](BRANDING.md) pour les fichiers à modifier et la reprise contrôlée d'une installation locale précédente. `scripts/migrate-local-identity.mjs` est un outil de maintenance explicite : il ne s'exécute jamais au démarrage, refuse une cible préexistante et conserve la source pour récupération.

### `infra`, `.github` et `scripts` : lancer et vérifier

`infra/local/compose.yaml` décrit l'environnement local : conteneur API, base PostGIS, réseau et stockage persistant. Il ne contient pas les données de la base : celles-ci résident dans un volume Docker. `infra/local/compose.ingestion.yaml` complète ce fichier avec le profil facultatif `ingestion`, son serveur Prefect, sa base de métadonnées et le runner. Le parcours de développement web garde Next.js séparé ; le profil facultatif `web-preview` permet aussi de lancer son artefact compilé.

Chaque `Dockerfile` décrit comment construire l'image d'une application. `.github/workflows/ci.yml` décrit les vérifications que GitHub exécute ; un workflow de contrôle ne publie pas automatiquement le site. Les fichiers de `scripts` sont des utilitaires du dépôt, pas des fonctionnalités accessibles aux utilisateurs.

### `docs` : comprendre le produit, les décisions et le travail quotidien

`product` explique ce que nous voulons construire, `architecture` pourquoi les composants ont été retenus, `archive` conserve les propositions remplacées et `engineering` explique comment travailler sur le socle réel. L'[index documentaire](../README.md) donne l'ordre de lecture. Les exemples d'une étude ne prouvent pas qu'une fonctionnalité existe déjà.

## Fichiers de configuration à la racine

| Fichier | Quand il intervient | Comment le traiter |
|---|---|---|
| `package.json` | Quand on lance une commande comme `pnpm.cmd dev:web` | Modifier les commandes ou outils communs ici, les dépendances propres au site dans `apps/web/package.json` |
| `pnpm-workspace.yaml` | Quand pnpm identifie les applications et paquets du monorepo | Actualiser lors de l'ajout d'un paquet si son chemin n'est pas déjà couvert |
| `pnpm-lock.yaml`, `apps/api/uv.lock` et `apps/ingestion/uv.lock` | Quand les outils installent les versions résolues | Laisser les gestionnaires les générer et les conserver dans Git ; le lock ingestion résout aussi le paquet API local |
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
| `apps/ingestion/.venv/` | Environnement Python isolé des flows et outils d'ingestion | Non, le code du projet reste dans `apps/ingestion/src/property_platform_ingestion/` |
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
| Ajouter les sources et preuves | `apps/api/src/property_platform/modules/evidence/` | Protocoles métier, registres examinés, modèles d'acquisition et observations existants |
| Ajouter une route métier HTTP | `apps/api/src/property_platform/api/`, branchée au routeur | À créer avec les services métier qu'elle appelle |
| Ajouter des migrations Django | `migrations/` dans le module propriétaire | À générer avec Django lorsque les modèles arrivent |
| Ajouter un domaine prix, avis ou documents | Module dédié sous `apps/api/src/property_platform/modules/` | À créer quand ses responsabilités et dépendances sont définies |
| Ajouter des contrôles de fonctionnalité | Tests proches du module concerné ; tests d'intégration transversaux dans `apps/api/tests/` | À ajouter avec les comportements concernés |
| Ajouter l'application mobile | `apps/mobile/`, consommant la même API | Non créé ; le pilote web vient d'abord |
| Ajouter une collecte ou un horaire | Transport sous `apps/ingestion/src/property_platform_ingestion/collectors/`, flows et registre de déploiements dans cette application | Vingt-six jobs préparés ; transformations et écritures métier restent dans leurs services API |
| Ajouter un traitement lourd OCR/rendu | Runtime spécialisé, séparé du web/API et du runner léger | Non implémenté ; définir son budget, stockage, identité et reprise avec le premier traitement |

Exemple futur : la page du site demande la fiche d'un bâtiment à une route de `api`, qui appelle un service de `catalog` et des lectures explicites de `evidence`. Django interroge PostgreSQL/PostGIS puis renvoie une réponse conforme au contrat. Le composant web l'affiche et utilise les traductions de l'interface. Chaque couche a ainsi un rôle précis ; la logique métier ne se retrouve pas recopiée dans la page.

## Ce qui rend cette organisation modulaire

- Chaque module possède ses mutations et invariants. Les appels externes passent par des services explicites ; aucun module ne modifie les tables d'un autre directement.
- Dépendances autorisées : publication → evidence → catalog, et publication → catalog. Les modules n'importent ni configuration ni HTTP. Import Linter vérifie ces directions en CI ; il ne peut pas détecter tous les accès ORM indirects, qui restent à examiner en revue.
- API, administration et application d'ingestion appellent les services métier propriétaires. Les modèles et migrations ne sont pas dupliqués dans les flows. Les dépendances lourdes OCR/Blender ne sont pas installées dans le serveur web.
- Le backend possède schémas et migrations métier. OpenAPI est exporté, les types TypeScript sont générés et la CI détecte leur divergence.
- Le web ne connaît pas les tables ni les modèles Django. Chaque fonctionnalité future sera regroupée sous `src/features/<fonction>` ; seuls les composants réellement partagés rejoignent une bibliothèque commune.
- Les adaptations de stockage, authentification et fournisseurs seront introduites avec leur première utilisation. Aucun framework abstrait de plugins n'est créé d'avance.

L'application d'ingestion réutilise le paquet Python de l'API dans un processus et une image distincts, avec ses propres dépendances Prefect/HTTPX. Une image spécialisée sera ajoutée avec le premier calcul lourd. Mobile, market, reviews et scenes arrivent lorsqu'une fonctionnalité les justifie ; aucun dossier vide ne simule une application prête.

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

La composition `home.tsx` et le visuel fixe `home-visual.tsx` restent serveur. Le contenu passe à `home-experience.tsx`, composant client d'`atlas` qui gère les apparitions et la parallaxe. Direction : expérience → calcul pur `home-motion.ts` / styles ; visuel → métadonnées `home-scenes.ts` / styles. Le diaporama et ses commandes ont été retirés. Ces modules ne lisent pas l'API, ne modifient pas le catalogue et n'introduisent aucun moteur d'animation partagé. Le contenu est visible sans JavaScript ; les effets s'arrêtent avec la réduction des animations ou l'économie de données. Les photos restent éditoriales, séparées des preuves immobilières ; [VISUAL_DESIGN.md](VISUAL_DESIGN.md) décrit références, droits et réglages.

La typographie partagée appartient à `apps/web/src/theme/` : `theme/fonts.ts` possède les profils de préchargement et exporte le type `FontProfile`. `i18n/locales.ts` associe chaque langue à un profil, avec une dépendance de type uniquement vers `theme` ; le layout serveur transmet ce profil à `getFontPreloads`. Le CSS partagé importe les déclarations de `public/fonts/fonts.css`. Direction : layout → i18n/theme → métadonnées statiques locales. `theme` ne dépend ni d'`i18n` à l'exécution, ni d'`atlas`, ni des contrats, ni de l'API. Les licences et identités des fichiers tiers restent dans `public/fonts/credits.json` ; aucune requête au fournisseur de fonte n'est effectuée pendant la navigation. Les fallbacks systèmes conservent les écritures non couvertes. Voir [l'ajout d'une langue](INTERNATIONALIZATION.md#ajouter-une-langue-sans-disperser-sa-configuration).

`catalog/queries.py` possède les lectures géographiques bornées ; `evidence/queries.py` possède la projection de provenance autorisée ; `publication/preview.py` les assemble sans mutation. L'API `api/parcels.py` valide les entrées et expose un contrat limité. La direction reste publication → evidence/catalog. Les migrations ajoutent les objets cartographiques typés dans leurs schémas propriétaires. Les originaux, opérateurs, attributs bruts et historiques internes ne sont pas exposés.

Dans le web, `features/atlas/map-style.ts` possède le style et l'adaptateur des libellés natifs MapLibre ; les cartes de biens et de districts lui transmettent les messages traduits du namespace `Map`. La direction reste cartes → présentation et types locaux. Les instances sont liées à leur locale, sans liste de langues dans cet adaptateur ni traduction des preuves géographiques.

Les endpoints `/api/v1/preview/parcels` et `/api/v1/preview/parcels/{id}` sont un aperçu de recherche **local**, pas une publication approuvée. Django exige DEBUG et PROPERTY_PLATFORM_PARCEL_PREVIEW ; hors DEBUG ils refusent même un flag activé. Un web compilé exige aussi l'opt-in PROPERTY_PLATFORM_ENABLE_LOCAL_PREVIEW=1. Ce flag ne permet pas de contourner Django. Les droits de diffusion, rôles, authentification du personnel, limitation de trafic distribuée et CSP complète avec nonces restent à définir avant publication.

La carte affiche les usages colorés, secteurs, rues et noms, empreintes 2D, lieux, références et vues satellite ; voir [la couverture et les limites](REEM_MAP.md). Les volumes 3D ne sont pas générés. La liste paginée fournit une alternative si WebGL ne fonctionne pas. La couverture d'une source, la validité de géométrie et l'approbation d'un dossier sont trois notions distinctes.

## Ce que le socle ne prétend pas fournir

Les imports Onwani et cartographiques alimentent le catalogue et conservent captures, observations et audit ; ils peuvent désormais être pilotés par Prefect. Ils ne publient pas automatiquement un dossier. L'accueil et la carte proposent un aperçu local. Auth Supabase, stockage objet, queue de génération et génération IA ne sont pas encore intégrés. L'administration Django est locale à ce stade ; elle ne doit pas être ouverte en production avant le parcours d'accès du personnel et ses règles métier. Les nouveaux modèles n'ont pas d'éditeur Django Admin qui contourne leurs services.

## Présentations immobilières — 12 octobre 2026

Le module `evidence` possède `PropertyPresentation` et `PropertyMedia`, leurs captures et le protocole de revue/import. Direction : import → protocoles / catalogue / modèles evidence ; queries → modèles evidence ; publication → queries ; API → projection et réponses HTTP. Les nouvelles tables restent dans `evidence`, sans nouvelle identité catalogue ni schéma par île. Leur migration est additive. Les registres examinés ne sont pas des données UI : ils alimentent les preuves par un import atomique avec reçus.

`features/atlas/property-card.tsx` possède la présentation des biens sélectionnés à partir du contrat généré ; `Inspector` conserve les informations secondaires. Les résumés, liens de promoteurs et photos ne viennent pas de constantes du composant. Les médias passent par une route fixe de l’API avec les mêmes restrictions locales et un budget de taille ; aucun service de rendu/OCR ni dépendance lourde n’est ajouté. Les imports ne fusionnent pas des objets par nom ou proximité. Voir [PROPERTY_EXPLORATION.md](PROPERTY_EXPLORATION.md).

`features/atlas/presentation.ts` possède aussi le choix du titre visible, l'index de candidats par parcelle et la référence cadastrale lisible. Direction : Explorer/Inspector/PropertyCard → présentation pure → types des contrats. Le choix ne filtre pas un nom selon sa fiabilité ; il signale l'association possible et préserve les identités, alternatives et codes sources. Cet index ne crée aucune relation acceptée en base.

### Extension Saadiyat : responsabilités

Le module evidence possède collection_profiles.py (configuration immuable examinée), osm_api_protocol.py (parseur XML portable sans ORM) et osm_bootstrap.py (captures et orchestration de la matérialisation initiale). La direction reste ingestion → evidence → catalog ; publication assemble les lectures filtrées par territoire. Le helper map_import.materialize_map_records conserve une unique transaction propriétaire et un audit commun aux formats Overpass et XML. Aucun collecteur ne modifie les modèles directement. Le découpage OSM API initial est manuel ; il ne devient pas un collecteur national récurrent. Voir [SAADIYAT.md](SAADIYAT.md).


## Observations de marché ADREC

Les données source ADREC appartiennent au module `evidence` : [ADREC.md](ADREC.md) décrit les modèles typés, captures et règles de snapshots. Le collecteur `apps/ingestion/src/property_platform_ingestion/collectors/adrec.py` acquiert uniquement les endpoints examinés ; `evidence/adrec.py` valide leur protocole et `evidence/adrec_import.py` matérialise les observations via la passerelle durable existante. Les trois tables `adrec_market_snapshot`, `adrec_sale_observation`, `adrec_index_observation` sont dans le schéma `evidence`, avec noms non qualifiés uniques et migration explicite depuis `public`.

La lecture appartient à `publication/adrec_preview.py`, puis à l’adaptateur HTTP et au composant web `features/atlas/adrec-market.tsx`. La dépendance reste `publication → evidence → catalog` ; Prefect ne possède pas les écritures métier. Il n’existe pas de module commercial `market` normalisé supplémentaire ni de rapprochement par nom seul. Les positions de lignes et hashes sont des identités d’observation, jamais des identifiants de transaction. Les séries ambiguës sont conservées mais écartées de la publication.


## Extension du contexte Abu Dhabi — 14 octobre 2026

Le guide [ABU_DHABI.md](ABU_DHABI.md) documente les six nouveaux déploiements et leurs limites. `evidence/abu_dhabi.py` possède les URLs/protocoles publics DoH, ADEK Charter, Mobility, SCAD et Onwani districts ; `context_import.py` possède leurs snapshots et mutations. `models.py` conserve un header d’audit et cinq tables d’observations typées dans le schéma evidence. Aucun objet n’est fusionné avec un bâtiment sur son nom ou sa proximité. Les 216 limites de districts ne prétendent pas ajouter toutes leurs parcelles.

`ingestion/collectors/context.py` acquiert puis rejoue les réponses avant la transaction. Le flow public_context et registry.py possèdent planification et paramètres fermés ; domain.py reste la passerelle synchrone. L’archive ADEK refusée en acquisition automatique passe par un reçu privé explicitement fourni, avec horodatage de fichier indiqué comme approximatif. Son calendrier reste inactif. Le script scripts/prepare_context_archive.py prépare ce reçu sans collecter ni écrire en base.

`publication/context_preview.py` possède les lectures bornées ; `api/public_context.py` leur livraison locale ; le web features/atlas/public-context.tsx leur rendu et pagination. `district-overview.tsx` et `district-map.tsx` consomment la projection typée `/district-map` des mêmes observations Onwani : annuaire et limites, simplification métrique dérivée sans mutation de la preuve originale. Les liens de navigation vers un territoire collecté utilisent les identifiants officiels municipality/DISTRICTID des profils examinés, jamais le nom seul. La vue générale Abu Dhabi est le défaut de navigation ; la configuration de collecte reste explicitement propre à chaque île. Les namespaces Context et Coverage des dictionnaires conservent l’interface multilingue et le RTL. La direction reste **publication → evidence → catalog**, avec ingestion → evidence ; aucun nouveau module métier ou microservice. Les contrats OpenAPI/types sont générés, pas corrigés manuellement.

La portée ADREC abu-dhabi utilise le même protocole et tables que les îles. Ses 90 jours complets restent vérifiés par partitions ; le plafond devient 50 000 observations et la pagination HTTP s’aligne. Les snapshots géographiques se recouvrent et ne doivent pas être additionnés.

### Projection des usages immobiliers

`publication/uses.py` possède la taxonomie dérivée et versionnée des usages (`use_types`, `source-use-v1`). Le module evidence fournit les tags de source autorisés ; le catalogue conserve les valeurs originales. API et web consomment ces types sans les stocker comme un second modèle métier ni importer une source au clic. Les dictionnaires Use traduisent les types d’interface ; les originaux Onwani/OSM gardent leur texte. Le [guide des fiches](PROPERTY_EXPLORATION.md#usages-visibles-et-données-déjà-ingérées--14-octobre-2026) donne les tables et les limites.

## Lieux complémentaires — 17 octobre 2026

`evidence/overture_protocol.py` possède la version examinée, les portées et la classification pure ; `evidence/overture_places.py` possède les captures et la matérialisation des lieux. `apps/ingestion/src/property_platform_ingestion/collectors/overture.py` acquiert les seuls fragments Parquet intersectant les deux profils via l’index STAC officiel. PyArrow appartient exclusivement au runtime ingestion ; ni le web ni l’API ne le chargent. Le flow `property-platform-map` réutilise la passerelle auditée, sans nouveau domaine ni migration. `publication/place_display.py` masque seulement les doublons d’affichage intersources à nom/type identiques et à moins de 15 m ; aucune identité ni observation n’est fusionnée. Les lectures carte et proximité restent bornées. `atlas/imagery-sources.ts` centralise les fonds raster examinés ; les données propres restent indépendantes. Voir [OVERTURE_PLACES.md](OVERTURE_PLACES.md).


**Affinage Explore — 19 octobre 2026.** `app/[locale]/market/page.tsx` possède la page Marché et ses filtres de territoire ; elle compose la lecture ADREC existante, avec `atlas/market-page.module.css` pour sa mise en page. Le lien d’en-tête ouvre cette page et les anciennes URL Explore `tab=market` y redirigent dans leur langue. Les vues contexte/sources restent disponibles dans Explore par URL. `components/map-locate-button.tsx` possède l’action de localisation commune. `atlas/presentation.ts` calcule aussi des suggestions d’affichage par proximité, sans mutation de données : point projet nommé à 50 m maximum de l’emprise d’une parcelle résidentielle/mixte sans identité nommée, exclusion des égalités ambiguës à moins de 10 m. Le calcul local WGS84 approximatif respecte trous et multipolygones ; méthode `boundary-proximity-v1`, distance et source sont conservées dans la suggestion et signalées dans les détails. Il ne remplace ni lien cadastral ni localisation qualifiée. `atlas/project-pulse.ts` possède la progression pure des halos ; `parcel-map.tsx` possède leur cycle interrompu en arrière-plan, selon la préférence de mouvement réduit et le réglage utilisateur. Direction : présentation cartographique → contrats existants ; aucun domaine métier, migration, pipeline ou abonnement supplémentaire.

`atlas/map-view-control.tsx` et son module CSS possèdent le menu Vue (plan/satellite, source et dates), fermé avec Échap ou un clic extérieur et exclusif des autres réglages. Il dépend des options de carte et des scènes déjà lues, sans collecte ni abonnement. `explorer.tsx` mesure la hauteur de la fiche pour déplacer les commandes au-dessus sur téléphone ; Vue reste à gauche et la légende à droite dans toutes les langues. Direction : route → composant de présentation → relais API existant.

`parcel-map.tsx` mesure aussi le rail des contrôles/crédits MapLibre via ResizeObserver et expose sa hauteur au conteneur de présentation ; les commandes Vue et légende réservent cet espace sur toutes les largeurs. L’observation est nettoyée avec le contrôle natif, sans modifier les données ou les sources.


**Hydrographie de présentation — 19 octobre 2026.** `features/atlas/hydrography.ts` possède la source vectorielle publique OpenFreeMap et les couches d’eau, partagées par `parcel-map.tsx` et `projects/neighbourhood-map.tsx` via les styles purs. Direction : carte → configuration de présentation → tuiles externes. Aucun accès aux modules de domaine, mutation SQL ou rapprochement d’identité. `imagery-sources.ts` possède le registre des fonds mondiaux et leur visibilité exclusive, sans mélange de fournisseurs. Voir [MAP_PROVIDERS.md](MAP_PROVIDERS.md).


**Relais satellite public — 19 octobre 2026.** `app/api/atlas/satellite/[provider]/[z]/[x]/[y]/route.ts` possède le relais borné de PNG WorldCover vers un hôte WMTS HTTPS fixe. Direction : route web → service raster public, sans import des domaines, calcul raster ou donnée SQL. Le registre d’`atlas/imagery-sources.ts` et les messages possèdent la présentation des années ; les anciens reçus Sentinel restent sous `evidence`. Voir [SATELLITE_IMAGERY.md](SATELLITE_IMAGERY.md) pour les conditions, refus observés, niveaux et contrôles. Aucun nouveau module de domaine, microservice ou migration.
