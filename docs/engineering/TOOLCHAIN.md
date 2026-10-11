# Versions des outils — vérification du 10 octobre 2026

La demande de mise à jour porte sur les dernières versions stables des outils du dépôt. Les versions directes sont fixées et les dépendances transitives verrouillées ; une nouvelle version publiée demain ne modifie pas automatiquement le projet. Les préversions, branches master et versions sans compatibilité requise ne sont pas assimilées à une mise à jour fonctionnelle.

## Versions exécutées ou configurées

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
| openapi-typescript | 7.13.0 | Déjà dernière version stable vérifiée |
| Python | 3.14.8 | Version compatible Django la plus récente ; .python-version, CI et image API |
| uv | 0.13.0 | Déjà dernière version stable vérifiée |
| Django | 6.1.2 | Mise à jour du framework, désormais hors branche 5.2 LTS |
| Django Ninja | 1.7.1 | Dernière version stable vérifiée |
| dj-database-url | 3.1.2 | Dernière version stable vérifiée |
| psycopg / psycopg-binary | 3.3.6 | Dernière version stable vérifiée |
| Gunicorn | 26.2.0 | Mise à jour du serveur WSGI |
| pytest / pytest-django | 9.1.1 / 4.14.0 | Dernières versions stables vérifiées |
| Ruff / Import Linter | 0.17.0 / 2.15 | Dernières versions stables vérifiées |
| Hatchling | 1.32.4 | Backend de construction Python fixé |
| PostgreSQL / PostGIS | Tag 18-3.6 | Dernier couple stable fourni par l'image PostGIS ; versions mineures du tag évolutives |
| Base des images applicatives | Debian Trixie | Node 26.11.1-trixie-slim / Python 3.14.8-slim-trixie |
| GitHub checkout / setup-node | 7.0.1 / 7.1.0 | Releases stables vérifiées |
| pnpm action-setup / setup-uv | 6.1.0 / 10.3.0 | Releases stables vérifiées via l'API GitHub |

Les versions npm proviennent du dist-tag latest du registre officiel ; les versions Python des métadonnées PyPI. Les lockfiles ont été régénérés avec pnpm 12 et uv, sans assouplir le contrôle des peers. L'exception d'âge de publication ajoutée par pnpm concerne uniquement @types/node@26.6.5, pas toutes les futures dépendances.

## Compatibilités qui empêchent un remplacement aveugle

**Python 3.15.0 vient d'être publié, mais Django 6.1 documente uniquement Python 3.12 à 3.14.** L'image Python officielle vérifiée publie aussi 3.14.8 comme version stable et 3.15 sous tags rc. Nous utilisons donc 3.14.8, et ne déclarons pas 3.15 validé. Une prochaine mise à jour pourra le tester lorsque framework, wheels et image stable seront disponibles ensemble.

**TypeScript 7 n'expose plus l'ancienne API du compilateur.** Next.js en utilise encore une, et openapi-typescript 7.13.0 annonce un peer TypeScript ^5.x. Le typage du code utilise bien 7.0.2, avec des commandes explicites ; l'API 6 est fournie via le paquet de compatibilité officiel pour Next (version du paquet 6.0.2, API embarquée 6.0.3 constatée), et l'API 5 reste locale au générateur. Aucun peer n'est forcé ou ignoré pour masquer ce décalage. Supprimer ces dépendances de compatibilité demande une évolution des outils qui les consomment.

**PostgreSQL 19 est encore en bêta dans les sources vérifiées.** Le tag stable PostGIS retenu est 18-3.6 ; aucun tag master/beta n'est utilisé. Les bibliothèques GDAL/GEOS/PROJ de l'image API proviennent des paquets de Debian stable, pas de compilations arbitraires des derniers commits. Trixie requiert les noms libgdal36, libgeos-c1t64 et libproj25.

Le dépôt ne gère pas les installations système de Git, Docker Desktop ni l'éditeur. Les guides pointent vers leurs distributions officielles ; cette mise à jour ne les installe ou remplace pas sur la machine. Node 26 est la branche Current, pas encore le choix LTS 24 de l'ancien socle.

## Ajout cartographique — 11 octobre 2026

**MapLibre GL JS 6.14.0**, version stable du registre npm vérifiée lors de l'installation, est fixé dans `apps/web/package.json` et le lockfile. Il est chargé dans le seul module d'exploration ; les versions des compilateurs existants restent inchangées. Son ajout explicite a produit une exception de délai de publication pour cette version dans `pnpm-workspace.yaml` ; aucune désactivation générale des contrôles de dépendances ou de TLS n'a été faite. Le moteur fonctionne ici sans tuiles externes ; les droits et coûts d'un fournisseur de fond de carte seront une décision séparée. [Documentation MapLibre](https://maplibre.org/maplibre-gl-js/docs/).

## PostgreSQL : données existantes

Le passage de 17 à 18 est une migration majeure, pas une simple mise à jour de fichiers. Le Compose crée un volume postgres18-data monté sous /var/lib/postgresql. L'ancien volume postgres-data n'est ni supprimé ni réutilisé directement. Les données existantes demandent un export/restauration ou pg_upgrade validé séparément. Voir [le lancement détaillé](DEVELOPMENT.md).

## Vérifications et limites

Les contrôles locaux doivent couvrir installation verrouillée, qualité, TypeScript 7, traductions, contrats OpenAPI, build standalone et HTTP sur quinze langues. Python est vérifié avec Ruff, Import Linter, tests HTTP et export OpenAPI. Les tests SQLite ne valident pas PostGIS ; Docker et l'intégration PostGIS sont exécutés par la CI et leur résultat doit être observé. Les tags d'images restent versionnés mais sans digest immuable ; les paquets système Debian ne sont pas figés par un snapshot.

## Sources primaires

- [Node.js](https://nodejs.org/en/download), [registre npm](https://registry.npmjs.org/), [PyPI](https://pypi.org/).
- [TypeScript 7 et compatibilité avec l'API précédente](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/).
- [Versions Python](https://www.python.org/downloads/), [compatibilité Python/Django](https://docs.djangoproject.com/en/6.1/faq/install/), [Django stable](https://www.djangoproject.com/download/).
- [PostgreSQL](https://www.postgresql.org/support/versioning/), [image officielle PostGIS et volumes](https://github.com/postgis/docker-postgis).
- [Images Node officielles](https://github.com/docker-library/official-images/blob/master/library/node), [images Python officielles](https://github.com/docker-library/official-images/blob/master/library/python).
- [checkout](https://github.com/actions/checkout/releases), [setup-node](https://github.com/actions/setup-node/releases), [pnpm action-setup](https://github.com/pnpm/action-setup/releases), [setup-uv](https://github.com/astral-sh/setup-uv/releases).
