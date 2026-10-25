# Versions des outils — vérification du 10 octobre 2026

**Analyses cartographiques — 20 octobre 2026.** Ajouts web verrouillés : SunCalc **2.1.1**, modules Turf `area`, `length`, `boolean-point-in-polygon`, `convex`, `destination` **7.4.0**, et types GeoJSON **7946.0.16**. SunCalc 2 utilise des degrés depuis le nord, pas les radians de ses anciennes API. Aucun changement de compilateur ou de peer TypeScript Next.js/OpenAPI. Le moteur natif facultatif utilise `ghcr.io/valhalla/valhalla-scripted@sha256:eaad372b8ef31e3e4592c442875aeb1375fbf5aeaa0d259b469e3b46583ab10d`, version observée **3.9.1-618cad5eb**, dans son propre conteneur ; il n'entre pas dans les runtimes web/API/Python. Manifeste, lockfile, Docker de routage et contrôle Compose CI sont alignés. Voir [MAP_ANALYSIS.md](MAP_ANALYSIS.md).

La demande de mise à jour porte sur les dernières versions stables des outils du dépôt. Les versions directes sont fixées et les dépendances transitives verrouillées ; une nouvelle version publiée demain ne modifie pas automatiquement le projet. Les préversions, branches master et versions sans compatibilité requise ne sont pas assimilées à une mise à jour fonctionnelle.

## Versions exécutées ou configurées

**Ajout facultatif du 16 octobre :** Tailscale **1.104.1**, image officielle `tailscale/tailscale:v1.104.1` fixée par digest dans `infra/local/compose.remote-preview.yaml`, fournit la prévisualisation privée sur téléphone. Sa version a été vérifiée dans la distribution officielle et l'image téléchargée. Il n'est ajouté à aucun runtime web/API/ingestion. Voir [REMOTE_PREVIEW.md](REMOTE_PREVIEW.md) et les [paramètres Docker officiels](https://tailscale.com/docs/features/containers/docker/docker-params).

| Outil | Version | Emplacement / rôle |
|---|---|---|
| Node.js | 26.11.1 | .node-version, CI, images web ; engines >=26.11.1 <27 |
| pnpm | 12.10.1 | packageManager, image de build et instructions |
| npm | 12.2.0 | Installation des outils et image de build web ; pnpm gère les dépendances du projet |
| TypeScript | 7.0.2 | Compilateur natif de typecheck web et contrats, alias @typescript/compiler |
| Paquet de compatibilité TypeScript pour Next.js | 6.0.2 | Alias typescript → @typescript/typescript6 ; l'API embarquée annonce 6.0.3 |
| API TypeScript pour openapi-typescript | 5.9.3 | Peer ^5.x du générateur, isolé dans packages/contracts |
| @types/node | 26.6.5 | Types du runtime web |
| Next.js | 16.4.0 | Déjà dernière version stable vérifiée |
| next-intl | 4.14.9 | Déjà dernière version stable vérifiée |
| React / React DOM / leurs types | 19.3.0 | Déjà dernières versions stables vérifiées |
| Biome | 2.5.15 | Déjà dernière version stable vérifiée |
| Playwright (`@playwright/test`, image `mcr.microsoft.com/playwright:v1.64.0-noble` par digest) | 1.64.0 | Parcours navigateur `checks-e2e` uniquement, jamais dans le runtime web ; version stable de plus de deux semaines au 23 octobre 2026 (1.64.1 plus récente non retenue). Le paquet npm et l'image doivent rester à la même version. Voir [E2E.md](E2E.md) |
| openapi-typescript | 7.13.0 | Déjà dernière version stable vérifiée |
| Python | 3.14.8 | Version compatible Django la plus récente ; .python-version, CI et image API |
| uv | 0.13.0 | Déjà dernière version stable vérifiée |
| Django | 6.1.2 | Mise à jour du framework, désormais hors branche 5.2 LTS |
| Django Ninja | 1.7.1 | Dernière version stable vérifiée |
| dj-database-url | 3.1.2 | Dernière version stable vérifiée |
| psycopg / psycopg-binary | 3.3.6 | Dernière version stable vérifiée |
| Gunicorn | 26.2.0 | Mise à jour du serveur WSGI |
| Prefect | 3.8.8 | Orchestration, serveur/UI et runner ; uniquement dans `apps/ingestion` |
| SQLAlchemy | 2.0.55 | Compatibilité du planificateur Prefect 3.8.8 ; uniquement dans `apps/ingestion` |
| HTTPX | 0.28.1 | Transport HTTPS borné des collecteurs ; uniquement dans `apps/ingestion` |
| boto3 / botocore | 1.43.114 / 1.43.114 | SDK S3/R2, ajouté le 15 octobre ; API et ingestion, aucune dépendance web |
| pytest / pytest-django | 9.1.1 / 4.14.0 | Dernières versions stables vérifiées |
| Ruff / Import Linter | 0.17.0 / 2.15 | Dernières versions stables vérifiées |
| Hatchling | 1.32.4 | Backend de construction Python fixé |
| PostgreSQL / PostGIS | Tag 18-3.6 | Dernier couple stable fourni par l'image PostGIS ; versions mineures du tag évolutives |
| Client PostgreSQL de l'ingestion | postgresql-client-18 (dépôt PGDG `trixie-pgdg`, clé vérifiée par empreinte) | `pg_dump`/`pg_restore` de même version majeure que le serveur, pour les [sauvegardes](BACKUPS.md) |
| PostgreSQL des métadonnées Prefect | Image 18.6-trixie | Base distincte `prefect`, sans PostGIS ni port publié vers l'hôte |
| Base des images applicatives | Debian Trixie | Node 26.11.1-trixie-slim / Python 3.14.8-slim-trixie |
| GitHub checkout / setup-node | 7.0.1 / 7.1.0 | Releases stables vérifiées |
| pnpm action-setup / setup-uv | 6.1.0 / 10.3.0 | Releases stables vérifiées via l'API GitHub |

Les versions npm proviennent du dist-tag latest du registre officiel ; les versions Python des métadonnées PyPI. Les lockfiles ont été régénérés avec pnpm 12 et uv, sans assouplir le contrôle des peers. L'exception d'âge de publication ajoutée par pnpm concerne uniquement @types/node@26.6.5, pas toutes les futures dépendances.

## Compatibilités qui empêchent un remplacement aveugle

**Planificateur Prefect — correction du 20 octobre 2026.** SQLAlchemy 2.1.4, précédemment résolu transitivement, faisait échouer `schedule_deployments` lors des insertions ORM groupées (`Can't evaluate bulk DML statement; please supply a bulk_dml decorated function`). Les lancements manuels fonctionnaient malgré cet échec des calendriers. L’API des [hybrides SQLAlchemy 2.1](https://docs.sqlalchemy.org/en/21/orm/extensions/hybrid.html) explique le nouveau hook de DML. L’ingestion fixe désormais [SQLAlchemy 2.0.55](https://pypi.org/project/SQLAlchemy/2.0.55/), dernière maintenance 2.0 vérifiée, compatible avec la contrainte Prefect. Le manifeste et le lockfile sont alignés ; serveur et runner utilisent la même image. La CI conserve `uv lock --check`, le build gelé et les tests ingestion. Une mise à jour 2.1 exige de vérifier une création automatique de runs planifiés sur PostgreSQL, en plus des lancements manuels. Aucune migration de schéma Prefect ou de base métier n’est requise par cette correction.

**Python 3.15.0 vient d'être publié, mais Django 6.1 documente uniquement Python 3.12 à 3.14.** L'image Python officielle vérifiée publie aussi 3.14.8 comme version stable et 3.15 sous tags rc. Nous utilisons donc 3.14.8, et ne déclarons pas 3.15 validé. Une prochaine mise à jour pourra le tester lorsque framework, wheels et image stable seront disponibles ensemble.

**TypeScript 7 n'expose plus l'ancienne API du compilateur.** Next.js en utilise encore une, et openapi-typescript 7.13.0 annonce un peer TypeScript ^5.x. Le typage du code utilise bien 7.0.2, avec des commandes explicites ; l'API 6 est fournie via le paquet de compatibilité officiel pour Next (version du paquet 6.0.2, API embarquée 6.0.3 constatée), et l'API 5 reste locale au générateur. Aucun peer n'est forcé ou ignoré pour masquer ce décalage. Supprimer ces dépendances de compatibilité demande une évolution des outils qui les consomment.

**PostgreSQL 19 est encore en bêta dans les sources vérifiées.** Le tag stable PostGIS retenu est 18-3.6 ; aucun tag master/beta n'est utilisé. Les bibliothèques GDAL/GEOS/PROJ de l'image API proviennent des paquets de Debian stable, pas de compilations arbitraires des derniers commits. Trixie requiert les noms libgdal36, libgeos-c1t64 et libproj25.

Le dépôt ne gère pas les installations système de Git, Docker Desktop ni l'éditeur. Les guides pointent vers leurs distributions officielles ; cette mise à jour ne les installe ou remplace pas sur la machine. Node 26 est la branche Current, pas encore le choix LTS 24 de l'ancien socle.

## Ajout cartographique — 11 octobre 2026

**MapLibre GL JS 6.14.0**, version stable du registre npm vérifiée lors de l'installation, est fixé dans `apps/web/package.json` et le lockfile. Il est chargé dans le seul module d'exploration ; les versions des compilateurs existants restent inchangées. Son ajout explicite a produit une exception de délai de publication pour cette version dans `pnpm-workspace.yaml` ; aucune désactivation générale des contrôles de dépendances ou de TLS n'a été faite. Le plan utilise les géométries de la base ; le fond satellite optionnel utilise Esri ou les aperçus Sentinel conservés. La diffusion publique et les droits des fournisseurs restent une décision séparée. [Documentation MapLibre](https://maplibre.org/maplibre-gl-js/docs/).

## PostgreSQL : données existantes

Le passage de 17 à 18 est une migration majeure, pas une simple mise à jour de fichiers. Le Compose crée un volume postgres18-data monté sous /var/lib/postgresql. L'ancien volume postgres-data n'est ni supprimé ni réutilisé directement. Les données existantes demandent un export/restauration ou pg_upgrade validé séparément. Voir [le lancement détaillé](DEVELOPMENT.md).

## Orchestration isolée — 13 octobre 2026

**Prefect 3.8.8 et HTTPX 0.28.1** sont les dernières versions stables vérifiées dans les métadonnées officielles PyPI pour cet ajout. Elles sont fixées dans [apps/ingestion/pyproject.toml](../../apps/ingestion/pyproject.toml) et résolues avec leurs dépendances dans [apps/ingestion/uv.lock](../../apps/ingestion/uv.lock). Prefect annonce Python `>=3.10,<3.15`, dont Python 3.14 ; le runtime reste **Python 3.14.8** pour respecter aussi la compatibilité Django. Cet ajout ne remplace pas les compilateurs et leurs dépendances de compatibilité web. Sources : [Prefect 3.8.8](https://pypi.org/project/prefect/3.8.8/), [HTTPX 0.28.1](https://pypi.org/project/httpx/0.28.1/).

L'image [apps/ingestion/Dockerfile](../../apps/ingestion/Dockerfile) utilise `python:3.14.8-slim-trixie` et `ghcr.io/astral-sh/uv:0.13.0`. Elle installe le paquet API local comme dépendance, ainsi que les bibliothèques système GDAL/GEOS/PROJ nécessaires à ses services géographiques. Prefect et HTTPX ne sont pas ajoutés au runtime web/API. Rasterio, OCR et rendu 3D restent hors de cette image.

Le profil [infra/local/compose.ingestion.yaml](../../infra/local/compose.ingestion.yaml) utilise cette image pour le serveur Prefect et le runner, ainsi que `postgres:18.6-trixie` pour leurs métadonnées séparées. La base métier garde son image PostGIS et son volume existant. L'accès UI local est [localhost:4200](http://localhost:4200) ; aucune instance Prefect Cloud ni ressource S3 n'est créée. Le guide [INGESTION.md](INGESTION.md) distingue enregistrement des jobs, activation d'un horaire et véritable exécution d'un import.

Les contrôles ingestion vérifient le lock, Ruff, les tests de transport sans réseau, les checkpoints et la conservation des horaires modifiés dans l'UI ; la CI construit aussi son image et liste les déploiements sans réseau. Les tests de passerelle et de mutation métier nécessitent PostGIS réel dans la suite API. Un build réussi ne prouve pas qu'une source distante est disponible ni qu'un import a été exécuté. La vérification TLS reste active ; un certificat supplémentaire doit être identifié et approuvé avant de configurer le secret de build facultatif. [Documentation du serveur Prefect dans Docker](https://docs.prefect.io/v3/how-to-guides/self-hosted/server-docker).

### Autorité HTTPS supplémentaire dans Docker

Les trois Dockerfiles web, API et ingestion acceptent le même secret BuildKit **`platform_extra_ca`**, facultatif. Il contient uniquement un certificat **public** d'autorité déjà approuvé par l'opérateur. Le build l'ajoute au magasin Debian avec `update-ca-certificates` ; sans ce secret, le magasin standard reste utilisé. La clé privée n'est jamais fournie et le certificat local n'est pas versionné dans Git.

Sur le poste Karim, les connexions Windows vers PyPI, pythonhosted et le registre npm ont une chaîne vérifiée vers l'autorité d'inspection HTTPS Avast déjà présente dans les magasins approuvés. Le fichier ignoré `C:\Users\Karim\Repositories\property-platform\.cache\validation\ingestion-trusted-ca.crt` contient seulement ce certificat public ; voir [le parcours de build dans INGESTION.md](INGESTION.md). Une nouvelle autorité ou un renouvellement exige une nouvelle vérification, pas la réutilisation aveugle d'un certificat trouvé dans une erreur. Le cache BuildKit ne dépend pas du contenu du secret : après remplacement du certificat, invalider la couche correspondante ou reconstruire sans cache.

Le web utilise **`NODE_USE_SYSTEM_CA=1`** et **`SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt`** pour Node 26 et le client embarqué de pnpm 12. Python/uv utilise **`UV_SYSTEM_CERTS=true`** ; les collecteurs HTTPS utilisent un contexte SSL système avec validation du certificat et du nom d'hôte. Les contrôles d'intégrité, de provenance des paquets et de délai de publication de pnpm restent actifs. Aucun `strict-ssl=false`, `NODE_TLS_REJECT_UNAUTHORIZED=0` ni mode HTTP non vérifié n'est utilisé. Cette adaptation ne modifie ni les versions verrouillées, ni les permissions des fichiers ou propriétaires de caches SWC. [Certificats système Node.js](https://nodejs.org/api/cli.html#node_use_system_ca1), [certificats TLS uv](https://docs.astral.sh/uv/concepts/authentication/certificates/).

## Vérifications et limites

Les contrôles locaux doivent couvrir installation verrouillée, qualité, TypeScript 7, traductions, contrats OpenAPI, build standalone et HTTP sur toutes les langues du registre. Python est vérifié avec Ruff, Import Linter, tests HTTP et export OpenAPI. Les tests SQLite ne valident pas PostGIS ; Docker et l'intégration PostGIS sont exécutés par la CI et leur résultat doit être observé. Les tags d'images restent versionnés mais sans digest immuable ; les paquets système Debian ne sont pas figés par un snapshot.

## Sources primaires

- [Node.js](https://nodejs.org/en/download), [registre npm](https://registry.npmjs.org/), [PyPI](https://pypi.org/).
- [TypeScript 7 et compatibilité avec l'API précédente](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/).
- [Versions Python](https://www.python.org/downloads/), [compatibilité Python/Django](https://docs.djangoproject.com/en/6.1/faq/install/), [Django stable](https://www.djangoproject.com/download/).
- [PostgreSQL](https://www.postgresql.org/support/versioning/), [image officielle PostGIS et volumes](https://github.com/postgis/docker-postgis).
- [Images Node officielles](https://github.com/docker-library/official-images/blob/master/library/node), [images Python officielles](https://github.com/docker-library/official-images/blob/master/library/python).
- [checkout](https://github.com/actions/checkout/releases), [setup-node](https://github.com/actions/setup-node/releases), [pnpm action-setup](https://github.com/pnpm/action-setup/releases), [setup-uv](https://github.com/astral-sh/setup-uv/releases).

## Outil satellite isolé — 11 octobre 2026

Rasterio 1.5.2 est utilisé uniquement par `scripts/acquire_reem_imagery.py`, dans un environnement local distinct. Ses dépendances sont fixées dans `scripts/imagery-requirements.txt` ; aucune modification des dépendances API/web, des compilateurs ou des images de service. Le transport lit des plages HTTPS vérifiées et borne les octets, le script ne télécharge pas le raster entier. [Version Rasterio sur PyPI](https://pypi.org/project/rasterio/1.5.2/). MapLibre 6 gère le texte RTL et les polices locales sans plugin distant : [API RTL](https://maplibre.org/maplibre-gl-js/docs/API/functions/setRTLTextPlugin/), [polices locales](https://maplibre.org/maplibre-gl-js/docs/examples/style-labels-with-local-fonts/).

## Lecture Parquet des lieux — 17 octobre 2026

[PyArrow 26.0.0](https://pypi.org/project/pyarrow/26.0.0/) est fixé uniquement dans `apps/ingestion/pyproject.toml` et `apps/ingestion/uv.lock`. Ses wheels CPython 3.14/Linux ont été vérifiées. Il lit les fragments régionaux Overture en flux, sans GeoPandas, DuckDB ni extension téléchargée au lancement. Les versions et dépendances de compatibilité web/API restent inchangées. L’image ingestion existante est réutilisée ; aucun nouveau conteneur permanent ou abonnement n’est ajouté.

## Indice d'activité satellite — 25 octobre 2026

[NumPy 2.5.4](https://pypi.org/project/numpy/2.5.4/) est fixé dans `apps/ingestion/pyproject.toml` et `apps/ingestion/uv.lock` pour l'arithmétique raster de B06 (`collectors/sentinel_activity.py`). C'est la version déjà retenue par `scripts/imagery-requirements.txt` ; wheel CPython 3.14 manylinux. Aucune dépendance API/web, aucun nouveau service. La lecture des fenêtres COG (Rasterio, déjà fixé à 1.5.2 pour l'outil isolé) sera ajoutée à l'ingestion dans la même tâche. Méthode : [CONSTRUCTION_ACTIVITY.md](CONSTRUCTION_ACTIVITY.md).
