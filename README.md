# property-platform

Liwa Atlas : plateforme immobilière cartographique évolutive, avec dossiers sourcés, plans, comparaison et suivi des changements. Première zone envisagée : Al Reem Island.

## Documents de cadrage

- [Étude produit](docs/product/ETUDE_PRODUIT_LIWA_ATLAS.md)
- [Approfondissement stratégique](docs/product/STRATEGIE_PRODUIT_LIWA_ATLAS.md)
- [Architecture actuelle — revue critique V2](docs/architecture/REVUE_ARCHITECTURE_LIWA_ATLAS_V2.md)
- [Contre-audit : décision maintenue et conditions de validation](docs/architecture/AUDIT_DECISION_STACK_LIWA_ATLAS.md)
- [Proposition de stack précédente — historique](docs/archive/ARCHITECTURE_STACK_LIWA_ATLAS.md)

Le dépôt contient Next.js/TypeScript, Django/Django Ninja, contrats OpenAPI générés et PostgreSQL/PostGIS. L'atlas local affiche les parcelles colorées, secteurs, rues, empreintes de bâtiments, lieux, références de projets et vues satellite, avec recherches, filtres et provenance. Les imports manuels conservent captures, observations et audit ; voir [les commandes expliquées](docs/engineering/DEVELOPMENT.md#couches-reem) et [la couverture réelle comparée au HTML](docs/engineering/REEM_MAP.md). Logements, prix structurés, dossiers publics approuvés, authentification, stockage objet et orchestration automatique restent à développer. Aucun déploiement public n'est effectué.

## Structure et démarrage

- `apps/web` : interface Next.js.
- `apps/api` : cœur Django/GeoDjango et modules catalogue, preuves, publication.
- `packages/contracts` : schéma API et types TypeScript générés.
- `infra/local` : environnement Docker Compose avec PostGIS.
- `.github/workflows` : qualité, compilation, frontières de modules et intégration PostGIS.

Lire [les règles de structure](docs/engineering/REPOSITORY.md) et [le guide de développement](docs/engineering/DEVELOPMENT.md). Les dépendances JavaScript et Python sont verrouillées ; les directions entre modules et la cohérence des contrats sont vérifiées automatiquement.

L'interface utilise l'anglais par défaut, des routes par langue et des traductions séparées. Voir [la politique multilingue](docs/engineering/INTERNATIONALIZATION.md) et [la revue de structure](docs/engineering/STRUCTURE_REVIEW.md).

Le socle exécutable a été actualisé pour Node 26 et les outils stables vérifiés le 10 octobre 2026. Les [versions et exceptions de compatibilité](docs/engineering/TOOLCHAIN.md) précisent les écarts avec les anciennes études de stack et la transition PostgreSQL 17 → 18.
