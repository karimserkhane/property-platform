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
| `s3` | compartiment privé compatible S3 (R2, B2, S3…), variables `BACKUP_COPY_S3_*`, **chiffrement obligatoire** (voir plus bas) | prêt, testé sans réseau ; aucun compte ni coût sans accord de Karim |

**Ce qui est copié et dans quel ordre.** Le miroir `files/` (médias privés, corps de captures déplacés par A10/A29, reçus), puis le dump, puis son manifeste : un manifeste présent dans la copie garantit que son dump et les fichiers qu'il référence y sont aussi. Chaque fichier est vérifié après écriture (taille et SHA-256 ; en S3, le fournisseur contrôle aussi la somme `ChecksumSHA256` envoyée et l'objet porte son SHA-256 en métadonnée). Un fichier déjà présent avec la même taille n'est pas recopié : les objets du miroir sont nommés par leur SHA-256 et les reçus ne sont jamais réécrits. La rotation de la copie est celle du dossier local (7 jours, 4 semaines) ; les fichiers du miroir n'y sont jamais supprimés.

**Échec visible.** La copie s'exécute dans le flow `backup-database`, après la sauvegarde locale et sa rotation : si elle échoue (dossier non monté, disque plein, somme différente, identifiants absents), le run Prefect échoue, alors que la sauvegarde locale est déjà complète.

**Restaurer depuis la copie.** Le flow `restore-check` accepte `source="copy"` (paramètre du run dans Prefect, l'horaire hebdomadaire garde `local`). Pour un dossier, la restauration lit directement la copie ; pour S3, le dump et le manifeste les plus récents sont téléchargés dans `BACKUP_DIR/.copy-restore` puis effacés, et chaque objet référencé est vérifié dans la copie par sa taille et son SHA-256, sans téléchargement.

**Activer une copie vers un dossier.** Dans `infra/local/.env` : `PROPERTY_PLATFORM_BACKUP_COPY_TARGET=directory` et `PROPERTY_PLATFORM_BACKUP_COPY_DIR=E:\property-platform-backups` (exemple pour un disque externe), puis recréer le seul conteneur d'ingestion avec `--env-file infra/local/.env`. Un dossier sur le même disque que Docker ne protège pas d'une panne ou d'une perte du PC : au 3 novembre, le poste n'a qu'un disque (C:, 47 Go libres), ce qui reste la limite de la décision « local ».

**Essai réel du 3 novembre 2026** (image de la branche, conteneur à part, sans toucher au runner) : copie de la sauvegarde `property_platform-20261103T160444Z` vers `.cache/backup-copy` en 14 min 09 (dump de 438 Mo et 6 153 fichiers du miroir, 2,94 Go) ; deuxième passage sans rien recopier ; `restore-check` depuis la copie vert en 6 min 51 (58 tables, 2 801 028 lignes, 2 985 objets vérifiés par taille et SHA-256). Le mode S3 est testé sans réseau (stub botocore), jamais contre un fournisseur réel.

**Chiffrement sur le poste ([A30](../tasks/A30.md), décision du 7 novembre 2026).** Avec `BACKUP_COPY_AGE_RECIPIENT` (la clé **publique** [age](https://age-encryption.org), `age1…`), chaque fichier (miroir, dump, manifeste) est chiffré sur le poste avant de partir et stocké sous `<nom>.age`. La cible `s3` refuse de démarrer sans cette clé ; la cible `directory` reste en clair si elle est vide, mais se chiffre de la même façon si elle est remplie (utile pour un dossier synchronisé).

- **Ce que voit le fournisseur** : uniquement du chiffré. Restent visibles les noms de fichiers (dont l'empreinte SHA-256 des objets du miroir, qui permet seulement de confirmer qu'un fichier déjà connu y figure), leur taille approximative et les dates d'envoi.
- **La clé privée ne reste pas sur le poste.** Le poste chiffre avec la clé publique seule : un vol du poste ou des identifiants S3 n'ouvre pas la copie. La clé privée vit dans le gestionnaire de mots de passe de Karim et sur papier, jamais dans Git, une image, `.env` ou un chat. **Sans elle, la copie est perdue** : d'où le contrôle de restauration ci-dessous, à faire dès la première copie.
- **Déjà copié ?** La taille du fichier en clair se déduit de la taille stockée (format age : en-tête fixe, 16 octets par bloc de 64 Kio) : la liste du compartiment suffit, sans téléchargement ni requête par fichier.
- **Changer de clé** : les fichiers déjà envoyés restent lisibles seulement avec l'ancienne clé. Utiliser un nouveau `BACKUP_COPY_S3_PREFIX` avec la nouvelle clé et garder l'ancienne jusqu'à la fin de la rotation.
- **Fichiers temporaires** : un fichier à la fois, dans `BACKUP_DIR/.copy-age-*` (l'hôte, pas la couche Docker), effacé après usage.

**S3 local en attendant un fournisseur (choix de Karim, 14 novembre 2026).** Karim préfère commencer par un serveur S3 sur le poste, pour que la copie parle déjà S3 et que le passage à un fournisseur hébergé se limite aux réglages. `infra/local/compose.backup-s3.yaml` (profil `backup-s3`) lance [Garage](https://garagehq.deuxfleurs.fr/) 2.5.0, figé par digest : un nœud, un compartiment et une clé créés au démarrage depuis `infra/local/.env`, aucun port publié (seuls les conteneurs du projet le joignent, à l'adresse `http://backup-s3:3900`), objets rangés dans `${PROPERTY_PLATFORM_BACKUP_S3_DIR:-../../.cache/backup-s3}`, un dossier de l'hôte ignoré par Git, hors du disque de Docker.

- **Limite** : il est sur le même PC que les sauvegardes. Il ne protège ni d'une panne du disque ni d'une perte du PC ; c'est une étape, pas la copie hors machine de la décision du 7 novembre.
- **Réglages** (`infra/local/.env`) : `PROPERTY_PLATFORM_BACKUP_COPY_TARGET=s3`, `BACKUP_COPY_S3_ENDPOINT_URL=http://backup-s3:3900`, `BACKUP_COPY_S3_REGION=garage`, `BACKUP_COPY_S3_BUCKET=property-platform-backups`, `BACKUP_COPY_AGE_RECIPIENT=age1…` ; `BACKUP_COPY_S3_ACCESS_KEY_ID` vaut `GK` suivi de 24 caractères hexadécimaux, `BACKUP_COPY_S3_SECRET_ACCESS_KEY` et `BACKUP_S3_LOCAL_RPC_SECRET` 64 caractères hexadécimaux chacun, générés une fois sur le poste (par exemple `openssl rand -hex 32` dans Git Bash) et jamais affichés ni copiés ailleurs.
- **Démarrer** : ajouter `-f infra/local/compose.backup-s3.yaml --profile backup-s3` aux fichiers et profils du conteneur d'ingestion en place, puis `up -d --no-deps backup-s3` et recréer le seul conteneur d'ingestion avec `--env-file infra/local/.env`. Le chiffrement `age` reste obligatoire, comme pour tout S3.
- **Passer chez un fournisseur** : créer le compartiment et la clé (étape 1 ci-dessous), remplacer dans `.env` l'adresse, la région, le compartiment et la clé, garder la même clé publique `age`. La première sauvegarde suivante recopie tout ; on peut ensuite arrêter `backup-s3` et, avec l'accord de Karim, effacer son dossier.
- **Essai du 14 novembre 2026** (conteneurs et réseau à part, jamais la pile en place) : avec le code de copie de `main` et le vrai `age`, une sauvegarde factice de 40 à 70 Mo est copiée chiffrée (empreinte `ChecksumSHA256` acceptée, en-tête `age-encryption.org/v1` côté serveur), le deuxième passage ne recopie rien, la relecture avec la clé privée redonne le fichier à l'octet près ; objets et métadonnées conservés après redémarrage, dans un dossier Windows monté ; service lancé sans aucune capacité Linux.

**Activer la copie chiffrée vers S3 (Karim, après fusion et redéploiement de l'image d'ingestion).**

1. Créer le compartiment privé et versionné et une clé limitée à ce compartiment chez le fournisseur retenu (Backblaze B2 proposé le 7 novembre).
2. Créer la paire de clés, dans un terminal du poste : `docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion run --rm --no-deps ingestion age-keygen`. Noter la ligne `AGE-SECRET-KEY-…` dans le gestionnaire de mots de passe et sur papier. Ne pas la coller ailleurs.
3. Dans `infra/local/.env` : `BACKUP_COPY_S3_*`, `BACKUP_COPY_AGE_RECIPIENT=age1…` (la clé publique), puis `PROPERTY_PLATFORM_BACKUP_COPY_TARGET=s3`. Recréer le seul conteneur d'ingestion avec `--env-file infra/local/.env`.
4. Après la première sauvegarde copiée, contrôler la restauration en donnant la clé privée à un conteneur temporaire seulement. Enregistrer la clé dans un fichier hors du dépôt, puis :

```bash
docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion run --rm --no-deps -v "C:/chemin/cle-age.txt:/run/secrets/backup-age-key:ro" -e BACKUP_COPY_AGE_IDENTITY_FILE=/run/secrets/backup-age-key ingestion python -c "from property_platform_ingestion import backup_copy; print(backup_copy.restore_check_from_copy())"
```

Commande pour PowerShell ; dans Git Bash, la préfixer par `MSYS_NO_PATHCONV=1`. Le résultat doit contenir `'ok': True`. Supprimer ensuite ce fichier. Ce contrôle télécharge et déchiffre le dump et chaque objet référencé : il prouve que la clé ouvre vraiment la copie. Le flow Prefect `restore-check` avec `source="copy"` échoue volontairement avec un message clair sur une copie chiffrée, puisque le runner n'a pas la clé.

Les objets de plus de 5 Gio demanderont un envoi en plusieurs parties, non écrit (dump actuel : environ 440 Mo).

## Restaurer manuellement

À réserver à une perte réelle de données, avec l'accord du propriétaire. Ne jamais restaurer par-dessus la base en service : restaurer dans une nouvelle base, vérifier, puis basculer.

```bash
docker compose -f infra/local/compose.yaml exec db createdb -U property_platform property_platform_restored
docker compose -f infra/local/compose.yaml cp .cache/backups/property_platform-<horodatage>.dump db:/tmp/restore.dump
docker compose -f infra/local/compose.yaml exec db pg_restore -U property_platform --no-owner --no-privileges --exit-on-error -d property_platform_restored /tmp/restore.dump
```

Depuis une copie chiffrée, déchiffrer d'abord chaque fichier : `age --decrypt -i <fichier de clé> -o <nom> <nom>.age` (le binaire officiel d'age suffit, sans ce dépôt).

Comparer ensuite les comptes avec le manifeste (le flow `restore-check` fait la même vérification). Les fichiers de `files/media` et `files/receipts` se recopient dans les volumes `media-data` et `ingestion-data` par un conteneur temporaire qui monte ces volumes.

## Ce que les sauvegardes ne remplacent pas

La [reconstruction complète depuis les pipelines](../tasks/A04.md) reste l'objectif : une base vide, les migrations et les flows doivent suffire pour les données publiques. Les sauvegardes couvrent les décisions humaines et les originaux privés, et raccourcissent la reprise.

Le flow manuel [rebuild-check](REBUILD.md) vérifie séparément le rejeu des captures
dans une base vide migrée. Son rapport distingue les tables comparées exactement,
les nouvelles traces d'exécution et les états qui nécessitent toujours A03.
