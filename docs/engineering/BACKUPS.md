# Sauvegardes et contrôle de restauration

Mise en place le 23 octobre 2026 (tâche [A03](../tasks/A03.md)). Les données métier restent reconstructibles par les migrations et les pipelines Prefect ; les sauvegardes conservent en plus ce que les pipelines ne recréent pas (décisions d'opérateur, médias privés, reçus archivés) et permettent une reprise rapide.

## Ce qui est sauvegardé

| Élément | Comment | Où |
| --- | --- | --- |
| Base PostgreSQL/PostGIS `property_platform` | `pg_dump` 18, format personnalisé compressé, pris sur **un seul instantané** exporté ; le nombre de lignes de chaque table de `real_estate` et `evidence` est compté sur ce même instantané | `property_platform-<horodatage UTC>.dump` |
| Manifeste | Nom, date, version du serveur, taille, SHA-256 du fichier, comptes par table, résumé des copies | `property_platform-<horodatage UTC>.json` |
| Médias privés (`/media`) et reçus de collecte (`/data`) | Copie incrémentale : seuls les fichiers nouveaux ou modifiés sont recopiés ; rien n'est supprimé du miroir | `files/media/`, `files/receipts/` |

Le dossier est `BACKUP_DIR` dans le conteneur d'ingestion, monté depuis `${PROPERTY_PLATFORM_BACKUP_DIR:-../../.cache/backups}` (relatif à `infra/local`), c'est-à-dire `.cache/backups` à la racine du dépôt par défaut : un dossier de l'hôte ignoré par Git, qui survit à une réinitialisation de Docker. Pour une copie hors de la machine, pointer `PROPERTY_PLATFORM_BACKUP_DIR` vers un disque externe ou un dossier synchronisé.

Les identifiants de la base passent aux outils PostgreSQL par l'environnement (`PGPASSWORD`), jamais par la ligne de commande. Aucune sauvegarde n'entre dans Git ni dans une image.

## Déploiements Prefect

| Déploiement | Flow | Horaire initial (désactivé à l'installation) |
| --- | --- | --- |
| `backup-database` | `property-platform-backup` | Chaque nuit à 01:30 (Asia/Dubai) |
| `restore-check` | `property-platform-restore-check` | Dimanche à 05:00 |

**Activation** : après le déploiement de l'image d'ingestion, activer les deux horaires dans Prefect (interface sur le port 4200, ou `prefect deployment schedule resume`).

**Rotation** : les 7 sauvegardes les plus récentes, plus la plus récente de chacune des 4 dernières semaines ISO. Seuls les fichiers `property_platform-<horodatage>.dump/.json` créés par ce mécanisme sont concernés ; les anciennes sauvegardes manuelles du même dossier ne sont jamais supprimées.

**Contrôle de restauration** : vérifie le SHA-256 du fichier, restaure dans une base jetable `restore_check_<horodatage>` sur le même serveur, compare les comptes à ceux du manifeste, vérifie que chaque objet local de `evidence.stored_object` restauré (médias privés, corps bruts de captures déplacés par A10) existe dans le miroir `files/media` avec sa taille et son SHA-256 (les objets S3 sont seulement comptés), puis supprime toujours la base jetable. Un écart fait échouer le flow ; au plus 50 lignes d'écart sont listées, le reste est compté.

Mesures du premier essai réel (23 octobre 2026) : sauvegarde de 468 Mo en 2 min 30 (49 tables, 196 521 lignes) et première copie de 1 208 reçus (682 Mo) ; restauration contrôlée en 1 min 40, sans écart.

## Restaurer manuellement

À réserver à une perte réelle de données, avec l'accord du propriétaire. Ne jamais restaurer par-dessus la base en service : restaurer dans une nouvelle base, vérifier, puis basculer.

```bash
docker compose -f infra/local/compose.yaml exec db createdb -U property_platform property_platform_restored
docker compose -f infra/local/compose.yaml cp .cache/backups/property_platform-<horodatage>.dump db:/tmp/restore.dump
docker compose -f infra/local/compose.yaml exec db pg_restore -U property_platform --no-owner --no-privileges --exit-on-error -d property_platform_restored /tmp/restore.dump
```

Comparer ensuite les comptes avec le manifeste (le flow `restore-check` fait la même vérification). Les fichiers de `files/media` et `files/receipts` se recopient dans les volumes `media-data` et `ingestion-data` par un conteneur temporaire qui monte ces volumes.

## Ce que les sauvegardes ne remplacent pas

La [reconstruction complète depuis les pipelines](../tasks/A04.md) reste l'objectif : une base vide, les migrations et les flows doivent suffire pour les données publiques. Les sauvegardes couvrent les décisions humaines et les originaux privés, et raccourcissent la reprise.

Le flow manuel [rebuild-check](REBUILD.md) vérifie séparément le rejeu des captures
dans une base vide migrée. Son rapport distingue les tables comparées exactement,
les nouvelles traces d'exécution et les états qui nécessitent toujours A03.
