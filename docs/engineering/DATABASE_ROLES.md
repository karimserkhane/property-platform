# Rôles PostgreSQL et bases d'essai des agents

Tâche [A45](../tasks/A45.md), commencée le 14 novembre 2026. Jusqu'ici l'API, l'ingestion et les agents utilisent la même identité `property_platform`, super-utilisateur de création du serveur ([audit du 8 novembre](AUDIT_STRUCTURE_20261108.md)). Un agent peut donc écrire dans la base partagée par erreur, et aucun ne peut essayer une donnée réelle sans risque.

`scripts/db/database.mjs` pose des rôles séparés et crée ou supprime une base d'essai par agent, par une procédure rejouable : aucun SQL manuel sur la base partagée. Sans `--yes`, rien ne change : le plan est affiché.

## Les rôles

| Rôle | Pour qui | Droits |
| --- | --- | --- |
| `pp_agent_readonly` | Agents qui lisent la base partagée | Connexion à `property_platform` ; lecture de toutes les tables (`pg_read_all_data`) ; transactions en lecture seule par défaut, requêtes limitées à 120 s. Aucun droit d'écriture : même en repassant la session en écriture, PostgreSQL refuse (`permission denied`). |
| `pp_agent_scratch` | Agents qui essaient une donnée réelle | Propriétaire des bases `scratch_*` ; **aucune connexion** à `property_platform`. |
| `pp_app` | API et ingestion, plus tard | Ni super-utilisateur ni création de rôle ; peut créer des bases (contrôles `restore-check`, `rebuild-check`, bases de test). Connexion à `property_platform`, mais pas encore propriétaire des schémas : voir « Reste à faire ». |

La procédure retire aussi la connexion à `property_platform` au rôle `PUBLIC` : seuls le propriétaire, les super-utilisateurs, `pp_agent_readonly` et `pp_app` s'y connectent. Les autres bases du serveur ne changent pas.

```bash
node scripts/db/database.mjs roles          # plan
node scripts/db/database.mjs roles --yes    # applique, rejouable
```

**Mots de passe.** Générés au premier `roles --yes`, gardés dans `.cache/db/roles.local.json` du dossier principal (ignoré par Git, partagé par tous les worktrees), puis passés à `psql` par l'environnement (`\getenv`) : jamais sur une ligne de commande, jamais affichés, jamais dans une image. Un mot de passe existant est conservé ; en supprimer un du fichier puis relancer `roles --yes` le remplace.

**Ce que ce n'est pas.** Un garde-fou contre l'erreur, pas une frontière de sécurité contre un agent malveillant : un agent qui a accès à Docker peut toujours ouvrir `psql` en super-utilisateur dans le conteneur. La règle d'[AGENTS.md](../../AGENTS.md) reste : pas de SQL manuel sur la base partagée.

## Lire la base partagée

```bash
node scripts/db/database.mjs psql --as readonly -- -c "select count(*) from real_estate.parcel"
```

La connexion passe par TCP dans le conteneur, sous le rôle `pp_agent_readonly` : ses droits s'appliquent. Dans l'image PostGIS officielle, l'accès local au conteneur est en `trust` : le mot de passe ne sert vraiment que depuis l'hôte (port 5432).

## Base d'essai par agent

```bash
node scripts/db/database.mjs scratch create claude --name a45 --yes
node scripts/db/database.mjs psql --as scratch --db scratch_claude_a45
node scripts/db/database.mjs scratch drop claude --name a45 --yes
node scripts/db/database.mjs scratch list
```

- Nom `scratch_<agent>` ou `scratch_<agent>_<suffixe>` (minuscules et chiffres) ; la commande refuse tout autre nom, si bien qu'elle ne peut pas supprimer `property_platform`, `restore_check_*`, `rebuild_check_*` ni une base de test.
- Créée depuis `template_postgis` (PostGIS déjà installé, puisque `pp_agent_scratch` ne peut pas créer l'extension), propriétaire `pp_agent_scratch`, fermée à `PUBLIC`, lisible par `pp_agent_readonly`.
- **Place disque contrôlée avant** : au moins 12 Go libres sur le disque du PC (qui porte le disque de Docker) et sur le volume du serveur, comme pour les déploiements ; sinon rien n'est créé. `--min-free-gb` change le seuil (essais sur un petit serveur jetable seulement).
- La suppression ferme les connexions ouvertes (`WITH (FORCE)`) et demande `--yes`.
- Une base d'essai se remplit par les migrations et les commandes documentées, ou par une restauration de sauvegarde ; elle ne remplace pas une base de test des contrôles.

Options communes : `--container` (par défaut `property-platform-local-db-1`), `--superuser` (par défaut `property_platform`), `--secrets` (autre fichier de mots de passe, pour un serveur jetable).

## Essai du 14 novembre 2026

Sur un serveur PostGIS jetable (même image figée, données en mémoire, sans réseau), jamais sur la base partagée :

- `roles --yes` deux fois : mêmes attributs, aucune erreur ;
- `pp_agent_readonly` lit, ne peut ni écrire ni créer de table, même après `set default_transaction_read_only = off` (`permission denied`) ;
- `pp_agent_scratch` refusé sur `property_platform` (`User does not have CONNECT privilege`), crée tables et géométries dans sa base d'essai ;
- `pp_app` se connecte mais ne lit pas encore `real_estate` (pas propriétaire) ;
- création refusée avec 0,9 Go libres ; création, recréation (rien à faire), suppression, re-suppression (rien à faire).

## Reste à faire (A45)

1. **Adoption par l'API et l'ingestion.** Transférer à `pp_app` la propriété des schémas et objets métier (`real_estate`, `evidence`, tables Django), sans toucher aux objets des extensions ; `REASSIGN OWNED` est impossible depuis le rôle de création du serveur. Puis faire créer les bases jetables de `restore-check`, `rebuild-check` et des tests depuis `template_postgis`, puisque PostGIS n'est pas une extension « de confiance ».
2. **Essai à part** de ce changement d'identité : restauration de la dernière sauvegarde dans un serveur jetable, migrations, `checks-api`, sauvegarde, `restore-check` et `rebuild-check` sous `pp_app`, avant de le proposer.
3. **Après fusion, avec Karim** : `roles --yes` sur le serveur partagé, puis bascule des fichiers Compose vers `pp_app`.
