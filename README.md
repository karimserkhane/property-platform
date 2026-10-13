# property-platform

Property Platform : plateforme immobilière cartographique destinée aux **sept émirats**, avec dossiers sourcés, plans, comparaison et suivi des changements. Premier jeu de données : Al Reem Island. Les autres territoires sont préparés dans la navigation ; leur collecte reste à activer après validation des sources.

## Documents de cadrage

- [Étude produit](docs/product/ETUDE_PRODUIT_PROPERTY_PLATFORM.md)
- [Approfondissement stratégique](docs/product/STRATEGIE_PRODUIT_PROPERTY_PLATFORM.md)
- [Architecture actuelle — revue critique V2](docs/architecture/REVUE_ARCHITECTURE_PROPERTY_PLATFORM_V2.md)
- [Contre-audit : décision maintenue et conditions de validation](docs/architecture/AUDIT_DECISION_STACK_PROPERTY_PLATFORM.md)
- [Proposition de stack précédente — historique](docs/archive/ARCHITECTURE_STACK_PROPERTY_PLATFORM.md)

Le dépôt contient Next.js/TypeScript, Django/Django Ninja, contrats OpenAPI générés et PostgreSQL/PostGIS. L'atlas local affiche les parcelles colorées, secteurs, rues, empreintes de bâtiments, lieux, références de projets et vues satellite, avec recherches, filtres et provenance. Al Reem et [Saadiyat Island](docs/engineering/SAADIYAT.md) disposent de sources distinctes et d'imports réels. [Prefect orchestre les données configurées](docs/engineering/INGESTION.md) depuis une application dédiée, avec interface locale sur le port 4200, historique durable et dix-sept déploiements. Quatorze calendriers sont initialement désactivés sur une installation neuve ; trois opérations restent manuelles. Les calendriers locaux de Karim sont activés le dimanche. Voir aussi [les commandes expliquées](docs/engineering/DEVELOPMENT.md#couches-reem) et [la couverture réelle comparée au HTML](docs/engineering/REEM_MAP.md). Logements, prix structurés, dossiers publics approuvés, authentification et stockage objet restent à développer. Aucun déploiement public n'est effectué.

## Structure et démarrage

- `apps/web` : interface Next.js.
- `apps/api` : cœur Django/GeoDjango et modules catalogue, preuves, publication.
- `apps/ingestion` : collecteurs Python, reçus d'acquisition et orchestration Prefect ; réutilise les services métier Django.
- `packages/contracts` : schéma API et types TypeScript générés.
- `packages/branding` : nom affiché et symbole configurables, indépendants des noms techniques.
- `infra/local` : environnement Docker Compose avec PostGIS et overlay facultatif d'ingestion, métadonnées Prefect séparées.
- `.github/workflows` : qualité, compilation, frontières de modules et intégration PostGIS.

Lire [les règles de structure](docs/engineering/REPOSITORY.md) et [le guide de développement](docs/engineering/DEVELOPMENT.md). Les dépendances JavaScript et Python sont verrouillées ; les directions entre modules et la cohérence des contrats sont vérifiées automatiquement.

Voir [la couverture nationale et l'ajout d'une nouvelle zone](docs/engineering/UAE_COVERAGE.md) : géographie centralisée, profils de sources distincts et limites de charge du prototype.

Pour changer le nom commercial sans renommer le code, modifier `packages/branding/src/brand.ts` ; voir [la configuration de marque et la reprise de l'ancienne base locale](docs/engineering/BRANDING.md).

L'interface utilise l'anglais par défaut, des routes par langue et des traductions séparées. Voir [la politique multilingue](docs/engineering/INTERNATIONALIZATION.md) et [la revue de structure](docs/engineering/STRUCTURE_REVIEW.md).

Le socle exécutable a été actualisé pour Node 26 et les outils stables vérifiés le 10 octobre 2026. Les [versions et exceptions de compatibilité](docs/engineering/TOOLCHAIN.md) précisent les écarts avec les anciennes études de stack et la transition PostgreSQL 17 → 18.

L'application d'ingestion ajoutée le 13 octobre utilise Python 3.14.8, comme l'API et le fichier `.python-version` de racine. [Le guide Prefect](docs/engineering/INGESTION.md) explique la première installation, l'interface, les exécutions manuelles, les calendriers et l'arrêt des services sans perdre les données.
