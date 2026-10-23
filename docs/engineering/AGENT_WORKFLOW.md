# Travail des agents : Codex, Claude Code et autres

Guide opérationnel commun à toute IA (ou personne) qui modifie le dépôt. Les règles courtes sont dans [AGENTS.md](../../AGENTS.md) ; ce document décrit le déroulé. Il s'applique quel que soit l'outil : un agent sans mémoire doit pouvoir reprendre le travail à partir du dépôt seul.

## 1. Démarrer

1. `git status`, `git branch --show-current`. Si le dossier contient des modifications non commitées d'un autre agent, travailler dans un `git worktree` séparé (par exemple `../property-platform-<agent>`).
2. Lire [AGENTS.md](../../AGENTS.md), puis le [tableau des tâches](../tasks/BOARD.md).
3. Vérifier qu'aucune PR ouverte ne traite déjà la tâche : `gh pr list --state open --search "<id>"`.

## 2. Choisir et réserver une tâche

Une tâche est **prenable** si son statut est `todo`, si toutes ses dépendances sont `done` et si `needs_owner_decision` vaut `no` (ou si la décision est notée dans son journal). Prendre la plus petite priorité, puis l'identifiant le plus petit.

Réserver avant de coder, pour que l'autre agent le voie sur GitHub :

1. Branche `<agent>/<id>-<sujet>` depuis la branche de référence à jour (aujourd'hui `codex/abu-dhabi-context-ingestion`, puis `main` quand elle aura été fusionnée).
2. Dans le fichier de la tâche et dans `BOARD.md` : `status: in-progress`, `owner: <agent>`, `branch: <branche>`.
3. Commit `Claim <id>: <titre>`, push, puis **PR en brouillon** vers la branche de référence ; noter son numéro dans `pr:`.

Une réservation sans commit depuis plus de 3 jours peut être reprise : l'indiquer dans le journal de la tâche et dans la PR.

## 3. Pendant le travail

- Commits petits et cohérents. Le journal de la tâche (en tête du fichier) et la description de PR disent : fait, reste à faire, contrôles lancés, contrôles non lancés et pourquoi.
- Une tâche = une PR. Si la tâche est trop grande, la découper en nouvelles tâches (nouveaux fichiers, `BOARD.md` à jour) plutôt que de livrer une PR géante.
- Ne jamais modifier la branche d'un autre agent ; faire une revue en commentaire de PR.

## 4. Contrôles en une commande

Les mêmes contrôles que la CI tournent dans Docker, sous Linux, sans toucher aux services partagés (`--no-deps`). La base locale doit être démarrée. Depuis la racine du dépôt ou du worktree :

```bash
docker compose -f infra/local/compose.yaml -f infra/local/compose.checks.yaml --profile checks run --rm --no-deps checks-api
docker compose -f infra/local/compose.yaml -f infra/local/compose.checks.yaml --profile checks run --rm --no-deps checks-ingestion
docker compose -f infra/local/compose.yaml -f infra/local/compose.checks.yaml --profile checks run --rm --no-deps checks-web
```

| Service | Contrôles |
| --- | --- |
| `checks-api` | Ruff, frontières de modules, `manage.py check`, migrations manquantes, contrat OpenAPI à jour, tests PostGIS (base `test_property_platform` créée et supprimée par les tests) |
| `checks-ingestion` | Ruff et tests d'ingestion |
| `checks-web` | Installation Linux des dépendances dans des volumes, Biome, contrats, TypeScript, tests web, liens Markdown ; `CHECK_BUILD=1` ajoute la compilation et le smoke HTTP |

Arguments pytest : `... run --rm --no-deps checks-api bash scripts/checks/api.sh -k parcel_tiles`. Après un changement de lockfile, reconstruire l'image avec `... --profile checks build checks-api` (ou `checks-ingestion`, `checks-web`). Dans un worktree, `docs:check` est sauté dans le conteneur : le lancer sur l'hôte avec `pnpm docs:check`.

## 5. Données reproductibles

Toute donnée métier doit pouvoir être reconstruite par les migrations et les pipelines Prefect :

- Une donnée entre par un collecteur ou une commande documentée qui crée sa capture, son exécution et son audit. Pas de SQL manuel dans la base partagée, pas de valeur saisie sans source.
- Une nouvelle table est rattachée à ses flows dans `evidence/pipeline_inventory.py` et appelle `evidence.install_row_journals(false)` dans sa migration ([DATA_HISTORY.md](DATA_HISTORY.md)).
- Une décision humaine (exclusion, rapprochement) passe par une commande auditée et réversible, sauvegardée (tâche A03).
- Les migrations sont additives ; ne jamais renuméroter une migration d'une autre branche sans le dire dans la PR.

## 6. Ajouter une technologie

Autorisé si elle sert une tâche et respecte la modularité :

- Service Docker **optionnel**, derrière un profil Compose, version figée (tag précis, idéalement digest), sans exposition publique ; aucune dépendance lourde dans le runtime web/API (OCR, rendu raster, modèles) ;
- versions, raison et alternatives notées dans [TOOLCHAIN.md](TOOLCHAIN.md) ; propriétaire et direction des dépendances dans [REPOSITORY.md](REPOSITORY.md) ;
- aucun service payant, abonnement ou clé de production sans accord explicite du propriétaire.

## 7. Mettre à jour la prévisualisation de Karim

Seulement après fusion (ou à la demande de Karim), depuis le dossier principal à jour :

```bash
docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview build api web
docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview up -d --no-build --no-deps --force-recreate api web
docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview up -d --no-build --no-deps --force-recreate remote-preview
```

La troisième commande est **obligatoire** après la recréation du site : le connecteur Tailscale partage son réseau ([REMOTE_PREVIEW.md](REMOTE_PREVIEW.md)). Si la PR ajoute une migration : `docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput` après le redémarrage de l'API. Si elle touche l'ingestion, reconstruire puis recréer `ingestion` avec **les mêmes fichiers Compose que le conteneur en place** (lire `docker inspect property-platform-local-ingestion-1 --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}'`), au minimum `compose.yaml` et `compose.ingestion.yaml` avec `--profile ingestion` ([INGESTION.md](INGESTION.md)). Un nouveau déploiement Prefect démarre avec son horaire désactivé ; ne l'activer que si la tâche le demande explicitement (par exemple les [sauvegardes](BACKUPS.md)), puis le noter dans la PR. Vérifier ensuite : API en bonne santé, site en `401` sans identifiants, Tailscale `Running`. Ne jamais supprimer un volume ni réinitialiser la base.

## 8. Terminer

1. Contrôles de la section 4 verts ; résultats copiés dans la PR.
2. Critères d'acceptation cochés dans le fichier de la tâche ; `status: done` dans le fichier et `BOARD.md` (dans la PR elle-même).
3. PR sortie du brouillon. Fusion par l'agent seulement si le propriétaire l'a délégué et si la CI GitHub est verte ; sinon, demander la revue.
4. Si la PR est abandonnée, remettre la tâche en `todo` et expliquer pourquoi dans son journal.
