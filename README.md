# property-platform

Liwa Atlas : plateforme immobilière cartographique évolutive, avec dossiers sourcés, plans, comparaison et suivi des changements. Première zone envisagée : Al Reem Island.

## Documents de cadrage

- [Étude produit](ETUDE_PRODUIT_LIWA_ATLAS.md)
- [Approfondissement stratégique](STRATEGIE_PRODUIT_LIWA_ATLAS.md)
- [Architecture actuelle — revue critique V2](REVUE_ARCHITECTURE_LIWA_ATLAS_V2.md)
- [Contre-audit : décision maintenue et conditions de validation](AUDIT_DECISION_STACK_LIWA_ATLAS.md)
- [Proposition de stack précédente — historique](ARCHITECTURE_STACK_LIWA_ATLAS.md)

Le dépôt contient le cadrage et un premier socle exécutable : Next.js/TypeScript, Django/Django Ninja, contrats OpenAPI générés et configuration PostgreSQL/PostGIS. La carte, les modèles métier, l'authentification, le stockage et les workers seront intégrés avec le dossier pilote. Le budget de pilote et ses limites sont détaillés dans la revue V2 ; aucun déploiement public n'est effectué.

## Structure et démarrage

- `apps/web` : interface Next.js.
- `apps/api` : cœur Django/GeoDjango et modules catalogue, preuves, publication.
- `packages/contracts` : schéma API et types TypeScript générés.
- `infra/local` : environnement Docker Compose avec PostGIS.
- `.github/workflows` : qualité, compilation, frontières de modules et intégration PostGIS.

Lire [les règles de structure](docs/engineering/REPOSITORY.md) et [le guide de développement](docs/engineering/DEVELOPMENT.md). Les dépendances JavaScript et Python sont verrouillées ; les directions entre modules et la cohérence des contrats sont vérifiées automatiquement.
