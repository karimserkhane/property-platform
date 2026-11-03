# Sauvegardes et contrôle de restauration

Mise en place le 23 octobre 2026 (tâche [A03](../tasks/A03.md)). Les données métier restent reconstructibles par les migrations et les pipelines Prefect ; les sauvegardes conservent en plus ce que les pipelines ne recréent pas (décisions d'opérateur, médias privés, reçus archivés) et permettent une reprise rapide.

## Ce qui est sauvegardé

| Élément | Comment | Où |
| --- | --- | --- |
| Base PostgreSQL/PostGIS `property_platform` | `pg_dump` 18, format personnalisé compressé, pris sur **un seul instantané** exporté ; le nombre de lignes de chaque table de `real_estate` et `evidence` est compté sur ce même instantané | `property_platform-<horodatage UTC>.dump` |
| Manifeste | Nom, date, version du serveur, taille, SHA-256 du fichier, comptes par table, résumé des copies | `property_platform-<horodatage UTC>.json` |
| Médias privés (`/media`) et reçus de collecte (`/data`) | Copie incrémentale : seuls les fichiers nouveaux ou modifiés sont recopiés ; rien n'est supprimé du miroir | `files/media/`, `files/receipts/` |

Le dossier est `BACKUP_DIR` dans le conteneur d'ingestion, monté depuis `${PROPERTY_PLATFORM_BACKUP_DIR:-../../.cache/backups}` (relatif à `infra/local`), c'est-à-dire `.cache/backups` à la racine du dépôt par défaut : un dossier de l'hôte ignoré par Git, qui survit à une réinitialisation de Docker. Une seconde copie, ailleurs, se configure à part : voir [Copie vers une seconde destination](#copie-vers-une-seconde-destination-a30).

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

Mesures du 3 novembre 2026, avant et après le déplacement des corps de captures hors de PostgreSQL ([A29](../tasks/A29.md)) :

| | Avant (15:43 UTC) | Après (16:04 UTC) |
| --- | --- | --- |
| Dump | 1 144,7 Mo, 5 min 12 avec le miroir | **438,1 Mo** (−62 %), 7 min 09 dont la première copie de 2 984 objets (1,28 Go) dans `files/media` |
| Tables, lignes | 58, 2 782 609 | 58, 2 801 028 |
| `restore-check` | 4 min 54, sans écart, 1 objet vérifié | 8 min 04, sans écart, **2 985 objets** vérifiés par taille et SHA-256 |

Les nuits suivantes ne recopient que les nouveaux objets. Chaque dump conservé (7 jours, 4 semaines) pèse donc environ 700 Mo de moins ; le miroir garde une seule copie des objets.

## Copie vers une seconde destination (A30)

**Décision de Karim (3 novembre 2026)** : les sauvegardes restent en local pour le moment ; la copie doit pouvoir passer plus tard à une solution cloud sans réécriture. Le module `backup_copy.py` d'`apps/ingestion` copie chaque sauvegarde réussie vers la destination choisie par `PROPERTY_PLATFORM_BACKUP_COPY_TARGET` (fichier `infra/local/.env`, ignoré par Git) :

| Valeur | Destination | État |
| --- | --- | --- |
| vide (défaut) | aucune copie | actif sur le poste de Karim |
| `directory` | dossier de l'hôte `PROPERTY_PLATFORM_BACKUP_COPY_DIR`, monté sur `/backup-copy` : disque externe, dossier synchronisé, partage réseau | prêt, essayé le 3 novembre |
| `s3` | compartiment privé compatible S3 (R2, B2, S3…), variables `BACKUP_COPY_S3_*` | prêt, testé sans réseau ; aucun fournisseur choisi, aucun compte ni coût sans accord de Karim |

**Ce qui est copié et dans quel ordre.** Le miroir `files/` (médias privés, corps de captures déplacés par A10/A29, reçus), puis le dump, puis son manifeste : un manifeste présent dans la copie garantit que son dump et les fichiers qu'il référence y sont aussi. Chaque fichier est vérifié après écriture (taille et SHA-256 ; en S3, le fournisseur contrôle aussi la somme `ChecksumSHA256` envoyée et l'objet porte son SHA-256 en métadonnée). Un fichier déjà présent avec la même taille n'est pas recopié : les objets du miroir sont nommés par leur SHA-256 et les reçus ne sont jamais réécrits. La rotation de la copie est celle du dossier local (7 jours, 4 semaines) ; les fichiers du miroir n'y sont jamais supprimés.

**Échec visible.** La copie s'exécute dans le flow `backup-database`, après la sauvegarde locale et sa rotation : si elle échoue (dossier non monté, disque plein, somme différente, identifiants absents), le run Prefect échoue, alors que la sauvegarde locale est déjà complète.

**Restaurer depuis la copie.** Le flow `restore-check` accepte `source="copy"` (paramètre du run dans Prefect, l'horaire hebdomadaire garde `local`). Pour un dossier, la restauration lit directement la copie ; pour S3, le dump et le manifeste les plus récents sont téléchargés dans `BACKUP_DIR/.copy-restore` puis effacés, et chaque objet référencé est vérifié dans la copie par sa taille et son SHA-256, sans téléchargement.

**Activer une copie vers un dossier.** Dans `infra/local/.env` : `PROPERTY_PLATFORM_BACKUP_COPY_TARGET=directory` et `PROPERTY_PLATFORM_BACKUP_COPY_DIR=E:\property-platform-backups` (exemple pour un disque externe), puis recréer le seul conteneur d'ingestion avec `--env-file infra/local/.env`. Un dossier sur le même disque que Docker ne protège pas d'une panne ou d'une perte du PC : au 3 novembre, le poste n'a qu'un disque (C:, 47 Go libres), ce qui reste la limite de la décision « local ».

**Essai réel du 3 novembre 2026** (image de la branche, conteneur à part, sans toucher au runner) : copie de la sauvegarde `property_platform-20261103T160444Z` vers `.cache/backup-copy` en 14 min 09 (dump de 438 Mo et 6 153 fichiers du miroir, 2,94 Go) ; deuxième passage sans rien recopier ; `restore-check` depuis la copie vert en 6 min 51 (58 tables, 2 801 028 lignes, 2 985 objets vérifiés par taille et SHA-256). Le mode S3 est testé sans réseau (stub botocore), jamais contre un fournisseur réel.

**Passer au cloud plus tard.** Choisir le fournisseur et son budget (décision de Karim), créer un compartiment privé et une clé limitée à ce compartiment, remplir `BACKUP_COPY_S3_*` dans `.env`, puis `PROPERTY_PLATFORM_BACKUP_COPY_TARGET=s3`. Avant d'y copier des preuves privées, décider aussi du chiffrement côté poste (non fait : le chiffrement au repos du fournisseur ne protège pas d'un accès au compte). Les objets de plus de 5 Gio demanderont un envoi en plusieurs parties, non écrit (dump actuel : environ 440 Mo).

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
