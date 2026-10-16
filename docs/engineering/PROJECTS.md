# Fiches projets, documents et vidéos

[Essayer les fiches](#1-essayer-les-premières-fiches) · [Pipelines](#2-ce-que-les-pipelines-collectent) · [Installer](#3-installer-les-changements-sans-effacer-la-base) · [Tables](#4-où-sont-les-données-) · [Couverture des deux îles](#8-extension-reem-et-saadiyat--16-octobre-2026)

Extension du 15 octobre 2026. Le catalogue distingue maintenant **promoteur → projet → liens vers bâtiments, repères ou parcelles**. Une page de projet rassemble les faits extraits de pages officielles, leurs preuves, documents et vidéos. Les unités effectivement disponibles, prix commerciaux et échéanciers restent un prochain lot : le nombre de logements d'un programme n'est pas un stock disponible.

**Historique de validation du 15 octobre :** les premiers runs [Reportage](http://localhost:4200/runs/flow-run/2785aaa6-122d-4248-a27a-6f824fa69994) et [Bloom](http://localhost:4200/runs/flow-run/59a57983-a7a5-49ae-90d1-269fcb41d207) avaient alimenté 3 projets. L'extension aux deux îles et les nouveaux catalogues sont décrits dans [la section 8](#8-extension-reem-et-saadiyat--16-octobre-2026). Aucun fichier de promoteur n'est approuvé pour republication par ces collectes.

## 1. Essayer les premières fiches

Après installation et import, ouvrir :

- [The District](http://localhost:3102/fr/projects/the-district), Reportage, Al Reem.
- [Vista 3](http://localhost:3102/fr/projects/vista-3), Reportage, Al Reem.
- [Park View](http://localhost:3102/fr/projects/park-view), Bloom, Saadiyat.

La sélection d'un objet explicitement rapproché ouvre le **dossier immobilier complet dans le panneau de la carte** : projet et promoteur, livraison, programme, typologies, équipements, médias, documents, informations d'achat et preuves. L'annuaire ouvre le même parcours avec `explore?territory=…&project=…`. Sur téléphone, la fiche est agrandissable ; la sélection ne déclenche pas de zoom. Une page indépendante reste partageable. Les bâtiments sans fiche structurée gardent leur présentation existante ; le quartier ou la proximité d'une parcelle ne suffisent pas à attribuer un bâtiment au promoteur. Un dossier sans rapprochement cartographique s'ouvre à l'échelle du quartier et ne crée aucun point.

La fiche complète organise les informations en présentation, logements, équipements, médias, documents et localisation. Les informations d'achat sont regroupées à part : prix, surfaces, charges, disponibilités et échéanciers indiquent explicitement leur absence tant qu'aucune donnée typée n'est collectée. Un total de logements ne devient jamais un nombre d'unités disponibles. Les preuves et dates restent accessibles dans des volets dépliables.

Le panneau utilise le relais serveur borné `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\api\atlas\projects\[slug]\route.ts`, puis le même contrat Django que la page. Il n'accepte ni URL distante fournie par le visiteur ni paramètre de requête. Les requêtes sont annulées à chaque changement de sélection ; un résultat précédent ne s'affiche pas sous le nom d'un autre projet. Un échec offre une relance et conserve le lien vers la fiche. Toutes les langues du registre disposent des textes d'interface ; les textes de preuve restent dans leur langue originale.

`features/projects/map-dossier.tsx` possède le panneau client et ses raccourcis internes ; `detail.tsx` possède la présentation partagée entre page et variante cartographique, et `cover.tsx` la couverture réutilisable. La sélection partagée de médias dans `presentation.ts` n'intègre que des images stockées avec droits approuvés. Sans image autorisée, une couverture typographique donne accès à la galerie officielle ; elle n'utilise ni image du concurrent, ni photo d'un autre bâtiment, ni rendu inventé. Les références PDF et vidéo restent ouvrables chez leur éditeur. Cette refonte de présentation ne modifie ni les tables ni les pipelines et ne nécessite pas de migration.

## 2. Ce que les pipelines collectent

Les collecteurs ne contactent que les URL examinées du registre. Ils enregistrent les pages HTML et conditions d'utilisation, contrôlent les réponses, puis extraient des champs typés. Les originaux conservent leur empreinte, heure de récupération, heure d'ingestion et, lorsqu'elle est connue, date de publication. Aucune date de publication n'est déduite de l'heure de téléchargement.

| Déploiement Prefect | Portée et résultat | Démarrage initial |
|---|---|---|
| `project-details` | 30 projets/programmes examinés à Reem ; une tâche indépendante par projet | Samedi 02:00, initialement désactivé |
| `saadiyat-project-details` | 27 projets/programmes examinés à Saadiyat ; une tâche indépendante par projet | Samedi 03:00, initialement désactivé |
| `reem-project-discovery` | Catalogues officiels : nouveaux liens en attente de revue, pas de création de bien | Samedi 04:00, initialement désactivé |
| `saadiyat-project-discovery` | Catalogues officiels Saadiyat, captures et candidats | Samedi 04:30, initialement désactivé |
| `project-media-files` | Fichiers explicitement fournis par l'opérateur, décrits dans un manifeste privé | Manuel |

Les horaires utilisent **Asia/Dubai**. Les horaires déjà configurés des autres imports sont conservés, y compris un calendrier volontairement supprimé. Dans [Prefect](http://localhost:4200), ouvrir Deployments → nom du déploiement → Run → paramètre `actor: Karim`. Le PC, Docker et le runner doivent être allumés. Un redémarrage n'exécute pas automatiquement tous les imports. Sur une nouvelle installation, activer les calendriers souhaités après une exécution réussie ; le job de fichiers reste manuel.

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
| `property_platform.evidence.project_source_candidate` | Liens observés dans les catalogues officiels : capture, éditeur, périmètre de collecte, titre, URL/empreinte, statut, projet reconnu ou revue en attente |
| `property_platform.evidence.capture` | Source, run, dates, SHA-256 et contenu inline **ou** objet principal externe |
| `property_platform.evidence.stored_object` / `capture_object` | Localisation physique immuable et liens vers les captures |

Les migrations additives sont `catalog/0006`, `evidence/0019`, `evidence/0020` puis `evidence/0021`, sous `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\`. La dernière ajoute les candidats et autorise l'opération d'orchestration correspondante ; elle ne collecte rien. Les anciennes tables et leurs preuves restent présentes.

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

Les tests backend GIS s'exécutent sur une **base PostGIS de test**, jamais avec un `truncate` de la base métier. Après imports et reconstruction du web, cette commande vérifie toutes les fiches du registre et l’annuaire en anglais, français et arabe :

```powershell
node scripts/smoke-projects.mjs
```

Les tests de fichiers utilisent des fixtures isolées : aucun faux média ou faux droit n'est ajouté aux projets de la vraie base. Les tests S3 utilisent des réponses SDK simulées ; ils ne certifient pas la connexion à un compte R2 réel tant qu'il n'est pas configuré.


## 8. Extension Reem et Saadiyat — 16 octobre 2026

**Validation locale terminée :** les quatre runs [fiches Reem](http://localhost:4200/runs/flow-run/52a47d25-9a22-4a88-b11e-19b65a3e41d7), [fiches Saadiyat](http://localhost:4200/runs/flow-run/59175f17-6f47-4a16-8a43-dc3b6840a6de), [catalogues Reem](http://localhost:4200/runs/flow-run/01acdd1f-1cef-4d2b-b965-cd584d2cba80) et [catalogues Saadiyat](http://localhost:4200/runs/flow-run/07a22a66-d254-48db-9892-e72c6aecf2ab) sont `Completed`. La migration `evidence/0021` est appliquée après sauvegarde vérifiée. API, runner et web compilé sur 3102 utilisent cette extension.

L'audit SQL/API donne **57 projets, 10 promoteurs et 83 snapshots historiques**. Les fiches courantes exposent une livraison annoncée pour 24 projets, un total de programme pour 39, 120 observations de typologie, 23 équipements et 28 références médias (27 PDF, 1 vidéo). Aucun de ces médias n'est approuvé pour copie ou republication. Les 5 liens d'identité actifs préexistants sont conservés. Les catalogues ont produit **119 observations de liens**, dont 49 rapprochées d'une URL examinée et **70 en attente de revue** ; ce ne sont pas 70 nouveaux projets confirmés.

Sur ce poste, les quatre calendriers du samedi sont **activés**, conformément à la demande de mise à jour le week-end. Les 22 calendriers actifs préexistants sont conservés : 26 sont actifs au total sur 32 déploiements. Le PC, Docker et le runner doivent rester allumés. Les valeurs initiales désactivées décrites plus bas concernent une nouvelle installation.

Vérifications : **332 tests backend sur PostGIS**, **120 tests ingestion** (2 scénarios d'intégration conditionnels ignorés), **36 tests web**, règles d'import, lint/format, contrats OpenAPI et liens documentaires. La compilation et ses contrôles couvrent les 15 langues ; `smoke-projects.mjs` vérifie les 57 fiches et l'annuaire en anglais/français/arabe sur les données réelles. Reem Nine et le filtre Saadiyat ont aussi été vérifiés dans le navigateur, avec un contrôle mobile arabe/RTL. Les tests ne certifient pas l'exhaustivité des sources ou la véracité des annonces des promoteurs.

L’[annuaire des projets](http://localhost:3102/fr/projects) permet d’ouvrir chaque fiche et de filtrer Reem ou Saadiyat. Le bouton **Voir les projets** de la carte y donne accès. Il lit PostgreSQL via Django : aucune collecte distante n’est déclenchée par un clic.

Le registre examiné contient **57 projets/programmes : 30 à Reem, 27 à Saadiyat**, chez **10 promoteurs**. Il n’est pas un recensement exhaustif de tous les bâtiments des deux îles. Certains programmes regroupent plusieurs bâtiments ou phases ; leurs totaux ne doivent pas être additionnés comme un stock disponible.

| Éditeur officiel | Fiches examinées | Source de départ |
|---|---:|---|
| Aldar | 25 | [Catalogue officiel](https://www.aldar.com/properties/en/communities), API publique vente et location |
| SAAS | 7 | [Propriétés](https://www.saasproperties.com/en/properties/) |
| Radiant | 8 | [Développements](https://radiantrealestate.ae/developments/) |
| Modon | 4 | [Immobilier](https://www.modon.com/real-estate) et communiqué officiel Maysan |
| IMKAN | 4 | [Projets](https://imkan.ae/projects) |
| Reportage | 4 | [Catalogue](https://reportagegroup.com/project-listing/) |
| Bloom | 2 | [Site officiel](https://bloomholding.com/) |
| MERED | 1 | [Riviera](https://mered.ae/projects/riviera) |
| Object 1 | 1 | [A1LA](https://object-1.com/project/a1la-residence/) |
| NORD | 1 | [Henge](https://nord.ae/projects/henge-residences/) |

Les champs diffèrent selon la source : nom, promoteur, lien officiel et preuve ; puis, lorsqu’ils sont explicitement extractibles, résumé, livraison annoncée, total du programme, typologies et liens documentaires. Une fiche sans équipements ou nombre de chambres documentés ne reçoit pas de valeurs inventées. Les listes de types et de chambres indépendantes d’Aldar ne sont pas croisées pour inventer des combinaisons. Les prix, unités disponibles, rendements et plans de paiement ne sont toujours pas collectés par ces jobs.

**Actualisation des liens :** chaque nouvelle exécution reconsulte les pages autorisées et observe leurs liens PDF/vidéo sûrs. Les nouveaux liens restent `reference_only`, sur les hôtes examinés, sans téléchargement des fichiers ni approbation de republication. Les liens temporaires signés et les contenus de pied de page/projets associés sont écartés. La page officielle Marlin 1 renvoie à des PDF Marlin 2 : ils ne sont pas attribués à Marlin 1. Une nouvelle URL ou identité ambiguë exige une revue du registre.

**Découverte :** 13 catalogues officiels sont acquis par les deux nouveaux flows. Une URL déjà examinée peut référencer un projet existant ; une nouvelle URL reste `pending_review` dans `evidence.project_source_candidate`. Un catalogue peut contenir d’autres quartiers : `territory_scope` est le périmètre demandé à la collecte, pas une localisation acceptée. Le pipeline ne suit pas les URL candidates, ne crée pas automatiquement de projet, ne fusionne pas les noms et ne place aucun repère cartographique. Un opérateur doit vérifier l’identité, la zone, les droits et l’extracteur, puis enrichir le registre avant l’import suivant.

**Reprise et isolation :** chaque tâche utilise une portée `territory:slug` ou `territory:catalogue`. Si une source échoue, les autres tâches continuent ; le flow finit en échec avec la liste des éléments concernés. Les observations réussies restent enregistrées. Relancer la même exécution conserve ses reçus privés et son identité ; une nouvelle exécution crée une observation datée. Il n’y a pas de `truncate and load`.

Les rapprochements cartographiques existants sont conservés. Les nouvelles fiches sans identité géographique examinée restent accessibles dans l’annuaire avec la mention de localisation à vérifier. Leur lien de carte ouvre le territoire, sans prétendre pointer le projet. Une égalité de nom ou une proximité n’est pas une preuve suffisante de parcelle ou de bâtiment.

Pour une autre installation, suivre la section 3, y compris `migrate` pour `evidence/0021`, puis lancer **project-details**, **saadiyat-project-details**, puis les deux jobs **project-discovery** dans Prefect. Attendre la fin de chaque run et vérifier ses journaux. Les quatre cadences proposées sont le samedi à 02:00, 03:00, 04:00 et 04:30, fuseau Asia/Dubai. Elles commencent désactivées ; les calendriers déjà édités dans l’interface restent prioritaires, même s’ils sont vides.

Code ajouté, sous `C:\Users\Karim\Repositories\property-platform\` : `apps/api/src/property_platform/modules/evidence/project_adapters.py`, `project_catalogues.json`, `project_discovery.py`, `migrations/0021_projectsourcecandidate_and_more.py` ; annuaire dans `apps/web/src/app/[locale]/projects/page.tsx`. Les contrats `packages/contracts/openapi.json` et `src/generated.ts` sont régénérés depuis Django.
