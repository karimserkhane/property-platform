# Ingestions publiques Abu Dhabi

Extension du **14 octobre 2026**, sur la branche `codex/abu-dhabi-context-ingestion`. Les connecteurs existants de Reem et Saadiyat restent disponibles. Cette extension ajoute des données à l’échelle de l’émirat ; elle ne prétend pas importer tous les sites, tous les permis ou tous les logements d’Abu Dhabi.

## Sommaire

- [Données et limites](#données-et-limites)
- [Pipelines Prefect](#pipelines-prefect)
- [Tables et provenance](#tables-et-provenance)
- [Où est le code](#où-est-le-code)
- [Installation et lancement](#installation-et-lancement)
- [Archive ADEK](#archive-adek)
- [Consultation dans le site](#consultation-dans-le-site)
- [Carte d’ensemble et districts officiels](#carte-densemble-et-districts-officiels)
- [Sources restant à qualifier](#sources-restant-à-qualifier)
- [Validation](#validation)

## Données et limites

Effectifs du premier import, pas une promesse d’exhaustivité. Les observations restent celles de leur producteur.

| Source | Données ajoutées | Limites essentielles |
|---|---|---|
| [ADREC](https://adrec.gov.ae/en/market-data) | **6 747 ventes** dans la fenêtre du 16 juillet au 13 octobre 2026, avec prix/surfaces disponibles et noms originaux | `municipality=all`, `district=all`. Les snapshots des îles recouvrent celui de l’émirat : ne pas les additionner. Pas de stock d’annonces, de prix demandé actuel ou de lien automatique vers un bâtiment. |
| [DMT / Onwani, couche DISTRICT](https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/1) | **216 districts**, noms anglais/arabe, identifiants et limites PostGIS ; 101 ADM, 69 AAM, 46 WRM dans la réponse examinée | Vérification des listes d’identifiants avant/après et du GeoJSON reçu. Ces observations de limites restent distinctes des identités cadastrales existantes ; elles n’ajoutent pas les parcelles/bâtiments de tous les districts. |
| [DoH — Public Health Facility Map](https://stem.doh.gov.ae/publicmap/) | **918 établissements**, dont 28 indiqués comme prévus dans la réponse examinée ; type, nom, adresse, opérateur, services originaux et coordonnées | Date de publication inconnue. La présentation historique du portail évoque des enquêtes anciennes ; une collecte aujourd’hui ne prouve pas une ouverture ou une licence valide aujourd’hui. Pas de recommandation médicale. |
| [ADEK — Charter Schools](https://charterschools.abudhabi/find-a-school) | **37 écoles Charter**, identifiant ESIS, noms bilingues, municipalité/quartier, niveaux originaux et coordonnées | Sous-ensemble Charter uniquement, sans notes Irtiqaa ni frais. Le fichier public a été reçu sur Windows ; la collecte automatique reçoit HTTP 403. Import du document conservé via Prefect, actualisation automatique désactivée. |
| [Abu Dhabi Mobility](https://admobility.gov.ae/en/pb-bus-service/) | **147 lignes** publiées, identité de ligne, numéro, nom et extrémités | Les liens d’horaires suivent le script du producteur ; les PDF, arrêts, parcours, fréquences et temps de trajet ne sont pas importés ou vérifiés individuellement. Certaines lignes sortent de l’émirat. |
| [SCAD — Real Estate Census](https://census.scad.gov.ae/home/realestate?lang=en) | **12 mesures** structurées publiées dans le HTML : bâtiments, unités, catégories, régions et croissance | Référence **2024**, modification du document déclarée **1 juillet 2025**. Nombres arrondis à des multiples de cinq. Ce n’est ni le registre des appartements ni l’ensemble des tableaux Tableau du portail. |

Les cinq sources de contexte ont un accès public observé, sans licence commerciale de redistribution établie dans cette revue. `reuse_status=public_access_license_unconfirmed` reste enregistré. L’API demeure une prévisualisation locale protégée par les réglages existants ; vérifier les droits avant diffusion publique. Il n’y a pas de nouvelles photographies ou de copies de brochures dans cette extension.

## Pipelines Prefect

Le registre contient désormais **26 déploiements**. Six viennent de cette extension. Les horaires utilisent `Asia/Dubai` et sont initialement inactifs sur une nouvelle installation. Sur le poste Karim, les cinq acquisitions automatiques validées sont activées pour le dimanche ; ADEK reste inactif.

| Déploiement | Ce qu’il fait | Dimanche |
|---|---|---|
| `adrec-abu-dhabi-sales` | Snapshot de 90 journées terminées pour l’émirat ; partitions mensuelles/journalières vérifiées | 10:30 |
| `abu-dhabi-health` | Réponse publique complète du répertoire DoH | 11:00 |
| `abu-dhabi-schools` | Document ADEK Charter ; tentative HTTPS ou archive explicitement fournie | 11:15, **inactif** |
| `abu-dhabi-mobility` | Liste publiée dans le sélecteur de lignes du site officiel | 11:30 |
| `abu-dhabi-statistics` | Mesures SCAD du Dataset JSON-LD, sans exécuter JavaScript | 11:45 |
| `abu-dhabi-districts` | Identifiants Onwani, limites GeoJSON, nouvelle lecture des identifiants | 12:00 |

Les cinq jobs de contexte utilisent le flow `property-platform-public-context`, avec un paramètre `dataset` fermé. Le flow de ventes ADREC est réutilisé. Aucun visiteur ne choisit une URL, un SQL ou une commande système.

Le premier import ADEK refusé reste dans l’historique avec sa capture HTTP 403. Le run manuel d’archive est distinct. Ne pas activer son calendrier avec un ancien reçu : cela ne rendrait pas les données plus récentes. Les horaires existants modifiés dans l’UI restent conservés au redémarrage. Le PC, Docker Desktop et le runner doivent fonctionner au moment programmé.

## Tables et provenance

Les changements sont **additifs**, appliqués après sauvegarde locale. Les migrations `evidence.0015_public_context`, `0016_adrec_emirate_scope` et `0017_district_context` sont présentes dans le dépôt. Le catalogue immobilier reste dans `real_estate` ; ces nouvelles observations restent dans `evidence`, sans copie de modèles dans Prefect.

| Nom SQL complet | Rôle |
|---|---|
| `property_platform.evidence.public_context_snapshot` | Une version complète de chaque jeu, son acquisition, sa capture principale, son territoire, son effectif et le statut de réutilisation |
| `property_platform.evidence.health_facility_observation` | Établissements et points PostGIS |
| `property_platform.evidence.school_observation` | Écoles Charter et points PostGIS |
| `property_platform.evidence.bus_route_observation` | Lignes et extrémités textuelles |
| `property_platform.evidence.census_measure_observation` | Valeurs décimales, unités, régions, catégories, année et arrondi |
| `property_platform.evidence.district_boundary_observation` | Limites MultiPolygon, identifiant de district et municipalité |
| `property_platform.evidence.adrec_market_snapshot` et `adrec_sale_observation` | Tables ADREC existantes, nouvelle portée `abu-dhabi` |

Le header commun du snapshot organise l’audit ; **les contenus restent dans cinq tables métier typées**, sans table JSON universelle. Les réponses originales restent dans `evidence.capture`.

- Les identités DoH, ESIS, lignes de bus et OBJECTID Onwani sont celles des producteurs. SCAD ne fournit pas d’identifiant de mesure : son `source_record_id` est une clé locale dérivée du libellé (SHA-256), pas un identifiant officiel.
- Observation → snapshot → capture/acquisition → source. `field_path` et `record_sha256` identifient la partie examinée ; `connector_version` décrit le mapping.
- Dates de début/fin de collecte, ingestion, opérateur Prefect et hash restent distincts. Publication inconnue : `NULL`. SCAD donne un jour de modification, conservé comme `DateField`, sans heure inventée.
- Pour l’archive ADEK, `acquisition_method=manual_archive_import`, `timestamp_basis=artifact_filesystem_time`, `fetched_started_at=NULL`. Le temps conservé est celui du fichier capturé sur Windows, approximatif pour la réception HTTPS. Il ne devient ni une date de publication ni une nouvelle collecte au moment du replay.
- Le même flow run terminé se réutilise sans réécrire. Une nouvelle acquisition réussie ajoute un snapshot ; aucun truncate, effacement ou retrait automatique des identités absentes.
- Les lectures utilisent uniquement la dernière version réussie, ordonnée par date de capture puis création. Une archive plus ancienne ne remplace pas une collecte récente dans l’interface.
- Une réponse vide, un schéma invalide, une identité dupliquée ou une géométrie incorrecte bloque le lot. Une baisse de couverture supérieure à 20 % demande une revue ; la version précédente reste consultable. Les captures d’échec disponibles restent conservées.
- PostgreSQL contrôle unicité par snapshot, champs d’audit, types, valeurs et coordonnées/topologie. Une migration refuse les tables homonymes sur le `search_path` avant de placer les tables dans leur schéma.

Pour consulter depuis la console SQL de PyCharm/pgAdmin :

```sql
SELECT s.dataset, s.source_row_count, s.source_modified_date,
       c.fetched_at, c.timestamp_basis, c.acquisition_method, r.actor
FROM evidence.public_context_snapshot s
JOIN evidence.capture c ON c.id = s.capture_id
JOIN evidence.ingestion_run r ON r.id = s.run_id
ORDER BY c.fetched_at DESC;

SELECT name, planned, facility_type, ST_AsText(location)
FROM evidence.health_facility_observation
LIMIT 20;
```

Ne pas additionner les lignes de tous les snapshots pour obtenir l’effectif actuel. Les anciennes observations sont volontairement présentes.

## Où est le code

Tous ces chemins partent de `C:\Users\Karim\Repositories\property-platform\` :

| Chemin complet | Responsabilité |
|---|---|
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\abu_dhabi.py` | URLs fermées, parsing inerte, formats, périmètres et validation des archives |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\context_import.py` | Transactions, snapshots, modèles propriétaires, garde de couverture |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\models.py` et `migrations\` | Tables, relations et contraintes |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\collectors\context.py` | Acquisition HTTPS et replay des reçus avant la transaction SQL |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\flows.py`, `registry.py`, `domain.py` | Ordonnancement, paramètres et passerelle Django |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\publication\context_preview.py` | Lectures limitées et dernière version exploitable |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\api\public_context.py` | Contrat HTTP local |
| `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\public-context.tsx` | Interface, recherche, pagination, langue et dates |
| `C:\Users\Karim\Repositories\property-platform\scripts\prepare_context_archive.py` | Préparer un reçu d’un document officiel obtenu manuellement |

Trajet : **Prefect → collecteur → reçus → passerelle Django → validation et transaction → PostGIS → API → web**. Ni réseau ni JavaScript du producteur ne s’exécutent au clic de l’utilisateur. Les bibliothèques, lockfiles et runtimes existants sont conservés ; aucune dépendance OCR, raster ou navigateur automatisé ajoutée aux services.

## Installation et lancement

Sur le poste actuel, les migrations/imports ont déjà été réalisés. Consulter le site suffit. Sur une autre installation, ouvrir PowerShell dans `C:\Users\Karim\Repositories\property-platform`, puis exécuter **une commande à la fois** :

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion build api ingestion
docker compose -f infra/local/compose.yaml up -d api
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion up -d prefect ingestion
```

`build` prépare le nouveau programme ; `up` démarre/remplace ses conteneurs ; `migrate` crée les structures ; aucun de ces trois gestes ne collecte les sources. Le runner enregistre les procédures dans [Prefect](http://localhost:4200). Ouvrir **Deployments**, rechercher un nom du tableau puis **Run**. Examiner **Flow Runs**, statut, résumé et logs avant d’activer son calendrier. Le run conserve son identité dans la base métier.

Voir [INGESTION.md](INGESTION.md) pour le build avec l’autorité TLS approuvée sur ce poste, les horaires, l’arrêt et les erreurs. Ne pas désactiver TLS. Une réponse 401/403 reste un refus d’accès ; aucun secret de frontend ou CAPTCHA n’est utilisé pour la contourner.

## Archive ADEK

Ce parcours sert à un **document original effectivement obtenu depuis le lien officiel public**, avec son origine et son statut de réception vérifiés. Le script ne télécharge rien, ne récupère aucun identifiant de connexion et ne transforme pas un fichier quelconque en preuve officielle. Conserver le fichier original et sa trace de réception.

Après obtention du GeoJSON depuis [le fichier public du portail](https://charterschools.abudhabi/documents/d/charterschools/schools), placer le document sous `.cache/acquisitions/adek-schools.geojson`. Depuis la racine :

```powershell
.\apps\ingestion\.venv\Scripts\python.exe scripts/prepare_context_archive.py --input .cache/acquisitions/adek-schools.geojson --output .cache/acquisitions/adek-school-archive.json
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion cp .cache/acquisitions/adek-school-archive.json ingestion:/data/adek-school-archive.json
```

L’environnement Python du premier bloc est celui installé selon [INGESTION.md](INGESTION.md). Le script contrôle le JSON, ses identités et coordonnées, calcule le SHA-256 et enregistre l’heure du fichier comme **approximative**. Il ne faut pas modifier le fichier original avant cette préparation ou lui attribuer une heure de publication. Le reçu est privé et ignoré par Git.

Dans Prefect, lancer `abu-dhabi-schools` avec `receipt_name` égal à `adek-school-archive.json` et `actor` égal à `Karim`. Le runner lit uniquement ce nom sous `/data`, vérifie périmètre, hash, taille et temps, puis passe par le service métier habituel. Une reprise conserve la date de l’archive. **Laisser le calendrier inactif** tant que le canal automatique officiel reste refusé.

## Consultation dans le site

[Ouvrir l’émirat](http://localhost:3102/en/explore?territory=abu-dhabi) : le panneau de contexte et le marché ADREC lisent PostgreSQL. Sur Reem/Saadiyat, ouvrir l’onglet **Neighbourhood**. Le sélecteur de données propose santé, Charter schools, bus, statistiques et districts ; rechercher un nom/lieu puis utiliser la pagination.

Le panneau indique **tout l’émirat** même depuis une île. Aucun de ces effectifs n’est présenté comme le nombre d’équipements sur Reem ou à distance de marche. Pour les écoles, l’arabe officiel est privilégié dans l’interface arabe ; les autres noms et grades restent dans leur langue source. Les textes de l’interface sont traduits dans les quinze langues, avec RTL.

La nouvelle option de sélection de zone permet de revenir à l’émirat. Sa vue de données ne déclare pas une carte parcellaire complète : les géométries de parcelles/bâtiments actuellement affichées restent celles des deux îles. Les couches de secteurs restent non cliquables, et le clic sur un bien ne reçoit pas de nouvel auto-zoom.

## Carte d’ensemble et districts officiels

La route sans territoire, par exemple [l’exploration en français](http://localhost:3102/fr/explore), ouvre désormais **Toute la zone / Whole area → Abu Dhabi**. Changer d’émirat garde ce niveau général. Choisir Reem ou Saadiyat ouvre la carte détaillée de l’île. Les anciens liens qui ne contiennent qu’un UUID de parcelle gardent le contexte Reem pour leur compatibilité.

Un **émirat** contient plusieurs **municipalités** ; le jeu Onwani fournit ici des **districts**. Une île peut être un district, mais un secteur comme RT7 est un niveau plus fin. Ne pas assimiler systématiquement district, quartier commercial, communauté et ville.

La vue d’ensemble affiche les 216 limites officielles et un annuaire consultable en anglais/arabe, filtrable par municipalité : Abu Dhabi (ADM), Al Ain (AAM), Al Dhafra (WRM). Les noms originaux restent ceux du producteur. Les boutons Reem et Saadiyat ouvrent les biens effectivement collectés ; les autres districts ne sont pas présentés comme disposant déjà d’un catalogue immobilier complet.

Le pipeline existant **abu-dhabi-districts**, programmé le dimanche à 12 h, heure de Dubai, acquiert les identifiants avant/après et les limites auprès de DMT / Onwani. Il conserve les acquisitions historiques et actualise le dernier snapshot complet. La table est `property_platform.evidence.district_boundary_observation`, liée à `property_platform.evidence.public_context_snapshot` et aux captures. Aucun second pipeline, table dupliquée, migration ou import manuel n’est nécessaire pour cette vue sur le poste déjà alimenté.

`/api/v1/preview/district-map`, relayé par `/api/atlas/district-map`, lit seulement la base. Le serveur produit une simplification de **20 mètres** pour l’affichage ; la géométrie originale, les bornes et le point intérieur d’étiquette sont conservés. La réponse est bornée à 500 districts ; un dépassement échoue au lieu de tronquer silencieusement. Une version explicite identifie cette géométrie d’affichage. Les accès restent limités à l’aperçu local comme les autres données.

Les liens vers les cartes détaillées utilisent le couple officiel **municipalité + DISTRICTID** : ADM/57 pour Reem et ADM/1347 pour Saadiyat. Une ressemblance de nom ne crée pas un rattachement. Ajouter un autre district détaillé demande un profil de collecte examiné et ses imports ; ajouter seulement son nom ne suffit pas.

Fichiers principaux :

- `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\publication\context_preview.py` : lecture et projection de carte.
- `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\api\public_context.py` : contrat HTTP typé et garde d’aperçu.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\district-overview.tsx` : annuaire et parcours vers les îles.
- `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\district-map.tsx` : carte des limites.
- `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\registry.py` : déploiement et horaire existants.

## Sources restant à qualifier

L’[inventaire national](../product/SOURCES_DONNEES_UAE.md) reste un registre de pistes, pas une liste d’imports tous exécutables.

| Source | Constat de cette extension | Suite possible |
|---|---|---|
| DARI projets | Annuaire public visible : 325 résultats lors de la revue. Endpoint observé `api.dari.ae/property-service/api/v1/property/project` : **401 sans autorisation** | Obtenir un canal/API/export autorisé auprès du producteur ; ne pas copier les credentials du frontend. Aucune fiche DARI inventée dans la base. |
| ADEK écoles privées / Irtiqaa | L’ancien dashboard `maps.adek.gov.ae/psdashboarden/` n’a pas été résolu depuis le poste | Trouver l’annuaire actuel et ses ressources ; les 37 Charter ne remplacent pas ce registre. |
| NCM qualité de l’air | Le site annonce `/api/?action=aqi`, mais une lecture directe retourne **404** | Qualifier le canal documenté courant, l’horodatage et les droits ; aucune mesure fabriquée ni station affectée à un bâtiment. |
| DMT Digital Twin | Annonce publique, aucun export exploitable qualifié | Export/licence ou partenariat ; pas de modèle 3D généré depuis une annonce. |
| FGIC / Bayanat | Portails de recherche, sans ressource Abu Dhabi supplémentaire qualifiée ici | Identifier fichiers, granularité et licence de chaque jeu. |
| Overture / Geofabrik / Microsoft footprints | Pistes ouvertes ; aucune extraction complète de l’émirat ou nouvelle correspondance d’identité validée dans cette extension | Runtime de collecte adapté aux gros fichiers, version/licences, mesure de couverture et rapprochements réversibles avant élargissement. OSM des deux îles reste en place. |
| Copernicus, SRTM, WorldCover, Wikidata, Commons | Pas de nouveau jeu/artefact Abu Dhabi qualifié et ingéré dans cette extension | Traiter les besoins précis de scènes, relief, alias ou photos avec droits et dates ; éviter le téléchargement mondial indiscriminé. Les anciens aperçus Sentinel restent disponibles. |

Les données foncières privées, comptes séquestres, titres et dossiers de propriétaires ne sont pas aspirés. Des sources intéressantes peuvent nécessiter un accord ; leur présence sur un site gouvernemental n’établit pas un accès automatique autorisé.

## Validation

Les suites couvrent la complétude des districts, les types, archives altérées, publication/collecte distinctes, unicité et contraintes SQL, reprise, rollback et conservation du dernier snapshot. Les tests GIS utilisent une vraie base PostGIS isolée ; les données du poste ne sont pas une fixture de test. Les dictionnaires sont contrôlés pour les quinze langues. Les effectifs de ce guide proviennent des imports réels, pas des tests.

Les résultats finaux, builds et vérification du navigateur sont consignés avec la livraison. Les refus 401/403/404 ci-dessus restent des limites de source, pas des imports annoncés réussis.


Résultats locaux : **237 tests API/PostGIS réussis**, **84 tests ingestion réussis** et un test de liens symboliques réservé à Linux ignoré sous Windows ; **21 tests web réussis**. Ruff/format, Biome, les deux contrats Import Linter, les contrats générés, les liens des 33 documents, Django check et l’absence de migrations manquantes sont validés. Les images API/ingestion/web sont construites avec TLS vérifié ; Next.js compile les quinze langues et passe son contrôle TypeScript. Le navigateur confirme les recherches anglaises, la provenance de l’archive et les noms arabes. Les lectures locales ont renvoyé les cinq effectifs attendus et les 6 747 ventes, sans réseau vers les producteurs.

Prefect contient **26 déploiements et 22 calendriers actifs** sur ce poste après cette extension. Les cinq nouveaux horaires automatiques sont vérifiés actifs ; ADEK est vérifié inactif. Les six imports ont un run terminé avec écritures en PostgreSQL ; le premier refus ADEK reste enregistré. Ces contrôles locaux ne valent pas validation d’un déploiement de production ou résultat observé de CI distante.

Le compilateur **TypeScript 7** du dépôt passe également dans le runtime Linux du build (`typecheck`), en plus du contrôle TypeScript embarqué de Next.js. Le dernier contrôle ciblé de contexte vérifie aussi qu’un changement de politique d’arrondi SCAD est refusé.

### Vérification de la carte d’ensemble et des clics — 14 octobre 2026

Dix tests ciblés sur PostGIS réel passent pour les snapshots, la navigation typée et le garde d’aperçu ; les 24 tests web passent, dont les étiquettes, empreintes avec trous et priorité de petite parcelle sous RT7 TMP2. Le compilateur TypeScript 7 et le build Next.js des quinze langues passent dans l’image Docker. La génération Next.js native Windows rencontre toujours la limite du cache SWC documentée ; les mêmes vérifications ont réussi dans Linux sans désactiver les protections.

La vérification navigateur a confirmé : défaut Toute la zone, 216 districts, recherche Saadiyat puis accès à sa carte, retour au niveau émirat, noms arabes et RTL, disposition carte/annuaire sur ordinateur et empilement sur petit écran, sélection réelle de RT7 · 3 au lieu de TMP2, fiche Leaf Tower au clic et secours TMP2 sur un point sans petite parcelle. Les images locales de vérification restent sous `C:\Users\Karim\Repositories\property-platform\.cache\validation\`, ignorées par Git.
