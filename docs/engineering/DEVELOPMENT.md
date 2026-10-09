# Démarrage et vérification

Prérequis : Node.js 24, pnpm 11.25.0, Python 3.12, uv 0.13.0 ; Docker avec Compose pour les contrôles PostGIS et l'API locale. Les dépendances sont verrouillées dans `pnpm-lock.yaml` et `apps/api/uv.lock`.

## Web

Depuis la racine :

```sh
pnpm install --frozen-lockfile
pnpm dev:web
```

Ouvrir http://localhost:3000. La page initiale ne dépend pas d'une API distante et ne montre pas de données inventées.

La racine redirige vers `/en`. Utiliser le sélecteur ou `/ar`, `/es`, `/de`, `/ru` et les autres routes configurées. Voir [la politique multilingue](INTERNATIONALIZATION.md).

Pour vérifier l'artefact compilé, exécuter `pnpm build`, puis `pnpm --filter @liwa/web start`. Le pré-démarrage prépare les fichiers statiques du serveur standalone. Une image Docker web est fournie avec le même principe ; elle ne déploie rien automatiquement.

Le build de production utilise explicitement Webpack : la copie standalone avec Turbopack échoue dans l'environnement Windows vérifié. Le développement utilise encore le compilateur par défaut de Next.js. Les scripts d'installation de Parcel/SWC sont désactivés explicitement dans pnpm : leurs binaires de plateforme restent installés via les dépendances optionnelles. Ne pas installer avec `--no-optional`. Si SWC refuse un cache Windows partagé ou aux permissions incompatibles, `SWC_NATIVE_BINDING_CACHE` peut désigner un cache privé sous le profil utilisateur ; conserver les vérifications de sécurité du chargeur.

## API et PostGIS

```sh
docker compose -f infra/local/compose.yaml up -d --build
docker compose -f infra/local/compose.yaml exec api python manage.py migrate
```

API : http://localhost:8000/api/v1/health/live ; base prête : `/api/v1/health/ready` ; documentation locale : `/api/v1/docs`. Les ports sont limités à l'interface locale. Les identifiants Compose sont exclusivement pour le développement. `down` conserve le volume ; `down -v` supprime ses données et ne doit pas être utilisé sans intention explicite.

Pour utiliser l'Admin en local, créer un utilisateur avec `docker compose -f infra/local/compose.yaml exec api python manage.py createsuperuser`. Ne pas créer ni versionner un compte par défaut.

## Vérifications et contrat

```sh
pnpm lint
pnpm typecheck
pnpm test:web
pnpm docs:check
pnpm build
node scripts/prepare-web-runtime.mjs
pnpm smoke:web
uv sync --project apps/api --frozen
uv run --project apps/api ruff check apps/api
uv run --project apps/api ruff format --check apps/api
uv run --project apps/api lint-imports --config apps/api/pyproject.toml
uv run --project apps/api pytest apps/api/tests -c apps/api/pyproject.toml
uv run --project apps/api python -m liwa.export_openapi --output packages/contracts/openapi.json
pnpm contracts:generate
pnpm contracts:check
```

Les tests locaux isolés utilisent SQLite uniquement pour HTTP et export de schéma, sans prétendre vérifier le SIG. La CI installe les bibliothèques GIS et utilise un vrai service PostGIS avec `LIWA_TEST_POSTGIS=1`, exécute les migrations et le test spatial. Sur un hôte avec les bibliothèques GIS, définir `DATABASE_URL` et ce flag pour reproduire l'intégration.

Après modification d'API, régénérer puis committer **OpenAPI et types TypeScript** ensemble. La CI vérifie le schéma exporté et les types générés. Next construit ses artefacts avant déploiement ; le petit processus de production ne compile pas le projet.

## Production

L'image API s'exécute sans root avec des dépendances runtime seulement. Le démarrage de production exige `DJANGO_SECRET_KEY`, `DATABASE_URL` et `DJANGO_ALLOWED_HOSTS`. Le déploiement public demande encore reverse proxy HTTPS, statiques de l'administration, politique d'accès du personnel, SMTP, schéma Supabase non exposé, rôles SQL et sauvegardes. Aucun déploiement public ni service payant n'est activé par ce socle.

Prochaine étape : définir le dossier pilote et ses modèles typés, puis la tranche carte → fiche → preuve → correction → publication, avec les critères du contre-audit.
