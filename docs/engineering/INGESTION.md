# Collecte et orchestration avec Prefect

**Files et exécutions orphelines du runner — 30 octobre 2026 ([A26](../tasks/A26.md)).** Le runner exécute une seule course à la fois.

- **Cadence.** Les quatre files (`walking-areas`, `basemap-*`, marquées `drain` dans le registre) passent toutes les deux minutes au lieu de chaque minute : les fonds de carte aux minutes paires, les zones de marche aux minutes impaires. Le runner tournait à environ 90 % de sa capacité, et un import de plusieurs heures laissait des centaines de courses en retard devant chaque lancement manuel.
- **Passage des horaires.** Un horaire `initial-cadence` resté sur `* * * * *` passe à la nouvelle cadence au redémarrage, et son état actif est conservé. Un horaire modifié par un opérateur reste tel quel.
- **Courses remplacées.** Au démarrage puis chaque minute, le runner ne garde que la dernière course en retard planifiée de chaque file : une seule course vide toute la file. Il annule les précédentes avec le message « Superseded by a later run of the same queue. ». Les lancements manuels ne sont jamais annulés.
- **Exécutions orphelines.** Au démarrage, avant de prendre une course, le runner marque « Crashed » les exécutions de ses déploiements restées `Pending`, `Running` ou `Cancelling`. Elles viennent d'un processus précédent, par exemple un conteneur recréé en pleine course. Sans cela, l'unique créneau de concurrence du déploiement restait pris : `walking-areas` n'a plus rien calculé du 27 au 30/10.

La règle suppose un seul runner pour ces déploiements, ce qu'assure le service `ingestion` du compose. Le contournement par appel direct du flow (paragraphe F06 ci-dessous) reste valable pendant un import de plusieurs heures.

**Parcelles AD-SDI de l'émirat — 27 octobre 2026 (F01).** Le registre atteint **63 déploiements** avec trois imports manuels `adm-`, `aam-` et `wrm-parcels-adsdi-districts` (flow `property-platform-sdi-district-parcels`). Chaque district est une exécution auditée distincte, de périmètre `<municipalité>:<district>` (par exemple `aam:al-bateen`), avec ses captures, sa quarantaine et sa source `ad-sdi:generic-search:plots:<périmètre>`. Les 213 districts viennent du registre revu `evidence/maps/sdi_districts.json` (statistiques AD-SDI du 27/10 : 98 ADM, 69 AAM, 46 WRM, environ 410 000 parcelles) ; aucun nom de district n'est accepté hors de ce registre. Les trois îles gardent leur périmètre et leur clause d'origine, pour que les captures archivées se rejouent à l'identique. Le paramètre `districts` limite l'import à une liste ; un échec n'interrompt pas les autres districts et le flow échoue en les nommant. Aucun horaire : une municipalité entière représente plusieurs heures d'acquisition.

**Budgets d'un district AD-SDI — 28 octobre 2026 (F05).** Un district a son propre budget, déclaré par `sdi_protocol` : 256 Mio et 503 réponses par session (métadonnées, deux listes et 500 lots de 100 au plus, pour le plafond de 50 000 identifiants), au lieu des 64 Mio partagés par les autres sources ; le journal des réponses d'un échec suit les mêmes bornes. Le sous-processus d'un import `sdi_parcels` dispose de 3 600 s (`SDI_TIMEOUT`) au lieu de 900. Mesures qui l'ont imposé : Al Faqa' a reçu 66,5 Mo en 60 de ses 74 lots (grandes parcelles rurales) ; Madinat Al Riyad demande 355 requêtes à environ 5 s chacune. Le plafond global de `SourceHTTP` (`MAX_DECLARED_SESSION_BYTES`) borne tout budget déclaré.

**Derniers districts AD-SDI — 28 octobre 2026 (F06).** Al Faqa' importé (7 307 parcelles). **SA' est indisponible chez la source** : trois essais identiques (27 et 28 octobre) reçoivent la page « Request Rejected » du pare-feu d'AD-SDI pour la clause `DISTRICTENG='SA'''` ; la requête n'est pas reformulée pour passer le filtre. Il ne sera collecté que par une autre voie autorisée (plateforme ouverte `data.abudhabi`, si Karim retient cette option dans [A21](../tasks/A21.md)). Madinat Al Riyad dépassait les 3 600 s dans la base, pas chez la source : avec l'index `parcel_official_plot` (F07), son réimport crée 35 077 parcelles en 8 minutes ([ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)). L'émirat compte ainsi 212 districts importés sur 213. Quand le runner est en retard sur les files minute, un import manuel peut être lancé par le flow lui-même dans le conteneur d'ingestion (`sdi_district_parcels(municipality=…, districts=[…], actor=…)`) : il crée la même exécution Prefect, avec capture, exécution et audit.

**Complément AD-SDI — 22 octobre 2026.** Le registre atteint **56 déploiements**
avec trois imports manuels `*-parcels-adsdi`. Le flow distinct compare les lots aux
parcelles Onwani et conserve les conflits, captures et audit ; il ne remplace pas
automatiquement un fournisseur par l'autre. Appliquer la migration additive 0030
et reconstruire API/ingestion. Le [guide de qualité cartographique](MAP_DATA_QUALITY.md)
documente les règles, l'import sur base vide et les limites de rejeu hors ligne.

**Catalogue — 21 octobre 2026 :** 42 déploiements sont enregistrés dans le code. Les fiches sont traitées source par source ; les vingt portées de découverte et leurs versions sont archivées séparément. Le flow manuel `empty-project-catalogue-rebuild` initialise une cible vide et rejoue fiches puis catalogues avec leurs horodatages d'origine. Il refuse un catalogue déjà alimenté et n'efface aucune donnée. `project-details` accepte `acquisition_mode=live`, `archive_latest` ou `archive_all` ; aucune substitution silencieuse d'une source indisponible. Voir [PROJECT_CATALOGUE.md](PROJECT_CATALOGUE.md) pour les modes, la séparation des bases et les limites de cette reconstruction.

**Analyses de carte — 20 octobre 2026 :** le registre atteint 41 déploiements avec **routing-osm-graph** et **walking-areas**. Le premier archive le PBF OSM en fragments DB de 4 Mio, puis construit le graphe privé Valhalla ; le second archive les contours piétons demandés sur la carte. Les tables typées et leurs journaux sont contrôlés par data-history. Reprise hors ligne, budgets, activation et exploitation dans [MAP_ANALYSIS.md](MAP_ANALYSIS.md).

**Historique — 20 octobre 2026 :** quatre déploiements complètent le registre : **data-history** vérifie chaque table métier et conserve son rapport ; trois **basemap-…** archivent les tuiles ouvertes demandées/couvertes et leurs dates. Voir [DATA_HISTORY.md](DATA_HISTORY.md) pour les migrations, reprises, retraits confirmés et limites de droits. Les données déjà collectées restent dans leurs modèles typés et leurs pipelines existants.

Mise en place du 13 octobre 2026. Le code de collecte et d'orchestration est dans **`C:\Users\Karim\Repositories\property-platform\apps\ingestion`**. Prefect fournit l'interface de lancement, les horaires et les journaux ; les services Django existants valident et enregistrent les données métier. L'application web lit ensuite cette base, sans attendre une collecte distante au clic.

## Sommaire

- [Comprendre les éléments](#comprendre-les-éléments)
- [Les tâches disponibles](#les-tâches-disponibles)
- [Premier démarrage](#premier-démarrage)
- [Lancer et suivre un import dans l'interface](#lancer-et-suivre-un-import-dans-linterface)
- [Configurer les horaires](#configurer-les-horaires)
- [Cas particulier des images Sentinel](#cas-particulier-des-images-sentinel)
- [Où trouver le code](#où-trouver-le-code)
- [Audit, répétitions et erreurs](#audit-répétitions-et-erreurs)
- [Arrêter, reprendre et mettre à jour](#arrêter-reprendre-et-mettre-à-jour)
- [Validation et limites actuelles](#validation-et-limites-actuelles)

## Comprendre les éléments

Un **collecteur** interroge une source connue, conserve les octets et leur heure d'acquisition. Un **import** contrôle ces réponses puis écrit dans la base métier. Un **flow** Prefect enchaîne ces étapes. Un **déploiement** est une tâche disponible dans l'interface, avec ses paramètres et, éventuellement, ses horaires. Un **run** est une exécution précise de cette tâche.

L'environnement ajoute trois services Docker :

| Service | Rôle | Accès |
|---|---|---|
| `prefect` | Interface, API et ordonnanceur Prefect | [http://localhost:4200](http://localhost:4200) |
| `prefect-db` | Base PostgreSQL des déploiements, runs, logs et horaires | Réseau Docker privé, aucun port Windows publié |
| `ingestion` | Runner qui exécute nos flows et collecteurs | Pas de nouveau port public |

La base métier reste **`property_platform`**, dans le service `db` déjà utilisé par Django/PostGIS. La base Prefect est distincte ; elle ne contient pas les tables de parcelles ou de bâtiments. Deux nouveaux volumes gardent les métadonnées Prefect et les reçus de collecte. Arrêter les conteneurs conserve ces volumes, comme celui de la base métier.

Cette configuration est locale : interface liée à `127.0.0.1`, mots de passe d'exemple et aucune publication sur Internet. Un environnement hébergé exige ses propres secrets, contrôles d'accès et sauvegardes.

## Les tâches disponibles

Les jobs projets et catalogues sont détaillés dans [PROJECTS.md](PROJECTS.md). Les pages sont collectées avant les transactions SQL ; leurs fichiers liés restent externes sans autorisation de copie. L’ingestion de fichiers opérateur écrit les octets dans le stockage privé et les métadonnées dans PostgreSQL.

**Ajout du 16 octobre :** le registre contient désormais **33 déploiements**. `media-storage` est un nouveau job manuel de reprise des photos acquises vers le stockage privé ; les imports de présentations Reem et Saadiyat exécutent aussi cette tâche après leur validation Django. API et runner partagent le volume persistant `/media`. L’archivage conserve les captures et les calendriers ; il ne publie rien sur le CDN. Le [guide des médias](MEDIA_STORAGE.md) fournit les commandes de migration, reconstruction et reprise, ainsi que l’activation ultérieure de R2/S3.

Les horaires ci-dessous sont **préparés mais désactivés au premier enregistrement**, dans le fuseau **Asia/Dubai**. Commencer par une exécution manuelle ; activer ensuite les tâches souhaitées dans l'interface. Le démarrage Docker n'effectue pas d'import.

| Déploiement | Données traitées | Horaire proposé |
|---|---|---|
| `project-details` | 30 projets/programmes examinés à Reem, tâches isolées et liens documentaires | Samedi 02:00 |
| `saadiyat-project-details` | 27 projets/programmes examinés à Saadiyat, tâches isolées | Samedi 03:00 |
| `reem-project-discovery` | Catalogues officiels et candidats à examiner | Samedi 04:00 |
| `saadiyat-project-discovery` | Catalogues Saadiyat et candidats à examiner | Samedi 04:30 |
| `project-media-files` | Manifeste privé de fichiers opérateur, sans approbation ni publication | Manuel |
| `parcels-onwani` | Parcelles officielles Onwani, captures, observations et géométries rejetées | Dimanche 03:00 |
| `map-district` | Couche officielle district/secteurs | Dimanche 04:00 |
| `map-community` | Couche officielle communautés | Dimanche 04:15 |
| `map-street` | Couche officielle rues | Dimanche 04:30 |
| `map-osm` | Empreintes, commerces, équipements et transports OSM de Reem | Dimanche 04:45 |
| `saadiyat-map-osm` | Même collecte bornée pour Saadiyat | Dimanche 07:45 |
| `reem-osm-bootstrap`, `saadiyat-osm-bootstrap` | Reprise officielle OSM XML par quatre fenêtres, mêmes identités et audit | Manuel uniquement |
| `project-references` | Pages publiques du registre de recherche et repères déclarés de projets | Lundi 05:00 |
| `property-presentations` | Six présentations examinées et médias dont les droits sont déclarés | Tous les jours 02:00 |
| `sentinel-previews` | Reçu existant de deux scènes historiques Sentinel | Manuel uniquement |
| `construction-activity` | Changement au sol Sentinel-2 des parcelles de projets relues ([méthode](CONSTRUCTION_ACTIVITY.md)) | Le 5 de chaque mois à 04:00 ; activé sur le poste de Karim le 30/10/2026 |
| `evidence-search` | Index de recherche des affirmations publiées et de leurs preuves, sans collecte ([règles](EVIDENCE_SEARCH.md)) | Tous les jours à 02:30 ; activé sur le poste de Karim le 30/10/2026 |
| `ingestion-readiness` | Vérification des registres et de la migration d'orchestration ; aucune collecte ni écriture métier | Manuel uniquement |

Le registre de recherche contient actuellement **113 URL** ; cela ne signifie pas que 113 fournisseurs acceptent la collecte ou que 113 projets sont identifiés. Le flow de références traite chaque URL séparément et signale un lot incomplet si certaines échouent. Une page de recherche reste une référence, pas une preuve automatiquement acceptée d'un prix ou d'une disponibilité.

Les connecteurs sont propres à leurs profils **Al Reem Island**, **Saadiyat Island** ou au contexte officiel **Abu Dhabi** ; cela ne donne pas une couverture nationale automatique. Pour une autre zone, ajouter son profil, ses sources et ses contrôles ; sélectionner simplement un autre émirat dans le site ne lance pas de collecte. Les présentations demeurent examinées manuellement : rafraîchir leurs reçus ne constitue pas un extracteur de prix, de livraison ou de plans de paiement. Voir [les prochains pipelines immobiliers](PROPERTY_DATA_PIPELINES.md).

## Premier démarrage

Docker Desktop doit être démarré. Ouvrir **PowerShell**, puis se placer dans la racine du dépôt :

```powershell
cd C:\Users\Karim\Repositories\property-platform
```

Les chemins qui suivent sont relatifs à cette racine. Les deux fichiers utilisés sont **`C:\Users\Karim\Repositories\property-platform\infra\local\compose.yaml`** et **`C:\Users\Karim\Repositories\property-platform\infra\local\compose.ingestion.yaml`**. Le premier décrit les services du site ; le second ajoute les services facultatifs d'ingestion.

**1. Démarrer la base métier, puis construire l'image d'ingestion :**

```powershell
docker compose -f infra/local/compose.yaml up -d db
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion build ingestion
```

`build ingestion` installe les versions verrouillées dans une image contenant Prefect, nos collecteurs et les services Django partagés. Cela ne lance ni collecte ni migration. Le site/API déjà démarrés peuvent rester en fonctionnement.

**2. Appliquer les migrations avec cette nouvelle image :**

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion run --rm --no-deps ingestion python /workspace/apps/api/manage.py migrate --noinput
```

Cette commande crée un conteneur temporaire, applique les migrations Django manquantes et le retire. La migration `evidence.0011_ingestion_orchestration` ajoute le registre d'exécution et ses liens d'audit dans le schéma `evidence`. Les migrations suivantes ajoutent les décisions de rapprochement d'identifiants de source et la référence à un import déjà appliqué. Elles ne recollectent aucune source et ne fusionnent pas automatiquement des biens. Le chemin `/workspace/apps/api/manage.py` est **dans le conteneur Linux** ; son équivalent sur le poste est **`C:\Users\Karim\Repositories\property-platform\apps\api\manage.py`**.

**3. Démarrer les trois services supplémentaires :**

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion up -d --no-build prefect-db prefect ingestion
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion ps
```

Le runner attend les services nécessaires, vérifie le schéma puis enregistre vingt déploiements. `Ready` signifie qu'il peut exécuter une tâche ; cela ne signifie pas que celle-ci a déjà importé des données. Ouvrir **[Prefect sur localhost:4200](http://localhost:4200)**. L'accueil peut être celui de l'interface v2.

**Sur le poste de Karim, ces étapes ont déjà été effectuées le 13 octobre 2026.** La migration est appliquée et les services sont démarrés ; ouvrir l'interface suffit tant que Docker tourne.

### Si la construction échoue sur un certificat TLS

Sur ce poste, Avast inspecte HTTPS. Le certificat public de son autorité racine, déjà approuvé par Windows et dont la chaîne a été vérifiée, a été exporté dans le fichier ignoré **`C:\Users\Karim\Repositories\property-platform\.cache\validation\ingestion-trusted-ca.crt`**. Pour reconstruire ici avec cette même autorité approuvée :

```powershell
docker build --secret id=platform_extra_ca,src=.cache/validation/ingestion-trusted-ca.crt -t property-platform-ingestion -f apps/ingestion/Dockerfile .
```

Le secret BuildKit apporte uniquement ce certificat public au système de confiance de l'image ; la vérification TLS reste activée. Ce fichier ne contient aucune clé privée et n'est pas commité. Sur un poste sans cette inspection, utiliser la construction normale. Si le fichier manque ou si la confiance a changé, vérifier l'autorité avec l'administrateur du poste avant de réexporter ; ne pas désactiver TLS pour terminer l'installation.

Ce même secret facultatif existe pour les images API et web. Si leurs constructions normales rencontrent aussi `UnknownIssuer` sur ce poste, construire leur image avec l'autorité déjà vérifiée, puis utiliser `up -d --no-build` pour la lancer :

```powershell
docker build --secret id=platform_extra_ca,src=.cache/validation/ingestion-trusted-ca.crt -t property-platform-local-api -f apps/api/Dockerfile .
docker build --secret id=platform_extra_ca,src=.cache/validation/ingestion-trusted-ca.crt -t property-platform-web-preview -f apps/web/Dockerfile .
```

Un certificat renouvelé nécessite une nouvelle vérification et une invalidation du cache de la couche de confiance ; voir [TOOLCHAIN.md](TOOLCHAIN.md). La chaîne de confiance ajoutée n'est pas un mot de passe de la plateforme.

## Lancer et suivre un import dans l'interface

1. Ouvrir [http://localhost:4200](http://localhost:4200), puis **Deployments** dans le menu gauche.
2. Ouvrir **`ingestion-readiness`**, puis **Run → Quick run**. Ce contrôle vérifie la connexion, les registres et la présence des nouvelles tables sans modifier les données métier.
3. Dans l'onglet **Runs**, ouvrir le nom de l'exécution. **Logs** affiche le résultat ; attendre **Completed**. Le premier essai local a confirmé six présentations, 113 références et `orchestration_schema: ready`.
4. Retourner dans **Deployments**, choisir par exemple **`parcels-onwani`**, puis **Run → Quick run**. Celui-ci interroge réellement Onwani et enregistre les réponses validées.
5. Pour préciser l'auteur, utiliser **Run → Custom run**, renseigner `actor` avec `Karim`, puis lancer. Les autres paramètres restent ceux du déploiement. Le journal métier associe cet auteur à l'identifiant du run Prefect.

Les imports utilisent une seule exécution simultanée dans ce runner. Si une autre tâche attend, son état peut rester `Scheduled` ou `Pending` jusqu'à libération du processus. Laisser le runner et la base actifs. Les données s'enregistrent dans le volume PostgreSQL du projet ; fermer l'onglet ne les efface pas.

**Interpréter les états :** `Completed` signifie que le flow s'est terminé normalement. Pour Onwani, un résultat métier `quarantined` peut accompagner `Completed` : les parcelles valides sont appliquées, des géométries rejetées restent conservées pour examen, et un avertissement apparaît dans les logs. `Failed` signale un échec ; examiner l'erreur et la source avant de relancer. Une tentative en échec n'efface pas la dernière carte publiée.

Pour tester les références sans parcourir tout le registre, utiliser **Custom run** avec `limit: 1`. `reference_key` permet de choisir exactement une URL enregistrée par sa clé ; il n'accepte pas une URL libre. Les contrôles HTTP bornent les tailles et délais, vérifient TLS et ne suivent pas les redirections arbitraires.

## Sauvegardes

Les déploiements `backup-database` (chaque nuit) et `restore-check` (chaque semaine) sauvegardent la base, copient les fichiers privés et vérifient une restauration complète dans une base jetable. Voir [BACKUPS.md](BACKUPS.md).

## Configurer les horaires

**Configuration locale activée à la demande de Karim le 13 octobre 2026 :** les sept collectes sont désormais programmées chaque **dimanche**, fuseau **Asia/Dubai** : présentations à 02:00, parcelles à 03:00, district à 04:00, communautés à 04:15, rues à 04:30, OSM à 04:45 et références à 05:00. Les références ne sont donc plus le lundi et les présentations ne sont plus quotidiennes sur ce poste. Le contrôle `ingestion-readiness` et les reçus historiques `sentinel-previews` restent manuels. Les tableaux d'horaires initiaux ci-dessus décrivent le premier enregistrement ; Prefect conserve la configuration active locale au redémarrage.

Sur la page d'un déploiement, le volet **Schedules** contient l'horaire préparé. Son interrupteur permet de l'activer ou le suspendre ; le menu associé permet de l'éditer. **Schedule** ajoute un autre horaire. Vérifier le fuseau **Asia/Dubai**, la fréquence et les paramètres avant l'activation. Le navigateur peut afficher les dates des runs dans son propre fuseau ; celui du schedule gouverne l'exécution.

Nos horaires initiaux sont hebdomadaires pour la géométrie et quotidiens pour les présentations. Une activation n'exige pas une nouvelle migration. Les horaires, leur état actif/inactif et les paramètres modifiés dans Prefect sont conservés au redémarrage du runner ; celui-ci ne rétablit pas systématiquement les valeurs du code. Supprimer tous les horaires d'un déploiement laisse ce choix intact au prochain démarrage.

**L'ordinateur, Docker et les trois services doivent rester démarrés pour exécuter des horaires locaux.** Prefect enregistre le calendrier ; le runner exécute les tâches. Une exécution régulière indépendante de ce PC demandera un hébergement séparé. La présente installation ne crée pas d'abonnement Prefect Cloud.

## Cas particulier des images Sentinel

Les deux scènes actuelles sont historiques et leur préparation raster reste séparée. Le flow importe un reçu déjà acquis, sans télécharger ou recalculer automatiquement de nouvelles images. Copier le reçu du poste dans le volume d'ingestion :

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion cp .cache/acquisitions/sentinel-reem.json ingestion:/data/sentinel-reem.json
```

Le fichier source complet est **`C:\Users\Karim\Repositories\property-platform\.cache\acquisitions\sentinel-reem.json`**. Dans Prefect, ouvrir **`sentinel-previews`**, puis **Run → Quick run**. Le paramètre `receipt_name` reste `sentinel-reem.json` ; le flow accepte un fichier JSON dans `/data`, pas un chemin arbitraire ou une URL.

Le reçu conserve les dates réelles de l'acquisition historique. Relancer exactement ce reçu réutilise son import déjà validé ; cela ne transforme pas une image ancienne en image fraîche. Les dépendances lourdes de rendu/OCR/raster ne sont pas ajoutées au serveur web/API ni au runner léger.

## Où trouver le code

Tous les chemins ci-dessous partent de **`C:\Users\Karim\Repositories\property-platform`** :

| Chemin complet | Responsabilité |
|---|---|
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\registry.py` | Catalogue des déploiements, paramètres et horaires initiaux |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\deployments.py` | Enregistrement et runner Prefect ; préservation des réglages UI |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\flows.py` | Enchaînement des tâches, paramètres, auteur et logs |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\collectors\http.py` | Collecte HTTPS bornée, délais, cadence et reçus |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\collectors\map.py` | Protocoles Onwani, couches officielles et OSM |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\collectors\references.py` | Acquisition des URL du registre de recherche |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\collectors\properties.py` | Acquisition des pages et médias de présentations examinées |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\collectors\snapshots.py` | Restitution exacte des réponses au validateur métier |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\storage.py` | Reçus privés persistants ; publication sans écrasement d'un reçu concurrent |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\runtime.py` | Processus Django isolé, délais et réconciliation d'un résultat incertain |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\domain.py` | Collecte puis appel des services Django partagés |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\rebuild\orchestration.py` | Registre durable, verrous, transaction et rapprochement des résultats |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\migrations\0011_ingestion_orchestration.py` | Création additive des deux tables d'orchestration |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\identity_resolution.py` | Correspondances exactes et décisions typées pour les identifiants Onwani renouvelés |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\identity_repair.py` | Réparation explicite des doublons déjà créés et révocation auditée |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\catalog\migrations\0005_source_identity_aliases.py` | Liens de remplacement conservant les anciens objets |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\migrations\0012_source_identity_aliases.py` | Tables de décisions et lien vers l'exécution réutilisée |

Les modèles et règles métier restent dans **`C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence`**. Le runner dépend de ce paquet local ; aucune copie des modèles n'est créée dans `apps/ingestion`. Les commandes `manage.py import_onwani`, `import_reem_map`, `import_reem_references`, `import_property_presentations` et `import_reem_imagery` restent utilisables manuellement. Prefect appelle leurs services partagés plutôt qu'un script shell qui reproduirait leurs règles.

Pour un nouveau fournisseur : ajouter un collecteur dans cette application, définir ses contrôles et son import typé dans le domaine propriétaire, puis enregistrer son flow et ses paramètres. Documenter la dépendance dans [REPOSITORY.md](REPOSITORY.md), verrouiller les dépendances et tester ses erreurs, répétitions et limites. Les prix/plans/disponibilités nécessiteront leurs propres modèles avant publication.

## Audit, répétitions et erreurs

Dans la base métier, les nouvelles tables sont **`property_platform.evidence.ingestion_execution`** et **`property_platform.evidence.ingestion_execution_run`**. Elles enregistrent identité durable, opération, portée, auteur, identifiant Prefect, tentatives, heures, état, empreinte éventuelle du reçu et liens vers les `IngestionRun` métier. Leur résumé JSON contient un bilan opérationnel ; les parcelles, faits et médias restent dans leurs modèles propres.

La collecte réseau se termine **avant** la transaction d'écriture métier. Les réponses passent ensuite par les validateurs existants. Des verrous PostgreSQL empêchent deux imports concurrents de remplacer la même famille de données. Le résultat et les écritures canoniques sont validés dans une même transaction ; une relance du même run retrouve son résultat enregistré. Un nouvel horaire constitue une nouvelle vérification, avec ses nouvelles dates réelles, même si les octets sont identiques.

Les tâches d'écriture ne sont pas mises en cache par Prefect et n'ont pas de réessai automatique aveugle. Si le processus dépasse son délai ou perd sa réponse après validation, une réconciliation consulte le registre avant d'annoncer un échec ; elle ne recollecte pas et ne répète pas les écritures. Les reçus de présentations persistés permettent de reprendre exactement le même lot. Une panne d'acquisition est auditée sans inventer une capture inexistante.

Pour Onwani et les couches de carte, les réponses complètes réellement reçues avant un rejet de schéma, de couverture ou de statut HTTP sont conservées comme captures d'une acquisition en échec. Le journal est borné ; un timeout sans réponse ou un flux interrompu ne crée pas de faux reçu. Aucune donnée canonique n'est appliquée à partir de ce lot rejeté. Pour les présentations, le checkpoint est publié seulement après acquisition du lot complet ; les collectes partielles ne remplacent pas le dernier lot validé.

Rejouer exactement un reçu Sentinel ou de présentations depuis **un nouveau run Prefect** crée sa propre ligne d'exécution, reliée au premier import par `reused_from`. Son auteur et son identifiant Prefect sont distincts ; les acquisitions, dates et auteurs d'origine restent intacts. Cette répétition n'ajoute pas une deuxième image ou une nouvelle observation commerciale.

### Quand le fournisseur change ses identifiants techniques

Le premier rafraîchissement a révélé qu'Onwani avait changé ses `OBJECTID` entre deux acquisitions. Ces numéros sont des identifiants de lignes chez le fournisseur ; ils ne garantissent pas qu'un nouveau numéro représente une nouvelle parcelle. Le contrôle local a retrouvé les mêmes 2 431 parcelles par **PLOTID non vide, code et géométrie identiques**, et huit communautés par leurs attributs de source et leur géométrie identiques.

Les décisions de rapprochement sont typées dans `evidence.parcel_source_alias` et `evidence.administrative_area_source_alias` : nouvel identifiant, objet interne conservé, capture justificative, auteur, raison et état de révocation. Les objets créés en double restent conservés avec `superseded_by` ; les projections de carte et les compteurs utilisent l'objet canonique. Les anciens liens de parcelle restent consultables. Aucun run, capture ou ancienne observation n'est supprimé ou réaffecté silencieusement.

Un nom, une proximité ou un PLOTID ambigu ne suffit pas à fusionner des objets. Les correspondances incertaines et les identifiants réutilisés pour une autre entité sont refusés. Les décisions acceptées peuvent être révoquées avec audit ; un rafraîchissement ne change pas une décision révoquée sans une nouvelle revue.

La commande de maintenance **`C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\management\commands\reconcile_source_identities.py`** effectue d'abord une simulation. Le `--run` désigne un **`evidence.ingestion_run.id`**, pas l'UUID du flow Prefect. Pour examiner une acquisition identifiée dans les tables d'audit, remplacer `UUID_ACQUISITION_A_EXAMINER` par son UUID réel :

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion exec ingestion python /workspace/apps/api/manage.py reconcile_source_identities --actor Karim --run UUID_ACQUISITION_A_EXAMINER
```

Cette simulation affiche `candidates`, `conflicts`, des exemples d'UUID et `applied: false`. Une application explicite de ce plan utilise la même commande avec `--apply`, seulement après revue de la portée et des conflits. Sur ce poste, les deux plans du 13 octobre ont été examinés puis appliqués : **2 431 parcelles et huit communautés, zéro conflit**. Il n'est pas nécessaire de refaire cette réparation pour utiliser Prefect.

Pour une révocation examinée, le même outil prend `--revert --target parcel` (ou `administrative_area`), `--decision` avec l'identifiant de la décision et `--reason` avec la raison, d'abord sans `--apply`. Il refuse une source occupée, une chaîne de remplacements ou des révisions modifiées depuis la décision. La révocation ne rembobine pas les faits acquis entre-temps et ne supprime aucune preuve.

**Compter ce que la carte affiche**, dans un client SQL connecté à `property_platform` :

```sql
SELECT count(*) AS parcelles_canoniques
FROM real_estate.parcel
WHERE superseded_by_id IS NULL;
```

Les lignes conservées pour l'historique expliquent pourquoi `SELECT count(*) FROM real_estate.parcel` peut être plus élevé. Les projections utilisent le premier compteur ; les doublons remplacés restent disponibles pour audit.

Les horaires et logs techniques sont dans la base Prefect ; la provenance durable des données demeure dans la base métier. Les captures, leur empreinte et les dates de collecte/publication connues restent distinctes. Voir [DATA_PROVENANCE.md](DATA_PROVENANCE.md) pour le sens de chaque date. Les reçus privés et dumps ne vont pas dans Git.

## Arrêter, reprendre et mettre à jour

**Arrêter seulement l'orchestration :**

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion stop ingestion prefect prefect-db
```

Le site, l'API et `db` restent actifs. L'arrêt laisse un délai de grâce aux tâches ; attendre la fin d'un run avant un changement de code. Les volumes ne sont pas supprimés.

**Tout arrêter, si le site utilise aussi ses conteneurs Docker :**

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion --profile web-preview stop
```

Cette commande arrête les services des profils locaux sans supprimer leurs conteneurs ni volumes. Si Next.js tourne avec `pnpm.cmd dev:web` dans un terminal Windows, appuyer aussi sur **Ctrl+C dans ce terminal**. `stop` permet de conserver les données et de reprendre ensuite les services voulus avec `up -d`.

**Reprendre :**

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion up -d --no-build prefect-db prefect ingestion
```

**Après une modification du code d'ingestion ou des services Django partagés**, reconstruire l'image, appliquer les éventuelles migrations, puis recréer les deux services qui l'utilisent :

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion build ingestion
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion run --rm --no-deps ingestion python /workspace/apps/api/manage.py migrate --noinput
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion up -d --no-build prefect ingestion
```

Sur ce poste avec l'inspection Avast, remplacer la commande `build ingestion` par la construction avec le certificat décrite plus haut. Si le backend web lui-même a changé, reconstruire également le service `api` suivant [DEVELOPMENT.md](DEVELOPMENT.md) ; le conteneur API n'est pas mis à jour par une construction d'ingestion. Les services utilisent une image figée, sans rechargement automatique du code Windows.

**Contrôler et lire les logs depuis PowerShell :**

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion exec ingestion python -m property_platform_ingestion check
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion exec ingestion python -m property_platform_ingestion datasets
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion logs -f ingestion prefect
```

`check` ne modifie pas la base. `datasets` affiche le catalogue. `logs -f` suit les journaux jusqu'à **Ctrl+C** ; cela arrête l'affichage, pas les conteneurs. Le sous-processus Django de chaque collecte hérite de la sortie d'erreur du runner : ses traces d'échec apparaissent dans les journaux du service `ingestion`, alors que le résultat Prefect ne garde que la classe d'erreur. Les commandes complètes sont longues parce que les deux fichiers Compose et le profil sont explicitement indiqués.

## Validation et limites actuelles

Prefect **3.8.8**, HTTPX **0.28.1**, Python **3.14.8** et uv **0.13.0** sont verrouillés ; les nouvelles versions ont été vérifiées sur les sources officielles le 13 octobre 2026. Les compatibilités conservées du site et de ses compilateurs sont décrites dans [TOOLCHAIN.md](TOOLCHAIN.md). Dernière version stable compatible ne signifie pas suppression des contraintes nécessaires au projet.

Validation locale : construction Linux avec TLS vérifié, **77 tests ingestion Linux**, **185 tests backend vérifiés sur PostgreSQL/PostGIS** (suite complète de 184, puis quatre tests ciblés après le dernier ajout), contrôles de formatage et registre de neuf déploiements. La compilation du web, ses 19 tests, le compilateur TypeScript 7, les contrats et le smoke HTTP des quinze langues passent dans Docker avec Node 26. Le workflow CI possède désormais un job ingestion séparé ; ces vérifications locales ne constituent pas une preuve d'exécution réussie sur GitHub Actions.

Essais réels du 13 octobre : contrôle de disponibilité, parcelles, district, communautés, rues, six présentations, référence officielle de The District et reçu Sentinel exécutés via Prefect. Une nouvelle acquisition Onwani après réparation affiche **`created: 0`, `unchanged: 2431`, `quarantined: 1`** ; les communautés affichent 26 objets inchangés. Le deuxième run Sentinel possède sa propre exécution avec `reused_from`, sans capture supplémentaire. Les horaires modifiés dans l'UI ont survécu au redémarrage ; les sept horaires sont laissés suspendus.

**Limite amont observée :** Overpass principal répond HTTP 406 et le miroir enregistré ne répond pas dans le délai de lecture de 60 secondes. Le flow `map-osm` est bien installé, mais son rafraîchissement réel a échoué. La réponse 406 et ses dates sont conservées dans une acquisition en échec ; les bâtiments, lieux et rues OSM déjà validés restent affichés avec leur provenance précédente. Ne pas confondre `Ready` avec une source disponible ou un import réussi. Une reprise sera utile lorsque le fournisseur répondra de nouveau, ou après revue d'un autre endpoint autorisé.

L'installation livre l'ordonnancement des sources existantes. Les traitements OCR/3D/IA, la collecte de prix et plans, les flux de disponibilité, les alertes externes et le stockage S3 restent des extensions à construire. Les tâches payantes demanderont une identité durable, une réservation de budget et une réconciliation avant tout réessai.


## Extension Saadiyat et calendriers locaux

Le registre comporte désormais 17 déploiements : les 9 précédents de Reem et 8 nouveaux pour Saadiyat. Les flows sont réutilisés avec le paramètre territory, tandis que captures, identités et registres restent propres à chaque île. Le guide [SAADIYAT.md](SAADIYAT.md) donne l'ordre des imports initiaux.

| Déploiement Saadiyat | Cadence locale, Asia/Dubai |
|---|---|
| saadiyat-parcels-onwani | Dimanche 06:00 |
| saadiyat-map-district | Dimanche 07:00 |
| saadiyat-map-community | Dimanche 07:15 |
| saadiyat-map-street | Dimanche 07:30 |
| saadiyat-map-osm | Dimanche 07:45 |
| saadiyat-project-references | Dimanche 08:00 |
| saadiyat-property-presentations | Dimanche 08:30 |
| saadiyat-osm-bootstrap | Manuel, aucun horaire |

Les cadences récurrentes Saadiyat sont activées sur le poste de Karim, selon la préférence déjà donnée pour le week-end. Les horaires et activations existants de Reem sont conservés. Sur une installation neuve, les calendriers restent initialement désactivés afin de vérifier les premiers imports avant leur activation. L'import XML initial OSM, Sentinel et le contrôle de disponibilité restent manuels.

Le bootstrap XML est une lecture limitée à quatre fenêtres enregistrées, 16 Mio par réponse et 64 Mio par lot. Il utilise les mêmes identités canoniques OSM que le connecteur Overpass, conserve les XML originaux et déduplique les recouvrements exacts. Une divergence de version/géométrie bloque le lot. L'API d'édition OSM ne sert pas de collecteur récurrent national ; les mises à jour continuent via le déploiement Overpass. Ses indisponibilités restent visibles dans Prefect et n'effacent pas les données acquises.


## Collectes ADREC — 13 octobre 2026

Les trois déploiements supplémentaires `adrec-reem-sales`, `adrec-saadiyat-sales` et `adrec-price-indices` portent le total à vingt. Ils alimentent trois tables typées du schéma `evidence` via Django et les captures existantes. Leur fonctionnement, les endpoints, le calendrier dominical et la consultation sur le site sont détaillés dans [ADREC.md](ADREC.md). Une série d’indices contradictoire est conservée non exploitable ; elle ne doit pas être corrigée en choisissant arbitrairement une ligne.


## Contexte Abu Dhabi — 14 octobre 2026

Les six nouveaux déploiements portent le total à **26** : ventes ADREC pour l’émirat et cinq jeux de contexte (santé, écoles Charter, bus, recensement immobilier, limites des districts). Le [guide Abu Dhabi](ABU_DHABI.md) détaille sources, horaires et tables. Les cinq acquisitions automatiques validées sont activées le dimanche sur le poste Karim. ADEK a retourné HTTP 403 au collecteur ; son import depuis un document conservé est manuel, avec receipt_name et date d’archive préservée. Son calendrier reste inactif. Ni les paramètres modifiés dans l’UI ni les horaires des vingt déploiements précédents ne sont réinitialisés.

## Lieux complémentaires — 17 octobre 2026

Le registre contient maintenant **35 déploiements**, avec `reem-places-overture` et `saadiyat-places-overture`. Les deux premières exécutions ont réussi et leurs calendriers dominicaux sont activés sur le poste Karim, sans changement des autres horaires. Le [guide Overture](OVERTURE_PLACES.md) décrit les preuves, la version fixée et les limites.
