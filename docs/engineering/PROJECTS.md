# Fiches projets, documents et vidéos

Extension du 15 octobre 2026. Le catalogue distingue maintenant **promoteur → projet → liens vers bâtiments, repères ou parcelles**. Une page de projet rassemble les faits extraits de pages officielles, leurs preuves, documents et vidéos. Les unités effectivement disponibles, prix commerciaux et échéanciers restent un prochain lot : le nombre de logements d'un programme n'est pas un stock disponible.

**Vérification locale du 15 octobre :** les deux runs Prefect ont terminé avec succès : [Reportage](http://localhost:4200/runs/flow-run/2785aaa6-122d-4248-a27a-6f824fa69994) et [Bloom](http://localhost:4200/runs/flow-run/59a57983-a7a5-49ae-90d1-269fcb41d207). La base contient 2 promoteurs, 3 projets, 4 snapshots, 5 liens d'identité actifs, 17 typologies, 20 équipements, 7 références PDF et 1 référence vidéo. Ce sont des observations sourcées ; aucun fichier de promoteur n'a été copié ou approuvé pour republication. Les 22 calendriers locaux préexistants ont été conservés. Les trois nouveaux déploiements restent manuels.

## 1. Essayer les premières fiches

Après installation et import, ouvrir :

- [The District](http://localhost:3102/fr/projects/the-district), Reportage, Al Reem.
- [Vista 3](http://localhost:3102/fr/projects/vista-3), Reportage, Al Reem.
- [Park View](http://localhost:3102/fr/projects/park-view), Bloom, Saadiyat.

La carte propose aussi un lien vers le projet dans les fiches des objets explicitement rapprochés. Le quartier ou la proximité d'une parcelle ne suffisent pas à attribuer un bâtiment au promoteur. Les quinze langues disposent des textes d'interface ; les textes de preuve restent dans leur langue originale.

## 2. Ce que les pipelines collectent

Les collecteurs ne contactent que les URL examinées du registre. Ils enregistrent les pages HTML et conditions d'utilisation, contrôlent les réponses, puis extraient des champs typés. Les originaux conservent leur empreinte, heure de récupération, heure d'ingestion et, lorsqu'elle est connue, date de publication. Aucune date de publication n'est déduite de l'heure de téléchargement.

| Déploiement Prefect | Portée et résultat | Démarrage initial |
|---|---|---|
| `project-details` | Pages Reportage de The District et Vista 3, livraison annoncée si présente, typologies, équipements, liens PDF | Manuel |
| `saadiyat-project-details` | Page Bloom de Park View, typologies, équipements, brochure et lien vidéo officiel | Manuel |
| `project-media-files` | Fichiers explicitement fournis par l'opérateur, décrits dans un manifeste privé | Manuel |

Les horaires déjà configurés des autres imports sont conservés. Pour ces nouveaux jobs, commencer dans [Prefect](http://localhost:4200) → Deployments → nom du déploiement → Run → paramètre `actor: Karim`. Le PC, Docker et le runner doivent être allumés. Un redémarrage n'exécute pas automatiquement tous les imports.

Le premier parcours est **pages → reçus privés → validation Django → snapshots SQL → API → site**. Une relance de la même exécution réutilise son reçu ; une nouvelle collecte produit une observation datée. Les snapshots historiques sont conservés. Les rapprochements d'identité sont explicites, audités et révocables. Une réponse manquante ou un format modifié fait échouer la collecte : aucune disponibilité ou date n'est inventée.

Les conditions officielles de [Reportage](https://reportagegroup.com/terms/) et de [Bloom](https://bloomholding.com/terms-of-use) ne constituent pas une autorisation générale de republier leurs médias. Le registre marque ces acquisitions comme recherche locale et les fichiers comme **références externes**. Le pipeline ne télécharge pas leurs PDF, photos ou vidéos. Park View renvoie vers la vidéo officielle Vimeo ; aucune iframe, lecture automatique ou URL temporaire signée n'est conservée. Les prix et disponibilités contradictoires du site Bloom ne sont pas importés comme offres.

## 3. Installer les changements sans effacer la base

Ouvrir **PowerShell**, puis exécuter les commandes une par une depuis la racine. Pour une base existante, réaliser d'abord la sauvegarde décrite dans [DATABASE_DESIGN.md](DATABASE_DESIGN.md). Les commandes ne créent ni compte cloud ni bucket.

```powershell
Set-Location 'C:\Users\Karim\Repositories\property-platform'

docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml stop ingestion

docker compose -f infra/local/compose.yaml build api

docker compose -f infra/local/compose.yaml up -d --no-build api

docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput

docker compose -f infra/local/compose.yaml exec api python manage.py check

docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion build ingestion

docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion up -d --no-build ingestion

docker compose -f infra/local/compose.yaml --profile web-preview build web

docker compose -f infra/local/compose.yaml --profile web-preview up -d --no-build web
```

`stop ingestion` suspend le runner pendant l'évolution SQL. `build` copie le nouveau code dans son image. `migrate` crée les nouvelles tables et contraintes, sans collecter les projets. Les deux runs Prefect de la section 2 alimentent ensuite la base. Le web Docker sur **3102** nécessite son propre build ; pour le web de développement sur **3000**, utiliser `pnpm.cmd dev:web` à la place des deux dernières commandes. Arrêter à la première erreur. Les volumes sont réutilisés ; ne pas lancer `down -v`.

## 4. Où sont les données ?

Dans l'outil SQL, sélectionner la base `property_platform` :

| Table | Contenu |
|---|---|
| `property_platform.real_estate.developer` | Identité stable du promoteur et site officiel |
| `property_platform.real_estate.project` | Identité stable du projet, territoire, promoteur et URL officielle |
| `property_platform.evidence.project_identity_link` | Rapprochement examiné vers un bâtiment, lieu ou parcelle ; preuve et révocation |
| `property_platform.evidence.project_snapshot` | Faits datés, résumé, livraison avec précision année/trimestre/mois/jour, total du programme et pointeurs de preuve |
| `property_platform.evidence.project_typology` | Types de logements et nombre de chambres documentés |
| `property_platform.evidence.project_amenity` | Équipements cités, texte original et preuve |
| `property_platform.evidence.project_media` | Référence d'image, PDF, vidéo ou modèle ; rôle, MIME, URL source, auteur, droits et captures associées |
| `property_platform.evidence.project_media_publication` | Copie publique explicitement publiée après approbation |
| `property_platform.evidence.capture` | Source, run, dates, SHA-256 et contenu inline **ou** objet principal externe |
| `property_platform.evidence.stored_object` / `capture_object` | Localisation physique immuable et liens vers les captures |

Les migrations additives sont `catalog/0006`, `evidence/0019` puis `evidence/0020`, sous `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\`. Les anciennes tables et leurs preuves restent présentes.

Une capture contient exactement une représentation principale : `payload` SQL non nul, ou `primary_object_id` non nul. Les anciennes petites captures restent inline. Un fichier opérateur reçoit `payload=NULL`, son objet principal et un `http_status=NULL` : il ne prétend pas être une réponse HTTP. Son horodatage de fichier est conservé avec `timestamp_basis=artifact_filesystem_time`. Le moment d'ingestion et le run sont distincts.

## 5. Ajouter un fichier dont les droits sont disponibles

Formats acceptés : JPEG, PNG, WebP, PDF, MP4, WebM et GLB, **128 MiB maximum par fichier**. La signature du format, taille et SHA-256 sont vérifiés. Les contenus HTML actifs, playlists et URLs arbitraires ne sont pas des fichiers acceptés. Une page Vimeo `text/html` reste un lien ; elle n'est pas convertie en MP4.

Cette procédure attache un fichier à une référence binaire existante dans `evidence.project_media`. Elle ne crée pas automatiquement une référence pour n'importe quel fichier trouvé sur Internet. Relever son UUID dans l'outil SQL. Pour une nouvelle catégorie ou source, ajouter d'abord une référence examinée et son extracteur. Ne pas modifier directement les droits en SQL.

**Option commande Django**, pour un fichier disponible sur le poste : remplacer les valeurs d'exemple par le fichier réel et l'UUID correspondant.

```powershell
docker compose -f infra/local/compose.yaml cp 'C:\Users\Karim\Downloads\fichier-autorise.mp4' api:/tmp/fichier-autorise.mp4

docker compose -f infra/local/compose.yaml exec api python manage.py attach_project_media --media-id UUID_DU_MEDIA --file /tmp/fichier-autorise.mp4 --actor Karim
```

Le fichier est archivé dans `/media`, volume privé partagé avec le runner ; sa référence et sa preuve d'acquisition sont enregistrées en SQL. Il n'est pas encore affichable par l'API. Relancer le même fichier ne crée pas une seconde capture ; un fichier différent sur cette référence est refusé et exige une nouvelle révision examinée.

**Option Prefect**, pour plusieurs fichiers : créer `C:\Users\Karim\Downloads\project-media.json` contenant, par exemple :

```json
[{"media_id":"UUID_DU_MEDIA","filename":"fichier-autorise.mp4"}]
```

Remplacer l'UUID par une valeur réelle avant exécution. Le manifeste accepte 1 à 20 entrées et 64 KiB maximum. Copier les fichiers dans le dossier privé du runner :

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml exec ingestion mkdir -p /data/media

docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml cp 'C:\Users\Karim\Downloads\fichier-autorise.mp4' ingestion:/data/media/fichier-autorise.mp4

docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml cp 'C:\Users\Karim\Downloads\project-media.json' ingestion:/data/project-media.json
```

Dans Prefect, lancer **project-media-files** avec `receipt_name: project-media.json` et `actor: Karim`. Le manifeste n'accepte pas de chemin absolu, URL ou traversée de dossier. Chaque fichier est enregistré séparément ; en cas d'interruption, un run peut avoir traité une partie du lot. Une relance reprend sans dupliquer les fichiers identiques. Ce job n'attribue aucun droit et ne publie rien.

## 6. Approbation et affichage

Un opérateur doit examiner une preuve distincte donnant le droit de diffuser le fichier. Une page de conditions restrictives ou le fichier lui-même ne suffisent pas. La commande `approve_project_media` exige l'UUID de cette capture, l'auteur, la licence et sa référence HTTPS :

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py approve_project_media --media-id UUID_DU_MEDIA --rights-capture-id UUID_PREUVE_DROITS --actor Karim --author 'Auteur réel' --licence-code explicit_permission --licence-url 'https://exemple.org/autorisation-reelle'
```

Ce sont des **paramètres d'exemple**, pas une autorisation existante. Le code vérifie les états et enregistre la décision ; il ne peut pas lire à la place de l'opérateur la portée juridique d'une permission. Les médias Reportage/Bloom ne sont pas approuvés par défaut.

Après approbation, le site utilise le relais fixe `/api/atlas/project-media/<UUID>` vers Django. L'API recontrôle les preuves et refuse les médias non approuvés ou bloqués. GET/HEAD et une seule plage HTTP `Range` sont pris en charge : **206** pour une plage, **416** si elle est invalide, `If-Range` pour éviter une reprise sur un autre contenu. Les transferts restent bornés et privés, sans mise en cache publique. PDF/GLB sont proposés en téléchargement ; les vidéos MP4/WebM approuvées utilisent les contrôles du navigateur, `preload=none`, sans autoplay. Les images approuvées peuvent être affichées. La compatibilité réelle des codecs dépend du navigateur ; aucun transcodage, HLS, miniature vidéo ou génération IA n'est ajouté au serveur web/API.

R2/S3 est une option décrite dans [MEDIA_STORAGE.md](MEDIA_STORAGE.md). Après configuration explicite d'un bucket public séparé et d'un domaine CDN, `publish_project_media --media-id UUID_DU_MEDIA --actor Karim` publie une copie déjà approuvée. La configuration seule ne copie rien. Une révocation dans la base coupe le relais privé et retire l'URL des nouvelles réponses ; une copie déjà publique doit aussi être supprimée du bucket et du cache CDN par l'opérateur.

Références techniques : [Django — StreamingHttpResponse](https://docs.djangoproject.com/en/6.1/ref/request-response/#streaminghttpresponse-objects), [HTTP Range](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Range_requests), [R2 — compatibilité S3](https://developers.cloudflare.com/r2/api/s3/api/).

## 7. Retrouver le code et valider

Tous les chemins commencent par `C:\Users\Karim\Repositories\property-platform\` :

- `apps\api\src\property_platform\modules\catalog\project_services.py` : identités stables.
- `apps\api\src\property_platform\modules\evidence\project_registry.json` : sources examinées, parseurs et rapprochements autorisés.
- `apps\api\src\property_platform\modules\evidence\project_protocol.py` : extraction et validation sans écriture SQL.
- `apps\api\src\property_platform\modules\evidence\project_import.py` : snapshots, transaction, idempotence et audit.
- `apps\api\src\property_platform\modules\evidence\project_queries.py` : projection bornée de l'observation courante par URL.
- `apps\api\src\property_platform\modules\evidence\project_media_storage.py` : attachement privé, revue et publication explicite.
- `apps\api\src\property_platform\object_storage\downloads.py` : flux local/S3 et plages d'octets, sans dépendance Django.
- `apps\api\src\property_platform\api\projects.py` et `project_media.py` : contrats et routes locales protégées.
- `apps\ingestion\src\property_platform_ingestion\collectors\projects.py` : acquisition HTTPS bornée avant transaction SQL.
- `apps\ingestion\src\property_platform_ingestion\media_files.py` : manifeste privé des fichiers opérateur.
- `apps\web\src\features\projects\` : fiche responsive, preuves, médias et erreurs traduites.
- `apps\web\src\app\api\atlas\project-media\[id]\route.ts` : relais par flux à destination fixe ; taille et délais bornés.

Les tests backend GIS s'exécutent sur une **base PostGIS de test**, jamais avec un `truncate` de la base métier. Après imports et reconstruction du web, cette commande vérifie les trois fiches en anglais, français et arabe :

```powershell
node scripts/smoke-projects.mjs
```

Les tests de fichiers utilisent des fixtures isolées : aucun faux média ou faux droit n'est ajouté aux projets de la vraie base. Les tests S3 utilisent des réponses SDK simulées ; ils ne certifient pas la connexion à un compte R2 réel tant qu'il n'est pas configuré.
