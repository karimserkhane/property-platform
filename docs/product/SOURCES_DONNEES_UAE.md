# Sources publiques et ouvertes pour Property Platform

Revue du **13 octobre 2026**. Cet inventaire contient **44 entrées de sources, jeux de données ou pistes institutionnelles**. Plusieurs entrées appartiennent à une même autorité ; ce n’est pas une liste de 44 fournisseurs indépendants. Il couvre les sept émirats, avec des niveaux d’accès très différents. Il documente la recherche ; il n’active pas de nouveaux imports.

La valeur recherchée est une fiche immobilière documentée : projet, promoteur, statut, avancement daté, caractéristiques, ventes, loyers, charges et environnement. Une carte cadastrale apporte la localisation ; les autres sources apportent les informations nécessaires pour comprendre le bien.

## Sommaire

- [Lire les niveaux de vérification](#lire-les-niveaux-de-vérification)
- [Abu Dhabi](#abu-dhabi)
- [Dubai](#dubai)
- [Ajman](#ajman)
- [Sharjah, Ras Al Khaimah, Fujairah et Umm Al Quwain](#sharjah-ras-al-khaimah-fujairah-et-umm-al-quwain)
- [Sources nationales et environnement du quartier](#sources-nationales-et-environnement-du-quartier)
- [Données ouvertes internationales](#données-ouvertes-internationales)
- [Accès techniques vérifiés](#accès-techniques-vérifiés)
- [Ordre conseillé pour les prochains pipelines](#ordre-conseillé-pour-les-prochains-pipelines)
- [Règles de qualification avant import](#règles-de-qualification-avant-import)

## Lire les niveaux de vérification

| Niveau | Signification |
|---|---|
| **Intégré** | Le dépôt possède déjà un connecteur ou un import pour un périmètre précis. Cela ne prouve pas une couverture nationale. |
| **API vérifiée** | Une réponse JSON publique de métadonnées a été obtenue pendant cette revue, sans clé ni compte. L’import complet reste à réaliser et tester. |
| **Documenté** | Une page de l’autorité ou la documentation du producteur confirme les données ou le service. Le téléchargement métier n’a pas été testé. |
| **À qualifier** | Portail, export, accès ou droits restent à vérifier ; aucune automatisation prête n’est affirmée. |
| **Piste** | Autorité ou initiative identifiée, sans jeu ouvert exploitable confirmé. |

**Officiel**, **ouvert** et **automatisable** sont trois propriétés distinctes. Un service officiel peut demander une authentification, un CAPTCHA, un accord ou des frais. Une donnée communautaire peut avoir une licence ouverte tout en restant incomplète. La fiabilité doit être évaluée pour chaque assertion : existence d’un permis, identité commerciale, prix passé, géométrie ou observation satellite.

## Abu Dhabi

| ID | Source primaire | Informations utiles | Accès et intérêt pour la plateforme |
|---|---|---|---|
| 01 | [ADREC — Market Data](https://adrec.gov.ae/en/market-data) | Ventes et indices publiés | **Intégré** pour Reem/Saadiyat ; voir [ADREC.md](../engineering/ADREC.md). Historique de marché, avec contrôle des séries ambiguës. |
| 02 | [DARI, confirmé par la FAQ ADREC](https://adrec.gov.ae/en/faqs) ; [portail](https://www.dari.ae/) | Projets enregistrés, taux d’avancement, références de compte séquestre | **Documenté / à qualifier**. Priorité élevée pour enrichir les fiches de projets ; aucun export massif ou API publique confirmé ici. |
| 03 | [DMT — Onwani](https://pages.dmt.gov.ae/en/onwani) | Adresses ; nos connecteurs lisent aussi parcelles, usages et attributs de permis disponibles | **Intégré** pour les deux îles. Étendre les profils territoriaux après vérification des couches et identités ; pas de couverture automatique de tout Abu Dhabi. |
| 04 | [SCAD — Census / Real Estate](https://census.scad.gov.ae/home/realestate?lang=en&tab=tool_interactive_unit) | Stocks de bâtiments et unités, catégories et régions | **Documenté**, tableaux/statistiques. Utile pour contextualiser l’offre. Résultats agrégés et arrondis : ne pas les transformer en registre individuel d’appartements. |
| 05 | [DMT — Abu Dhabi Digital Twin](https://www.dmt.gov.ae/en/Media-Centre/News/News_EN_AR_12_10_22) | Initiative de représentation et analyse urbaine | **Piste**, annonce de 2022. Accès actuel, exports 3D et droits non confirmés ; ne pas promettre de récupérer le jumeau numérique. |

La FAQ ADREC recommande explicitement DARI pour l’avancement des projets. Cela en fait une meilleure piste pour ces faits que la seule recherche de noms dans des transactions. Les démarches TAMM/DARI réservées aux propriétaires ou professionnels ne deviennent pas des jeux ouverts du seul fait qu’elles sont décrites publiquement.

## Dubai

| ID | Source primaire | Informations utiles | Accès et intérêt pour la plateforme |
|---|---|---|---|
| 06 | [DLD — Real Estate Data, projets](https://dubailand.gov.ae/en/open-data/real-estate-data/) | Identifiants projet/promoteur, statut, avancement, inspection, dates et unités | **Documenté**, CSV annoncé, CAPTCHA présent. Priorité pour les fiches immobilières de Dubai. |
| 07 | [DLD — ventes et loyers](https://dubailand.gov.ae/en/open-data/real-estate-data/) | Prix, surfaces, typologies, périodes et projets | **Documenté**, CSV annoncé. Comparables historiques ; qualifier les identifiants et périodes de chaque export. |
| 08 | [DLD — terrains, bâtiments et unités](https://dubailand.gov.ae/en/open-data/real-estate-data/) | Références, caractéristiques, étages et surfaces | **Documenté**. Relations entre actifs à vérifier ; la présence d’une référence foncière ne garantit pas une géométrie exportable. |
| 09 | [DLD — promoteurs](https://dubailand.gov.ae/en/open-data/real-estate-data/) | Enregistrement, identité et licence | **Documenté**. Référentiel professionnel, avec conservation des dates de validité. |
| 10 | [DLD — Project Status Enquiry](https://backoffice.dubailand.gov.ae/en/eservices/real-estate-project-status-landing/) | Consultation de l’avancement d’un projet | **Documenté**, recherche par projet ou terrain. Vérification ciblée ; pas d’API de collecte massive confirmée. |
| 11 | [DLD — Service Charge Index](https://dubailand.gov.ae/en/eservices/service-charge-index-overview/service-charge-index/) | Charges approuvées par projet, usage et année | **Documenté**, formulaire/CAPTCHA et export PDF affichés. Valeur forte pour la comparaison du coût de possession ; accès automatique à qualifier. |
| 12 | [Dubai Municipality — Construction & Development](https://www.dm.gov.ae/open-data2/) | Permis de construire et de démolir annoncés | **Documenté / à qualifier**. Les anciens liens de catalogue doivent être résolus avant import. |
| 13 | [Dubai Municipality — informations de bâtiments/projets](https://www.dm.gov.ae/open-data2/) | Usages, niveaux et résumés de bâtiments | **Documenté / à qualifier**. Complément des informations commerciales ; contrôler le schéma réel des fichiers. |
| 14 | [Dubai Municipality — Makani](https://www.dm.gov.ae/open-data2/) | Service de géolocalisation et adressage | **Documenté / à qualifier**. Positionnement d’entrées ; une entrée n’est pas nécessairement un bâtiment, projet ou terrain. |
| 15 | [Dubai Here / GeoDubai — GIS Projects](https://www.dm.gov.ae/municipality-business/planning-and-construction/geographic-information-systems/gis-projects/) | Cartographie 2D/3D, actifs et infrastructures décrits par la municipalité | **Documenté / à qualifier**. Piste pour géométries et contexte urbain ; exports libres et accès de notre plateforme non établis. |
| 16 | [Data.Dubai — présentation officielle](https://www.digitaldubai.ae/apps-services/details/data.dubai) ; [portail](https://data.dubai/en/) | Catalogue transversal, statistiques et services de données | **Documenté**. Distinguer les données ouvertes des jeux partagés nécessitant une demande. |

**Changement important de point d’entrée :** le lien historique `https://www.dubaipulse.gov.ae/data/dm-general/dm_building_permits-open` a répondu à notre requête HTTPS, mais son URL finale était **`https://data.dubai/en/`**. Le contenu reçu était un accueil, pas la fiche des permis. Un statut HTTP 200 ne prouve donc pas l’accès au jeu recherché. Retrouver sa fiche actuelle, ses ressources et sa licence dans Data.Dubai avant de développer le collecteur.

[Digital Dubai décrit les modalités d’accès](https://partnersportal.digitaldubai.ae/Services/Details/c64fcb52-534f-4831-815f-ab5d4aed38b6) : consultation/téléchargement pour les données ouvertes ; demande et connexion pour les jeux partagés ; frais éventuels selon le service. La [page de Dubai Municipality](https://www.dm.gov.ae/open-data2/) demande de citer la source. Cela ne dispense pas de vérifier les conditions particulières du fichier courant.

## Ajman

Les cinq jeux 17 à 21 ont été vérifiés directement : **métadonnées JSON publiques HTTP 200**, éditeur **Department of Land and Real Estate Regulation**, licence déclarée **CC BY 4.0**. Les chiffres ci-dessous sont les effectifs du catalogue à la date de revue, pas des comptes de ventes individuelles.

| ID | Jeu officiel | Utilité | Métadonnées observées et limites |
|---|---|---|---|
| 17 | [Real Estate Units Sales](https://data.ajman.ae/explore/dataset/real-estate-units-sales/?flg=en-gb) | Valeurs et nombres de ventes par projet, quartier et typologie | **API vérifiée** ; 6 075 lignes ; cadence déclarée trimestrielle ; traitement le 21 août 2026. Agrégats, pas une transaction par ligne. |
| 18 | [Real Estate Units Transactions](https://data.ajman.ae/explore/dataset/real-estate-units-transactions/api/?flg=ar) | Activité immobilière agrégée | **API vérifiée** ; 6 299 lignes ; trimestriel ; traitement le 21 août 2026. Ne pas additionner aveuglément avec le jeu de ventes. |
| 19 | [Completed Real Estate Development Projects](https://data.ajman.ae/explore/dataset/completed-real-estate-projects/) | Projets, promoteurs, unités et localisation textuelle | **API vérifiée** ; 496 lignes ; `project_id` présent ; traitement le 19 janvier 2026 ; cadence non déclarée. Priorité élevée pour de vraies fiches nommées. |
| 20 | [Management companies for Real Estate Development Projects](https://data.ajman.ae/api/explore/v2.1/catalog/datasets/management-companies-for-real-estate-development-projects) | Société de gestion associée au projet | **API vérifiée** ; 451 lignes ; `project_id`, `office_id`, année ; cadence annuelle ; traitement le 9 juin 2026. Gestionnaire et promoteur sont des rôles distincts. |
| 21 | [Real Estate Offices Classification](https://data.ajman.ae/api/explore/v2.1/catalog/datasets/real-estate-offices-classification) | Classification officielle des agences, datée | **API vérifiée** ; 3 159 lignes ; `office_id`, résultat et date ; traitement le 3 juin 2026. Ce n’est pas une note de qualité d’un bâtiment. |
| 22 | [Ajman Municipality & Planning — Open Data](https://www.am.gov.ae/en/open-data/) | Catalogue municipal, données spatiales et infrastructures | **Documenté**. Jeux précis, granularité et ressources à qualifier ; ne pas supposer un cadastre public exhaustif. |

Les métadonnées de ventes contiennent noms de projets anglais/arabe, secteurs, districts, types, chambres, montants, effectifs, année et trimestre. Elles ne fournissent pas le `project_id` du jeu de projets dans le schéma examiné. Un rapprochement par noms reste donc une décision à documenter et rendre réversible. Les cinq schémas vérifiés n’exposent pas de champ géométrique : une carte nécessite une autre preuve de localisation.

Les montants manquants doivent rester inconnus. Une moyenne trimestrielle éventuelle utilise la valeur totale divisée par le nombre de ventes correspondant, avec périmètres compatibles ; elle ne devient pas le prix d’une unité précise.

## Sharjah, Ras Al Khaimah, Fujairah et Umm Al Quwain

| ID | Source | Informations utiles | État réel de qualification |
|---|---|---|---|
| 23 | [Sharjah Real Estate Registration Department, résultats relayés par Sharjah24](https://sharjah24.ae/en/Articles/2026/04/14/aa3) | Publications de marché et activité par période | **Documenté**, communiqué relayé. Le site direct `shjrerd.gov.ae` n’a pas été récupéré pendant la revue ; aucun registre ouvert de transactions individuelles confirmé. |
| 24 | [Sharjah Municipality, référencée dans l’annuaire officiel des municipalités](https://mun.rak.ae/uae-municipalities/) | Autorité à examiner pour permis et données urbaines | **Piste**. Portail cible `portal.shjmun.gov.ae` non récupéré ; jeux ouverts précis et API non confirmés. |
| 25 | [RAK Municipality — Lands & Properties](https://mun.rak.ae/home/rak-municipality/organizational-structure/lands-properties-sector/) | Rapports fonciers et immobiliers par période | **Documenté**, rapports proposés. Bon démarrage pour la couverture de RAK ; ne pas les traiter comme une liste d’annonces. |
| 26 | [Ras Al Khaimah Statistics Center — Real Estate](https://css.rak.ae/en/Pages/statistical-themes.aspx?catId=2&subcatId=6) | Séries de marché et valeurs agrégées | **Documenté**, tableaux et publications. Comparaison régionale ; conserver périodes et unités de mesure. |
| 27 | [Fujairah GIS Center](https://gis.fujairah.ae/en/) | Autorité géographique et cadastrale à qualifier | **Documenté** comme fournisseur institutionnel ; export public et licence non établis. Aucun accès aux dossiers privés de propriétaires ou contrats de location n’est proposé. |
| 28 | [Umm Al Quwain Municipality, annuaire officiel](https://mun.rak.ae/uae-municipalities/) | Point de départ institutionnel pour la couverture UAQ | **Piste**. `md.uaq.ae` est référencé mais n’a pas été récupéré ; aucun jeu parcellaire/prix ouvert vérifié ici. |

Cette recherche ne démontre pas une profondeur de données identique dans les sept émirats. Les échecs de récupération ne prouvent ni la fermeture du service ni l’absence de données ; ils empêchent d’affirmer qu’un connecteur est prêt. Commencer avec les publications disponibles et mesurer les lacunes par zone.

## Sources nationales et environnement du quartier

| ID | Source primaire | Informations utiles | Accès et précautions d’interprétation |
|---|---|---|---|
| 29 | [Bayanat, portail national référencé par le ministère des Finances](https://mof.gov.ae/en/open-data/bayanat-ae/) ; [portail](https://bayanat.ae/en) | Recherche de jeux gouvernementaux et statistiques | **Documenté** comme catalogue. Identifier un jeu, son éditeur et sa licence ; le portail ne constitue pas un registre national de biens. |
| 30 | [FGIC — Union Atlas](https://atlas.fgic.gov.ae/uaeatlas/MapsAndGazetteer/AdvancedDigitalApplications?lang=en) | Références cartographiques et géographiques nationales | **Documenté / à qualifier**. Page dynamique peu extractible ; téléchargement et droit de redistribution non établis. |
| 31 | [KHDA — annuaire des écoles](https://web.khda.gov.ae/en/Education-Directory/Schools) | Écoles de Dubai, programmes, frais et inspections | **Documenté**, annuaire public. Enrichissement familial du quartier ; noter l’année d’inspection et l’identité de l’établissement. |
| 32 | [ADEK — School Performance Plaques](https://www.adek.gov.ae/en/Programmes-and-Initiatives/School-Performance-Plaques) | Système Irtiqaa d’évaluation des écoles d’Abu Dhabi | **Documenté** ; accès à un annuaire/export complet à qualifier. Ne pas confondre programme d’évaluation et données effectivement récupérées. |
| 33 | [DoH — Public Health Facility Map](https://stem.doh.gov.ae/publicmap/) | Localisation d’établissements de santé et services décrits | **Documenté** comme carte publique ; API/export à qualifier. Utile pour les équipements proches, pas pour produire une recommandation médicale. |
| 34 | [RTA — Open Data](https://www.rta.ae/wps/portal/rta/ae/home/open-data?lang=en) | Données de mobilité de Dubai à sélectionner | **Documenté**, récupération directe limitée pendant la revue. Ne pas annoncer un flux GTFS/temps réel accessible sans avoir trouvé et testé sa ressource actuelle. |
| 35 | [Abu Dhabi Mobility — Public Transport Services](https://admobility.gov.ae/en/pb-bus-service/) | Lignes et horaires publics | **Documenté**. Accès piéton aux arrêts et dessertes ; des horaires publiés ne garantissent pas un temps de trajet réel. |
| 36 | [NCM — National Air Quality Platform](https://airquality.ncm.gov.ae/?lang=en) | Mesures et indicateurs de qualité de l’air | **Documenté** ; flux, historique et réutilisation à qualifier. Observation de station, avec heure et distance ; aucune exposition annuelle d’un bâtiment déduite d’une lecture ponctuelle. |

## Données ouvertes internationales

Ces producteurs fournissent des données géographiques réutilisables ou documentées. Ils ne remplacent pas l’autorité locale pour les droits de propriété, les permis et l’enregistrement d’un promoteur. Mesurer la couverture effective de chaque zone UAE avant d’en annoncer l’exhaustivité.

| ID | Source du producteur | Utilité | Accès, licence et limites |
|---|---|---|---|
| 37 | [OpenStreetMap](https://www.openstreetmap.org/copyright) et [Geofabrik GCC States](https://download.geofabrik.de/asia/gcc-states.html) | Bâtiments, rues, équipements et chemins | **Intégré** par OSM sur deux îles ; transport Geofabrik non intégré. Extraits publics PBF/GeoPackage, ODbL et attribution. Le fichier GCC dépasse les UAE : filtrer le territoire. |
| 38 | [Overture Maps — documentation](https://docs.overturemaps.org/) | Bâtiments, lieux, réseau et identifiants GERS | **Documenté**, GeoParquet/S3/Azure et extraction par zone. [Licences par thème/source](https://docs.overturemaps.org/attribution/), pas une licence uniforme. Très bonne piste pour combler des lacunes géographiques. |
| 39 | [Microsoft Global ML Building Footprints](https://github.com/microsoft/GlobalMLBuildingFootprints) | Empreintes détectées sur images, hauteur parfois estimée | **Documenté**, CDLA Permissive 2.0. Mesurer couverture UAE et millésime des images ; une détection ne prouve pas le statut légal du bâtiment. |
| 40 | [Copernicus Data Space — STAC](https://documentation.dataspace.copernicus.eu/APIs/STAC.html) | Catalogue Sentinel et observations datées du terrain | **Documenté** pour CDSE. Nos deux aperçus Sentinel utilisent actuellement EarthSearch/AWS ; aucun connecteur CDSE n’est implémenté. Downloads/comptes/quotas selon le canal ; traitement raster séparé du web/API. |
| 41 | [NASA — SRTMGL1](https://search.earthdata.nasa.gov/search?q=SRTMGL1) | Relief régional, environ 30 m | **Documenté** ; conditions/compte selon l’accès. Mesures de février 2000 : interprétation limitée pour les îles et remblais récents. Pas de hauteur de tour ou diagnostic d’inondation à la parcelle. |
| 42 | [ESA WorldCover — Data Access](https://esa-worldcover.org/en/data-access) | Occupation du sol mondiale à 10 m | **Documenté**, GeoTIFF, CC BY 4.0. Millésimes 2020/2021 ; couche de contexte, pas zonage réglementaire actuel. |
| 43 | [Wikidata — Data access](https://www.wikidata.org/wiki/Wikidata:Data_access) | Identifiants, noms multilingues et références de bâtiments connus | **Documenté**, données structurées CC0. Utile pour des alias vérifiables ; couverture non exhaustive et faits commerciaux à confirmer auprès de leur autorité. |
| 44 | [Wikimedia Commons — Reusing content](https://commons.wikimedia.org/wiki/Commons:REUSE) | Photos documentées de lieux et bâtiments | **Documenté**. Licence, auteur et attribution par fichier ; aucune licence unique pour toutes les images. À utiliser après revue du fichier, pas en reprenant indistinctement les photos d’une page web. |

Pour Overture, les [bridge files](https://docs.overturemaps.org/gers/bridge-files/) peuvent fournir des correspondances entre identifiants source OSM et GERS, lorsqu’ils sont présents. C’est une piste plus solide qu’une fusion automatique de bâtiments sur leur seul nom. Elle doit conserver la version de release, la preuve du lien et les possibilités de révocation. Des bâtiments OSM présents dans Overture ne constituent pas une seconde confirmation indépendante.

## Accès techniques vérifiés

Les vérifications suivantes ont porté sur des métadonnées et quelques pages, sans lancer d’ingestion ni modifier la base immobilière. Les JSON d’Ajman sont accessibles depuis le poste avec TLS vérifié, même lorsque le navigateur de recherche ne parvient pas à les restituer.

| Jeu | Métadonnées officielles vérifiées |
|---|---|
| Ventes | [API JSON](https://data.ajman.ae/api/explore/v2.1/catalog/datasets/real-estate-units-sales) |
| Transactions agrégées | [API JSON](https://data.ajman.ae/api/explore/v2.1/catalog/datasets/real-estate-units-transactions) |
| Projets achevés | [API JSON](https://data.ajman.ae/api/explore/v2.1/catalog/datasets/completed-real-estate-projects) |
| Gestionnaires | [API JSON](https://data.ajman.ae/api/explore/v2.1/catalog/datasets/management-companies-for-real-estate-development-projects) |
| Classification d’agences | [API JSON](https://data.ajman.ae/api/explore/v2.1/catalog/datasets/real-estate-offices-classification) |

La [console du portail](https://data.ajman.ae/api-console/explore/v2.1/) documente les lectures/extractions. Les métadonnées confirment schémas, éditeur, licence, cadence lorsqu’elle existe et date de traitement. Elles ne valident pas encore pagination, unicité, stabilité entre lectures, complétude des prix ou jointures avec notre catalogue. La date `data_processed` est une date technique du producteur ; elle n’est pas nécessairement la date de chaque événement.

## Ordre conseillé pour les prochains pipelines

Cette priorité est notre jugement produit/technique, pas une promesse d’accès ou une notation officielle des producteurs.

| Étape | Travail à réaliser | Résultat concret attendu |
|---|---|---|
| 1 | Qualifier les données projets DARI pour Abu Dhabi et DLD pour Dubai : identifiants, statut, avancement et accès autorisé | Fiches de projets plus riches et suivi daté de l’avancement, directement lié au besoin principal |
| 2 | Développer Ajman projets achevés + gestionnaires, puis ventes agrégées | Nouvelle couverture avec API/licence vérifiées ; noms de projets et promoteurs, sans inventer de position précise |
| 3 | Retrouver les ressources courantes de permis et bâtiments dans Data.Dubai ; qualifier Makani/GeoDubai | Extension géographique de Dubai avec références d’actifs et preuves de permis réellement disponibles |
| 4 | Ajouter Overture/Geofabrik pour les lacunes mesurées, avec rapprochements contrôlés | Géométries et équipements supplémentaires à faible coût de données, sans remplacer silencieusement nos identités |
| 5 | Ajouter charges DLD, écoles, santé, mobilité et statistiques régionales selon les accès confirmés | Comparaison du quartier et des coûts, avec dates, périmètres et limites explicites |
| 6 | Étendre satellite, relief, occupation du sol et médias une fois leur utilité mesurée | Historique visuel et contexte territorial ; traitements et budgets séparés des requêtes interactives |

Pour une première intégration rapidement testable, **Ajman projets** est le candidat le mieux qualifié de cette revue. Pour améliorer immédiatement les dossiers du pilote Abu Dhabi, **DARI** est la piste fonctionnelle à examiner en premier. Ces deux objectifs peuvent avoir des ordres différents selon l’accès effectivement obtenu.

Les noms de futurs déploiements, par exemple `ajman-completed-projects` ou `dubai-project-register`, sont des propositions documentaires. Ils ne sont pas enregistrés dans Prefect et ne constituent pas des commandes disponibles. La plateforme conserve actuellement ses imports existants et les vingt déploiements décrits dans [INGESTION.md](../engineering/INGESTION.md).

## Règles de qualification avant import

1. **Établir l’identité du jeu.** Autorité, URL finale, collection, version, périmètre et type de fait. Ne pas confondre catalogue, portail de services et données téléchargeables. Un homonyme commercial comme `datadubai.ae` n’est pas `data.dubai`, portail officiel.
2. **Conserver accès et droits.** Licence exacte, attribution, conditions, accès public/compte/accord, date de revue et éventuels frais. Un CAPTCHA se traite par un canal autorisé ou un export fourni par l’opérateur ; aucun contournement automatique prévu.
3. **Tester un échantillon et sa granularité.** Vente individuelle, agrégat trimestriel, stock, document ou géométrie. Contrôler valeurs absentes, unités AED/m²/ft², périodes, identifiants et limites d’export. Une ligne d’agrégat ne devient jamais une fausse transaction.
4. **Préserver provenance et temps.** Capture brute et hash, paramètres exacts, statut HTTP, publication source connue ou `NULL`, date de l’événement, début/fin de collecte, ingestion, version du mapping et opérateur. Les corrections restent historisées.
5. **Réconcilier avec preuve.** Identité source et namespace stables ; liens candidats séparés des identités acceptées. Les sources géographiques et commerciales ne sont pas fusionnées sur un nom, un rectangle ou une proximité seuls.
6. **Choisir la cadence utile.** Trimestriel, annuel, release géographique ou observation datée. Un passage hebdomadaire peut détecter une modification d’un jeu trimestriel ; il ne rend pas les événements temps réel. Une mesure d’air ancienne doit rester présentée comme ancienne.
7. **Écrire via les modules propriétaires.** Collecteurs et orchestration dans `apps/ingestion`, validations/services métier Django dans `evidence`, publication dans `publication`. Modèles typés par domaine ; pas de table JSON universelle qui mélange permis, prix, images et avis.
8. **Limiter les acquisitions.** URLs enregistrées, TLS, pagination/partitions vérifiées, quotas, tailles et délais bornés. Mettre en quarantaine les conflits ; ne pas écraser la dernière projection exploitable lors d’une collecte partielle. Les fichiers lourds iront vers un stockage objet adapté, avec métadonnées en base.

Les propriétaires, acheteurs, locataires, dossiers personnels, titres privés et fichiers accidentellement indexés ne font pas partie de cet inventaire exploitable. Les plans de paiement, disponibilités commerciales, plans intérieurs et photos de promoteurs demanderont en parallèle des sources de promoteur ou contrats de diffusion spécifiques : les catalogues gouvernementaux ne couvrent pas à eux seuls tout ce besoin.

Les tests effectués ici concernent la disponibilité et les métadonnées citées. Aucun modèle, table, volume Docker, migration, calendrier ou connecteur applicatif supplémentaire n’a été modifié pendant cette recherche.
