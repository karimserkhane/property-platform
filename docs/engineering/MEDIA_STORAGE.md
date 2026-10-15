# Fichiers, R2/S3 et CDN

Le dépôt sait archiver les photographies acquises dans un stockage de fichiers persistant, puis les lire depuis l’API. Le même adaptateur accepte PDF, JPEG, PNG, WebP, MP4, WebM et GLB. **Le parcours actuellement raccordé au site reste celui des photographies de biens déjà autorisées.** Ajouter des brochures, vidéos ou modèles nécessite encore leur collecteur, leurs droits et une interface adaptée ; cette fondation ne les collecte ni ne les génère automatiquement.

En développement, les fichiers sont dans un volume Docker sur ton PC. Pour la future mise en ligne, le même code peut utiliser **Cloudflare R2**, par son API compatible S3. Un second bucket peut recevoir les seules photos autorisées pour une diffusion publique par un domaine CDN. Aucun compte, abonnement, bucket ni domaine n’est créé par les commandes locales.

## 1. Le rôle de chaque composant

| Composant | Contenu et rôle |
|---|---|
| PostgreSQL/PostGIS | Identités des biens, sources, captures, licences, dates, SHA-256, tailles et références des fichiers |
| Stockage privé local ou R2 | Octets des fichiers archivés ; noms techniques immuables calculés depuis leur SHA-256 |
| Bucket public R2 distinct, facultatif | Copies des photos explicitement approuvées pour être publiées |
| Domaine CDN, facultatif | Distribution des copies publiques depuis `https://media.ton-domaine…` |
| Django | Vérification de provenance, contrôles d’autorisation et enregistrement des références |
| Prefect | Déclenchement, supervision et reprise de l’archivage après l’import |
| Next.js | Affichage depuis le CDN lorsque la copie publique existe ; sinon lecture via l’API locale |

Les photographies décoratives de l’accueil, leurs variantes optimisées, les polices et leurs licences restent des ressources versionnées du site. Leur petite taille et leur cycle de publication ne justifient pas un déplacement automatique. Les reçus de collecte Prefect restent dans leur volume privé séparé `/data`.

**Compatibilité avec les preuves existantes :** `evidence.capture.payload` est conservé. Les petites captures historiques gardent leurs octets SQL et leurs dates ; l’archivage crée une copie vérifiée et ses liens. Cette étape ne prétend donc pas avoir supprimé tous les binaires de PostgreSQL. Une acquisition future de gros documents devra faire évoluer explicitement la représentation des captures avant de stocker uniquement leurs métadonnées en SQL. Ne pas remplacer un payload par une chaîne vide.

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

Source originale, date de récupération, date de publication connue, date d’ingestion, exécution de collecte et licence restent accessibles par les relations `capture`, `property_media` et `licence_capture`. Les octets, clés privées et noms des opérateurs ne sont pas ajoutés au contrat public des fiches. Le seul champ supplémentaire est `delivery_url`, nul tant qu’une copie publique approuvée n’existe pas.

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

Le fournisseur est interchangeable grâce au protocole S3 ; la configuration R2 est : endpoint HTTPS du compte et région **`auto`**. Le SDK officiel boto3 est verrouillé dans les deux environnements Python. Les clés sont fournies explicitement : le code ne cherche pas de profil AWS sur ton PC.

Les images API et ingestion fixent `AWS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt` : le SDK utilise le magasin Debian vérifié, y compris l’éventuelle autorité publique supplémentaire déjà approuvée pour les builds. Le SDK garde la vérification TLS active. Pour un SDK exécuté directement sur Windows derrière une inspection HTTPS, configurer au besoin `AWS_CA_BUNDLE` avec un bundle public vérifié ; ne jamais désactiver TLS pour contourner une erreur de certificat. Voir [TOOLCHAIN.md](TOOLCHAIN.md).

Le jour où tu actives ton compte Cloudflare, préparer dans R2 :

1. Un bucket **privé** pour les originaux, sans domaine public ni accès `r2.dev`.
2. Un token limité aux buckets requis pour l’ingestion, avec lecture et écriture. Un token distinct de lecture seule peut servir à l’API ; il doit pouvoir lire les originaux de son bucket.
3. Facultativement, un **second** bucket destiné aux seules copies publiques et un domaine personnalisé tel que `media.ton-site.com`. Le CDN se raccorde à ce domaine. Garder `MEDIA_PUBLICATION_ENABLED=0` pendant les premiers essais privés.
4. Adapter l’exemple CORS au vrai domaine du site si des lectures JavaScript ou exports canvas le demandent : GET/HEAD, sans téléversement public ni origines universelles. La lecture d’une image par une balise `<img>` ne nécessite pas à elle seule de CORS.

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

Après avoir vérifié compte, autorisations, quotas et budget, le démarrage explicite se fait avec :

```powershell
docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.storage.s3.yaml --profile ingestion up -d --no-build api ingestion
docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.storage.s3.yaml --profile ingestion exec ingestion python /workspace/apps/api/manage.py check
docker compose --env-file infra/local/.env -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml -f infra/local/compose.storage.s3.yaml --profile ingestion exec ingestion python /workspace/apps/api/manage.py archive_property_media --actor Karim
```

L’archivage ajoute les copies R2 depuis les captures conservées en SQL. Les liens locaux restent en base, ainsi que le volume local. Une fois une copie R2 présente pour la capture, elle est préférée à la copie locale. Changer un namespace, un bucket ou un fournisseur nécessite de recopier et vérifier les données avant de retirer l’ancien accès. Un changement de variable n’est pas un déplacement automatique des fichiers.

## 6. Autoriser les copies publiques et le CDN

La lecture privée via l’API fonctionne sans bucket public. Pour activer le CDN plus tard : configurer le bucket public distinct, son domaine HTTPS et `MEDIA_PUBLICATION_ENABLED=1`, puis recréer l’API et l’ingestion avec **les trois fichiers** de la section précédente.

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
