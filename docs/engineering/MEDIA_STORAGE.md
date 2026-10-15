# Fichiers, R2/S3 et CDN

Le dépôt sait archiver les photographies acquises dans un stockage persistant et diffuser les **médias de projets approuvés**, y compris les vidéos MP4/WebM. PDF, JPEG, PNG, WebP et GLB utilisent les mêmes adaptateurs. Le [guide des projets et vidéos](PROJECTS.md) décrit les références officielles, l'ingestion de fichiers opérateur, la revue des droits et les pages web. Les fichiers des promoteurs restent des liens externes tant qu'ils ne disposent pas d'une autorisation de copie examinée.

En développement, les fichiers sont dans un volume Docker sur ton PC. Pour la future mise en ligne, le même code peut utiliser **Cloudflare R2**, par son API compatible S3. Un second bucket peut recevoir les seuls médias autorisés pour une diffusion publique par un domaine CDN. Aucun compte, abonnement, bucket ni domaine n’est créé par les commandes locales.

## 1. Le rôle de chaque composant

| Composant | Contenu et rôle |
|---|---|
| PostgreSQL/PostGIS | Identités des biens, sources, captures, licences, dates, SHA-256, tailles et références des fichiers |
| Stockage privé local ou R2 | Octets des fichiers archivés ; noms techniques immuables calculés depuis leur SHA-256 |
| Bucket public R2 distinct, facultatif | Copies des médias explicitement approuvés pour être publiées |
| Domaine CDN, facultatif | Distribution des copies publiques depuis `https://media.ton-domaine…` |
| Django | Vérification de provenance, contrôles d’autorisation et enregistrement des références |
| Prefect | Déclenchement, supervision et reprise de l’archivage après l’import |
| Next.js | Affichage depuis le CDN lorsque la copie publique existe ; sinon lecture via l’API locale |

Les photographies décoratives de l’accueil, leurs variantes optimisées, les polices et leurs licences restent des ressources versionnées du site. Leur petite taille et leur cycle de publication ne justifient pas un déplacement automatique. Les reçus de collecte Prefect restent dans leur volume privé séparé `/data`.

**Compatibilité avec les preuves existantes :** les petites captures historiques gardent leurs octets SQL et leurs dates ; l'archivage crée une copie vérifiée et ses liens. La migration `evidence/0020` ajoute une représentation principale externe : exactement `payload` SQL ou `primary_object_id`, jamais les deux ni aucun. Les nouveaux fichiers opérateur sont externes et n'inventent pas de statut HTTP. Aucun ancien payload n'est remplacé par une chaîne vide. Les formats de preuve et les commandes sont détaillés dans [PROJECTS.md](PROJECTS.md).

## 2. Les fichiers et les tables

Tous les chemins Windows ci-dessous partent de `C:\Users\Karim\Repositories\property-platform`.

| Emplacement | Responsabilité |
|---|---|
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\object_storage\core.py` | Formats, limites, préparation par flux, clés et vérification SHA-256 |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\object_storage\adapters.py` | Adaptateurs filesystem et S3/R2 ; aucune dépendance métier |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\media_storage.py` | Raccordement aux captures/licences et publication explicite |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\management\commands\archive_property_media.py` | Commande de reprise des photos existantes |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\migrations\0018_media_object_storage.py` | Création additive des trois tables dans le schéma `evidence` |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\flows.py` | Tâche d’archivage privée et flow `property-platform-media-storage` |
| `C:\Users\Karim\Repositories\property-platform\infra\local\compose.yaml` | Volume partagé `media-data` monté sur `/media` |
| `C:\Users\Karim\Repositories\property-platform\infra\local\compose.storage.s3.yaml` | Surcharge facultative de configuration R2/S3 |
| `C:\Users\Karim\Repositories\property-platform\infra\local\.env.example` | Exemple sans secrets ; à copier en `.env` ignoré par Git |
| `C:\Users\Karim\Repositories\property-platform\infra\storage\r2-public-cors.json` | Exemple CORS à adapter au vrai domaine public |

Les tables à ouvrir dans ton outil SQL sont :

- `property_platform.evidence.stored_object` : une copie physique, avec backend, namespace, bucket, clé, SHA-256, taille, MIME, création et vérification. Deux captures contenant la même photo peuvent partager cet objet privé.
- `property_platform.evidence.capture_object` : lien entre une capture et une copie physique, avec opérateur et date de stockage. Une nouvelle copie chez un autre fournisseur ajoute un lien ; elle ne réécrit pas les anciennes preuves.
- `property_platform.evidence.media_publication` : lien explicite entre une photo approuvée et sa copie publique, avec opérateur et date de publication. Une configuration CDN seule ne crée pas ces lignes.

Source originale, date de récupération, date de publication connue, date d’ingestion, exécution de collecte et licence restent accessibles par les relations `capture`, `property_media` et `licence_capture`. Les octets, clés privées et noms des opérateurs ne sont pas ajoutés au contrat public des fiches. Pour les photographies historiques, `delivery_url` reste nul sans copie publique approuvée. Les nouveaux médias de projets peuvent aussi fournir l’URL du relais privé après approbation ; voir [PROJECTS.md](PROJECTS.md).

## 3. Installer ou actualiser le stockage local

Ouvrir **PowerShell**, aller à la racine, puis lancer chaque commande séparément. La base existante doit être sauvegardée avant une migration ; voir [le guide des bases](DATABASE_DESIGN.md). Sur un poste où cette intégration a déjà été appliquée, ces commandes sont réexécutables.

```powershell
Set-Location 'C:\Users\Karim\Repositories\property-platform'
docker compose -f infra/local/compose.yaml build api
docker compose -f infra/local/compose.yaml up -d --no-build api
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
docker compose -f infra/local/compose.yaml exec api python manage.py check
docker compose -f infra/local/compose.yaml exec api python manage.py archive_property_media --actor Karim
```

Le build actualise le programme. `up` réutilise PostgreSQL et crée le volume **`property-platform-local_media-data`**, sans effacer les volumes existants. `migrate` crée les tables de métadonnées ; il ne télécharge aucun fichier. `check` valide la configuration sans contacter R2. `archive_property_media` copie les photos déjà acquises, vérifie leurs octets et enregistre les liens. **Aucune nouvelle photo n’est recherchée sur Internet par cette commande.**

La réponse contient `archived`, `published` et `remaining`. Avec la configuration locale, `published` reste zéro. Un deuxième passage sur des captures déjà archivées indique `archived: 0`. Si `remaining` est supérieur à zéro, relancer la commande : chaque lot traite au maximum 500 photos. Pour essayer un seul élément, ajouter `--limit 1`.

Le volume est visible dans Docker Desktop → **Volumes**. `/media/objects/sha256/…` est un chemin Linux **dans le conteneur** ; ce n’est pas un dossier Windows nommé `C:\media`. Arrêter les conteneurs conserve le volume. Ne pas utiliser `down -v`, supprimer ce volume ou lancer un nettoyage de volumes pour appliquer une mise à jour.

Avec Django exécuté directement sous Windows, `MEDIA_LOCAL_ROOT` permet de choisir un chemin absolu. Le défaut est `.cache/media` dans le répertoire de lancement. Le fichier `C:\Users\Karim\Repositories\property-platform\apps\api\.env.example` donne un exemple absolu. Django ne lit pas automatiquement les fichiers `.env` : définir les variables dans l’IDE ou dans l’environnement du terminal. Un serveur Django Windows et un serveur Docker ne partagent pas automatiquement leurs dossiers.

## 4. Relier Prefect

Après la migration, reconstruire aussi l’image d’ingestion : elle embarque les mêmes services Django et le SDK S3.

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion build ingestion
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion up -d --no-build ingestion
```

Le runner retrouve les calendriers existants. Les flows **property-presentations** et **saadiyat-property-presentations** enchaînent maintenant : acquisition → validation/import Django → **Archive acquired media**. Les écritures de fichiers s’effectuent après la transaction d’import. La tâche archive les photos en attente de tous les territoires enregistrés ; elle ne déclenche aucune nouvelle collecte et ne publie rien sur le CDN.

Dans [Prefect local](http://localhost:4200), le nouveau déploiement **media-storage**, flow **property-platform-media-storage**, permet une reprise manuelle. Il commence sans horaire. Les calendriers des imports existants restent conservés ; leurs futures exécutions feront l’archivage après l’import. Une panne de stockage fait échouer la tâche sans supprimer l’import déjà réussi. Relancer le job reprend les liens manquants ; une photo terminée n’est pas dupliquée. Les journaux Prefect et le champ `actor` du lien permettent de retrouver l’exécution.

## 5. Préparer R2, sans activer le cloud par défaut

### 5.1. Ce que tu dois faire dans Cloudflare

L'intégration du dépôt est prête ; il manque le compte, le bucket et ses identifiants. **Commencer avec le stockage privé, sans CDN public.** PostgreSQL reste dans Docker et le site continue à lire les mêmes tables. R2 héberge les fichiers ; il ne déploie ni le site, ni Django, ni PostgreSQL.

1. Ouvrir [le tableau de bord Cloudflare](https://dash.cloudflare.com/) et se connecter à son compte. Si R2 n'est pas encore activé, effectuer soi-même les étapes d'activation et de facturation présentées par Cloudflare.
2. Aller dans **Storage & databases → R2 → Overview**, puis **Create bucket**. Selon la présentation du tableau de bord, le menu peut aussi s'appeler **R2 object storage**.
3. Nommer le bucket **`property-platform-originals`**, choisir la classe **Standard** et conserver le placement automatique pour ce premier essai. Ce bucket sera réservé au développement ; la production aura son stockage et ses identifiants séparés.
4. Dans les réglages du bucket, laisser **Public Development URL / r2.dev désactivé** et ne raccorder aucun **Custom Domain** à ce bucket privé. Le site pourra lire les fichiers via notre backend authentifié auprès de R2.
5. Revenir à R2 → Overview → **Manage** dans **API Tokens**. Créer un token nommé, par exemple, `property-platform-dev-ingestion`, avec **Object Read & Write**, puis **Apply to specific buckets only → property-platform-originals**. Il n'a pas besoin de droits d'administration du compte ou de création de buckets.
6. Copier les deux identifiants **Access Key ID** et **Secret Access Key** dans le fichier local décrit à la section suivante. Il s'agit des identifiants **S3**, pas d'un token général Cloudflare à envoyer comme Bearer. Conserver le secret dans son gestionnaire de mots de passe : Cloudflare ne le réaffiche pas après cette étape.
7. Copier aussi l'**endpoint S3** affiché par Cloudflare, par exemple `https://IDENTIFIANT_DU_COMPTE.r2.cloudflarestorage.com`. Copier l'origine seule, sans ajouter `/property-platform-originals`.
8. Pour séparer les rôles, créer un second token `property-platform-dev-api`, limité au même bucket avec **Object Read only**, puis placer ses identifiants dans les deux variables `MEDIA_S3_READ_*`. Le runner garde le token d'écriture ; le serveur HTTP utilise celui de lecture.

Le premier essai n'exige **ni achat de domaine, ni Worker, ni Cloudflare Pages, ni logiciel AWS supplémentaire**. Les libellés ci-dessus et l'endpoint sont décrits dans le [démarrage S3 officiel de Cloudflare](https://developers.cloudflare.com/r2/get-started/s3/). La classe Standard dispose actuellement d'une allocation mensuelle gratuite de **10 GB-month**, 1 million d'opérations de classe A et 10 millions de classe B. Ce sont des franchises d'usage, pas un plafond bloquant les dépenses ; vérifier la [tarification R2](https://developers.cloudflare.com/r2/pricing/) et les indicateurs de consommation du compte. L'allocation gratuite ne concerne pas la classe Infrequent Access.

### 5.2. Remplir le fichier local du dépôt

Ouvrir dans PyCharm **`C:\Users\Karim\Repositories\property-platform\infra\local\.env`**. S'il a déjà été préparé sur ce poste, le remplir sans refaire la copie ci-dessous. Les valeurs S3 se trouvent dans l'écran de création du token et l'aperçu R2 :

```dotenv
MEDIA_S3_NAMESPACE=r2-primary
MEDIA_S3_ENDPOINT_URL=https://IDENTIFIANT_DU_COMPTE.r2.cloudflarestorage.com
MEDIA_S3_REGION=auto
MEDIA_S3_BUCKET=property-platform-originals
MEDIA_S3_ACCESS_KEY_ID=ACCESS_KEY_ID_DU_TOKEN_INGESTION
MEDIA_S3_SECRET_ACCESS_KEY=SECRET_ACCESS_KEY_DU_TOKEN_INGESTION
MEDIA_S3_READ_ACCESS_KEY_ID=ACCESS_KEY_ID_DU_TOKEN_API
MEDIA_S3_READ_SECRET_ACCESS_KEY=SECRET_ACCESS_KEY_DU_TOKEN_API
MEDIA_S3_PUBLIC_BUCKET=
MEDIA_PUBLIC_BASE_URL=
MEDIA_PUBLICATION_ENABLED=0
```

Remplacer les valeurs en majuscules par les vraies valeurs, directement dans l'IDE. Ne pas coller les clés dans le chat, dans un fichier suivi par Git, ni dans une commande PowerShell qui les conserverait dans son historique. Le namespace est notre identifiant stable de stockage ; ce n'est pas une valeur à rechercher chez Cloudflare. La région reste `auto`. Le bucket et l'endpoint sont deux réglages distincts. Les deux champs publics restent vides et la publication reste à zéro pendant cet essai privé.

Le fournisseur est interchangeable grâce au protocole S3 ; la configuration R2 est : endpoint HTTPS du compte et région **`auto`**. Le SDK officiel boto3 est verrouillé dans les deux environnements Python. Les clés sont fournies explicitement : le code ne cherche pas de profil AWS sur ton PC.

Les images API et ingestion fixent `AWS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt` : le SDK utilise le magasin Debian vérifié, y compris l’éventuelle autorité publique supplémentaire déjà approuvée pour les builds. Le SDK garde la vérification TLS active. Pour un SDK exécuté directement sur Windows derrière une inspection HTTPS, configurer au besoin `AWS_CA_BUNDLE` avec un bundle public vérifié ; ne jamais désactiver TLS pour contourner une erreur de certificat. Voir [TOOLCHAIN.md](TOOLCHAIN.md).

Copier le modèle de configuration :

Faire cette copie une seule fois : si le fichier `.env` existe déjà, le modifier sans écraser ses valeurs.

```powershell
Copy-Item -LiteralPath 'C:\Users\Karim\Repositories\property-platform\infra\local\.env.example' -Destination 'C:\Users\Karim\Repositories\property-platform\infra\local\.env'
```

Remplir **le nouveau fichier `.env`** dans l’IDE, jamais dans un message ou un commit. Il est ignoré par Git. Les variables `MEDIA_S3_*` restent côté serveur. Ne pas les préfixer par `NEXT_PUBLIC_`. Ne pas afficher `docker compose config` sans `--quiet` avec de vrais secrets ; Docker inspect et l’accès administrateur au poste peuvent aussi lire les variables des conteneurs. En production, fournir ces valeurs avec le gestionnaire de secrets de l’hébergeur et des rôles séparés.

Vérifier la configuration résolue, sans l’afficher :

```powershell
docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.storage.s3.yaml --profile ingestion config --quiet
```

**Toujours fournir les trois fichiers dans cet ordre pour cette variante.** Le dernier remplace le backend local par S3 pour l’API et l’ingestion ; les fichiers de base restent nécessaires. Utiliser cette même combinaison pour les commandes `up` et `exec` de l’environnement cloud afin de ne pas recréer accidentellement les services avec le backend local.

### 5.3. Raccorder puis essayer un seul fichier

Toutes ces commandes s'exécutent dans **PowerShell**, depuis `C:\Users\Karim\Repositories\property-platform`. Les services locaux décrits dans [DEVELOPMENT.md](DEVELOPMENT.md) doivent être démarrés et leurs migrations appliquées. Avec le code actuel déjà construit, il n'y a pas de dépendance supplémentaire à installer ni de nouvelle migration à lancer pour changer de fournisseur.

```powershell
Set-Location 'C:\Users\Karim\Repositories\property-platform'

docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.storage.s3.yaml --profile ingestion config --quiet

docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.storage.s3.yaml --profile ingestion up -d --no-build --no-deps api ingestion

docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.storage.s3.yaml --profile ingestion exec ingestion python /workspace/apps/api/manage.py check

docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.storage.s3.yaml --profile ingestion exec ingestion python /workspace/apps/api/manage.py archive_property_media --actor Karim --limit 1
```

Exécuter une commande à la fois et attendre son succès. `config --quiet` contrôle l'assemblage sans imprimer les clés. `up` recrée uniquement API et runner avec leurs nouveaux réglages ; les bases, volumes et le web restent en place. `check` vérifie Django mais **ne prouve pas une connexion réseau à R2**. La dernière commande effectue le vrai essai d'écriture à partir d'une photo autorisée déjà acquise ; elle n'effectue aucune publication publique.

Le résultat attendu d'un premier transfert disponible contient `archived: 1` et `published: 0`. Dans Cloudflare, ouvrir le bucket : un objet apparaît sous `objects/sha256/…`. Dans PostgreSQL, `property_platform.evidence.stored_object` contient une copie avec `backend=s3`, `namespace=r2-primary` et le nom du bucket ; `evidence.capture_object` la lie à la capture. Le nom de fichier est son empreinte technique : il n'est pas nécessaire de le renommer. Un résultat `archived: 0` peut simplement signifier qu'il n'y a plus de photo éligible à transférer.

Ouvrir ensuite un bien disposant déjà d'une photo, par exemple Sky Tower, sur le site local : la lecture passe par l'API, qui récupère la copie privée depuis R2. L'absence de `delivery_url` publique est normale. Le web n'a pas besoin d'une clé Cloudflare et ne nécessite pas de nouveau build pour ce changement d'environnement. Les liens PDF/vidéo des promoteurs restent externes : ce premier transfert ne les copie pas automatiquement.

Les prochains runs Prefect d'archivage utiliseront les mêmes réglages R2. Si la création du token, le certificat ou le transfert échoue, arrêter la séquence à cette erreur ; ne pas rendre le bucket public pour contourner une erreur d'autorisation. Pour revenir aux réglages locaux sans effacer les copies R2, recréer API et ingestion avec les deux fichiers de base uniquement ; les fichiers créés exclusivement sur R2 nécessitent toujours leur accès R2 ou une recopie vérifiée.

### 5.4. Transférer les photos restantes

Une fois le premier essai réussi, cette commande traite les photos restantes, par lot de 500 maximum. Les services utilisent déjà la configuration R2 de la section précédente :

```powershell
docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.storage.s3.yaml --profile ingestion up -d --no-build api ingestion
docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.storage.s3.yaml --profile ingestion exec ingestion python /workspace/apps/api/manage.py check
docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.storage.s3.yaml --profile ingestion exec ingestion python /workspace/apps/api/manage.py archive_property_media --actor Karim
```

L’archivage ajoute les copies R2 depuis les captures conservées en SQL. Les liens locaux restent en base, ainsi que le volume local. Une fois une copie R2 présente pour la capture, elle est préférée à la copie locale. Changer un namespace, un bucket ou un fournisseur nécessite de recopier et vérifier les données avant de retirer l’ancien accès. Un changement de variable n’est pas un déplacement automatique des fichiers.

## 6. Autoriser les copies publiques et le CDN

La lecture privée via l’API fonctionne sans bucket public. Pour activer le CDN plus tard : configurer le bucket public distinct, son domaine HTTPS et `MEDIA_PUBLICATION_ENABLED=1`, puis recréer l’API et l’ingestion avec **les trois fichiers** de la section précédente.

Dans Cloudflare, créer ce **deuxième** bucket, par exemple `property-platform-public-media`. Le domaine choisi doit être une zone du même compte Cloudflare. Dans ce bucket : **Settings → Custom Domains → Add**, saisir par exemple `media.ton-domaine.com`, examiner le DNS proposé puis connecter le domaine et attendre son état actif. Cette opération expose les objets de ce bucket : il doit contenir exclusivement les copies autorisées. Le bucket des originaux reste privé. Voir [les étapes officielles de raccordement](https://developers.cloudflare.com/r2/buckets/public-buckets/).

Ajouter ce bucket au périmètre du token d'écriture, puis remplir dans le fichier local :

```dotenv
MEDIA_S3_PUBLIC_BUCKET=property-platform-public-media
MEDIA_PUBLIC_BASE_URL=https://media.ton-domaine.com
MEDIA_PUBLICATION_ENABLED=1
```

Ne pas utiliser littéralement le domaine d'exemple. Le token API de lecture doit rester limité aux originaux. Si le navigateur doit lire des pixels ou effectuer des requêtes JavaScript vers ce domaine, adapter `C:\Users\Karim\Repositories\property-platform\infra\storage\r2-public-cors.json` aux origines réelles du site, puis le renseigner dans les réglages CORS du bucket public. Ne pas ajouter de permission d'écriture publique.

La publication est ensuite une commande séparée, exécutée dans l’ingestion qui dispose du token d’écriture :

```powershell
docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.storage.s3.yaml --profile ingestion exec ingestion python /workspace/apps/api/manage.py archive_property_media --actor Karim --publish
```

Elle ne publie que les JPEG déjà autorisés en base, avec capture et preuve de licence réussies. Elle ne publie pas tous les fichiers d’un bucket et ne rend pas les originaux publics. Le site reçoit `delivery_url` après création de la copie et enregistrement de sa publication. Il utilise le CDN, conserve les crédits et revient au relais API si le chargement CDN échoue. Les URL publiques ne contiennent aucune signature secrète.

Les URL présignées privées R2, si une future fonctionnalité en a besoin, doivent utiliser l’endpoint S3 et une autorisation serveur ; elles ne fonctionnent pas sur le domaine CDN personnalisé. Aucun endpoint anonyme de signature ou de téléversement arbitraire n’est ajouté ici.

**Retrait d’un média :** désactiver son `display_allowed` bloque les nouvelles réponses API et retire son URL CDN des fiches. Une copie déjà publique reste accessible par son URL connue, éventuellement en cache pendant 24 heures. Pour un retrait complet, supprimer explicitement cette copie dans le bucket public et purger son URL dans Cloudflare. Ne pas supprimer le fichier privé ni la preuve de licence. Les clés publiques contiennent l’UUID du média afin de ne pas confondre plusieurs publications de la même photographie.

## 7. Intégrité, reprise et limites

Les clés privées sont dérivées du contenu : `objects/sha256/ab/<sha256>.<extension>`. Une nouvelle version produit une nouvelle clé. Le disque utilise une publication atomique sans remplacement ; R2/S3 utilise `If-None-Match: *`. Un fichier existant doit correspondre au SHA-256 et à la taille attendus. **L’ETag S3 n’est pas assimilé au SHA-256.** Une réponse réseau perdue peut être rejouée ; si l’écriture précédente existe, son contenu est vérifié avant réutilisation.

Un échec SQL après une écriture peut laisser un fichier sans lien SQL. La reprise retrouve le même contenu et crée le lien manquant. Ne pas faire de suppression automatique des objets sans lien : vérifier l’absence de jobs en cours, garder un délai de rétention et examiner les preuves avant un nettoyage. Une copie publique créée juste avant une perte d’approbation doit être retirée manuellement ; elle ne sera pas annoncée par l’API.

Les flux d’entrée sont bornés à **128 Mio par fichier** et utilisent un fichier temporaire au-delà de 1 Mio. La route photo actuelle reste limitée à **2 Mio et JPEG**. Ces seuils sont des budgets de cette première intégration, pas une promesse de streaming vidéo adaptatif. HLS, miniatures, antivirus, OCR, transcodage et génération 3D nécessiteront des jobs isolés, leurs budgets et leurs modèles de dérivation. Vérifier une signature de fichier ne remplace pas une analyse antivirus ou la validation approfondie d’un PDF/vidéo.

Les téléchargements et écritures ne s’exécutent pas dans une longue transaction SQL. Une copie archivée manquante ou corrompue produit une indisponibilité explicite ; l’API ne cache pas ce problème en revenant silencieusement au payload SQL. La lecture SQL reste compatible pour les captures qui n’ont pas encore été archivées.

## 8. Sauvegarder et vérifier

Sauvegarder **PostgreSQL et les objets** : un dump SQL seul ne contient pas le nouveau volume. Prévoir un inventaire des clés et SHA-256, une copie indépendante du stockage, une politique de rétention et un essai de restauration. R2 est un stockage principal ; ce n’est pas à lui seul une sauvegarde indépendante. Conserver le namespace et le mapping bucket/domaine avec la procédure de restauration, sans y écrire les secrets.

Le volume local peut être exporté depuis Docker Desktop → Volumes → `property-platform-local_media-data` → Exports, en conservant aussi le dump PostgreSQL correspondant. Pour une sauvegarde cohérente, suspendre les imports et les publications pendant l’export, puis les reprendre. Ne pas éditer les fichiers binaires du volume à la main.

Les tests API couvrent les formats autorisés, tailles, clés, intégrité, écritures immuables, échec/reprise, licence, refus d’écriture dans une transaction, schémas SQL et exposition conditionnelle de l’URL CDN. Le protocole du SDK S3 est testé avec le stub officiel botocore, sans clé cloud ni facture. La CI vérifie aussi les deux variantes Compose, les contrats et le build web. Un essai réel de lecture/écriture sur **ton** compte R2, la configuration du domaine et les droits des tokens restent à effectuer au moment de l’activation.

## Sources techniques

Validation locale du **15 octobre 2026** : migration `0018` appliquée après sauvegarde SQL privée ; 6 captures liées à un seul fichier local de **160 006 octets**, zéro copie publique ; deuxième archivage sans doublon. Le run Prefect `7ed2efdb-5df8-4244-a16e-0f84714360c5` du nouveau déploiement est terminé avec succès. Les contrôles comprennent 290 tests API/PostGIS, 88 tests ingestion, 25 tests web, contrats générés et build standalone sur quinze langues. Ces résultats ne constituent pas une validation d’un compte R2 réel.

- [R2 et compatibilité S3](https://developers.cloudflare.com/r2/api/s3/api/), [écritures conditionnelles R2](https://developers.cloudflare.com/r2/api/s3/extensions/).
- [Domaine personnalisé et bucket public](https://developers.cloudflare.com/r2/buckets/public-buckets/), [configuration CORS](https://developers.cloudflare.com/r2/buckets/cors/).
- [URL présignées et limites de domaine](https://developers.cloudflare.com/r2/api/s3/presigned-urls/).
- [SDK boto3 sur PyPI](https://pypi.org/project/boto3/1.43.114/), [stub officiel botocore](https://botocore.amazonaws.com/v1/documentation/api/latest/reference/stubber.html).
- [Configuration et certificats du SDK boto3](https://docs.aws.amazon.com/boto3/latest/guide/configuration.html).
- [Tarification et quotas R2 à vérifier lors de l’activation](https://developers.cloudflare.com/r2/pricing/).
