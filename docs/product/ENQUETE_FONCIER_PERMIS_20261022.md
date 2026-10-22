# Terrains, chantiers et permis — enquête du 22 octobre 2026

## Résultat principal

Une autre publication officielle AD-SDI livre des objets parcellaires pour Al Maryah, malgré la réponse vide de la couche Onwani utilisée jusqu'ici. Le service `Pub/Generic_Search_WM/MapServer/10` retourne **73 objets, 73 `PLOTID` distincts, tous avec polygones**, pour le district exactement nommé `AL MARYAH ISLAND`. Des requêtes de comptage donnent aussi **2 506 objets pour Reem** et **5 456 pour Saadiyat**. Ces deux derniers comptes ne constituent pas encore un contrôle de leurs identifiants et géométries sur l'ensemble des lignes. [Couche officielle Plots](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/Pub/Generic_Search_WM/MapServer/10).

Ce sont des résultats techniques observés, pas une certification des droits fonciers, de l'exhaustivité ou de la fraîcheur. La licence de republication de cette publication sous `/Pub/` reste à établir ; les conditions du catalogue `/OpenData/` ne lui sont pas attribuées automatiquement. Les données ne sont **pas encore importées** dans la plateforme par cette enquête.

Deux autres résultats utiles : ADGM confirme un annuaire immobilier pour **Maryah et Reem**, via AccessRP ; DMT documente un accès public aux informations de permis via les **QR codes de chantier alimentés par MePS**. L'accès automatique au premier et un exemple exploitable du second restent à qualifier. [ADGM Real Estate Services](https://www.adgm.com/registration-authority/real-estate-services), [annonce DMT du 8 novembre 2024](https://www.dmt.gov.ae/en/Media-Centre/News/New-Guidelines-for-Construction-Signboards-in-the-Emirate-of-Abu-Dhabi).

L'enquête complète l'[inventaire national du 13 octobre](SOURCES_DONNEES_UAE.md), sans présenter les sources déjà connues comme de nouvelles intégrations. Elle concerne d'abord les trois îles actuelles, puis Abu Dhabi et les autres émirats. Le [relevé technique versionné](PUBLIC_SOURCE_PROBES_20261022.json) conserve 39 observations, leurs paramètres, heures UTC et empreintes disponibles, sans exporter de base métier ni publier les polygones collectés. L'heure est celle enregistrée par chaque sonde ; elle ne représente pas uniformément la fin de réception. Deux délais dépassés n'ont ni réponse ni empreinte.

## Méthode et niveaux de preuve

Recherche en anglais et en arabe, avec variantes Maryah / Mariyah / Sowwah / Suwwah, Reem, Saadiyat, plot / parcel / cadastral / site plan, land / construction / building permit, مخطط / قطعة أرض / رخصة بناء. Les recherches ont croisé forums, publications institutionnelles, catalogues GIS, services publics, portfolios de concepteurs et entreprises, brochures et documents réglementaires. Les discussions servent à découvrir des pistes ; les affirmations retenues sont ensuite rattachées à leur producteur.

| Niveau employé | Ce qui a réellement été établi |
| --- | --- |
| **Données testées** | Réponse métier publique JSON, avec compte et/ou échantillon de géométries et attributs sélectionnés. Ce niveau ne valide pas les droits de republication. |
| **Métadonnées testées** | Schéma ou catalogue lisible ; contenu, complétude et actualité non démontrés. |
| **Service documenté** | Le producteur explique le service ; pas de téléchargement métier automatisable validé. |
| **Piste / historique** | Document utile pour investigation, avec précision, date ou correspondance encore insuffisante. |

Contrôles réseau bornés, TLS vérifié, trois requêtes simultanées au maximum, sans compte, achat, formulaire envoyé ou contournement. Attributs sélectionnés sans propriétaires individuels ni coordonnées de personnes. Un HTTP 200 contenant une erreur ArcGIS ou une page HTML ne compte pas comme succès métier. Les observations portent sur le 22 octobre 2026 ; une date de copyright, de collecte, de conception ou d'ingestion ne devient pas une date de mise à jour du terrain.

## 1. Les alternatives GIS concrètes à Onwani

### AD-SDI — Plots, publication de recherche

[Service et description REST/SOAP](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/Pub/Generic_Search_WM/MapServer), [schéma de la couche 10](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/Pub/Generic_Search_WM/MapServer/10).

| Contrôle | Résultat observé |
| --- | --- |
| Filtre exact `UPPER(DISTRICTENG)='AL MARYAH ISLAND'` | 73 objets annoncés ; lecture des 73 lignes sans limite de transfert signalée |
| Identité Maryah | 73 `PLOTID` distincts et non vides ; 73 objets possèdent des anneaux de polygone |
| Localisation Maryah | Coordonnées WGS84 ; emprise des objets : longitude 54.3857979 à 54.3954149, latitude 24.4913636 à 24.5131901 |
| Filtre exact `AL REEM ISLAND` | 2 506 objets annoncés par le serveur ; pas un import complet |
| Filtre exact `AL SAADIYAT ISLAND` | 5 456 objets annoncés par le serveur ; pas un import complet |
| Origine dans les trois lignes Maryah échantillonnées | `ABU DHABI MUNICIPALITY` |

La réponse Maryah contient notamment `PLOTID`, `PLOTNUMBER`, `COMMUNITYENG`, `DISTRICTENG`, `PRIMARYUSEENG` et `SOURCEOFORIGIN`. Les trois premiers numéros examinés sont SS2, C1 et C2, avec leurs secteurs propres. Le numéro de lot seul ne suffit donc pas au rapprochement.

**Qualification restante :** topologie sur PostGIS, réconciliation avec les identifiants Onwani, divisions/fusions, ancienneté, droits et attribution. `PRIMARYUSEENG` est un entier sans domaine renseigné dans la métadonnée du champ : ne pas lui appliquer automatiquement le dictionnaire ou les couleurs d'une autre couche. Le service indique un maximum de 2 000 objets par réponse ; Reem et Saadiyat nécessitent une pagination vérifiée. Une demande de valeurs distinctes testée a retourné des répétitions avec une limite de transfert : ne pas supposer que tous les drapeaux annoncés sont correctement exécutés.

La conclusion précédente reste précisément : **Onwani PLOT était vide pour le test Maryah**, et non « il n'existe aucune source publique de parcelles ». Le nouveau service est une autre publication AD-SDI ; son indépendance vis-à-vis de la base municipale d'origine n'est pas démontrée.

**Complément technique du même jour :** le dictionnaire existe dans `types`, même
si le domaine du champ est vide : 2 correspond à Commercial et 13 à Residential.
L'import SDI vérifie désormais ce dictionnaire propre, les lots complets et la
topologie PostGIS, puis compare les identités et les géométries sans écraser Onwani.
Les 73 parcelles Maryah ont été intégrées dans l'aperçu privé via Prefect. Voir
[les règles et résultats d'intégration](../engineering/MAP_DATA_QUALITY.md).

### AD-SDI — couches OpenData

[Catalogue officiel et conditions](https://sdi.gov.abudhabi/sdi/opendata.html), [MapServer OpenData](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/OpenData/ADSDI_OpenData/MapServer).

| Couche | Données et intérêt | Qualification réelle |
| --- | --- | --- |
| [207 — Developer Projects](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/OpenData/ADSDI_OpenData/MapServer/207) | Polygones, noms, développeur, référence source | Données testées. Intersection avec le contour officiel Maryah : **2** périmètres, `Al Maryah Island` et `Al Maryah Phase 1 & 2`, Mubadala. Ce ne sont pas deux nouvelles tours ni un annuaire exhaustif. |
| [828 — Urban Development Projects](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/OpenData/ADSDI_OpenData/MapServer/828) | Périmètres, `PROJECTID`, nom, entreprise et rôles | Métadonnées et comptes par fenêtres testés. Doublons possibles avec 207 ; ne pas additionner leurs effectifs. |
| [353 — Building](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/OpenData/ADSDI_OpenData/MapServer/353) | Empreinte, hauteur en étages, statut physique, identifiants de permis/chantier, dates | **30** bâtiments intersectent le contour officiel Maryah ; le filtre textuel du district confirme 30. Schéma riche, mais un bâtiment voisin échantillonné avait permis et dates vides. Pas une preuve que ces champs sont remplis sur Maryah. |
| [817 — ADR AddressPoint](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/OpenData/ADSDI_OpenData/MapServer/817) | Adresse, route, district, GUID et QR d'adresse | Données de comptage testées. Intérêt pour joindre les adresses ; un QR d'adresse n'est pas un QR de permis. |
| [27 — Land](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/OpenData/ADSDI_OpenData/MapServer/27) | Objets géographiques terrestres, type, nom | Métadonnées et comptes testés. **Ne pas assimiler cette classe au cadastre des lots.** |
| [21 — Fountain](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/OpenData/ADSDI_OpenData/MapServer/21), [22 — Fountain Surface](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/OpenData/ADSDI_OpenData/MapServer/22) | Points et surfaces de fontaines | La couche 21 compte **3** points dans le contour Maryah. Identification et ancienneté non établies : aucun n'est attribué à la nouvelle fontaine IA. |
| [130 — AutoPermitZones](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/OpenData/ADSDI_OpenData/MapServer/130) | Zones, champ `Name` | Métadonnées seulement ; couche rangée sous **Environmental**. Le nom ne démontre ni permis de construire ni chantiers autorisés. |

Le [FeatureServer associé](https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/OpenData/ADSDI_OpenData/FeatureServer) expose une sélection différente. Les couches 207, 828 et 353 examinées sont dans le **MapServer** ; on ne peut pas remplacer mécaniquement le mot MapServer par FeatureServer.

Les deux lignes Maryah de la couche 207 ont `SHARINGSTATUS_DM=Report`. La signification de cette valeur n'a pas été établie ; elle n'est pas traduite en autorisation de réutilisation.

Les conditions AD-SDI permettent l'usage métier des données effectivement classées Open Data, avec attribution et sous réserve des licences associées. Elles distinguent les couches sensibles, confidentielles ou secrètes dont les métadonnées peuvent être visibles sans téléchargement autorisé. Elles ne garantissent ni exactitude ni exhaustivité. L'emplacement d'un service et la capacité HTTP Query ne remplacent donc pas la qualification de sa classification. [Conditions AD-SDI](https://sdi.gov.abudhabi/sdi/opendata.html).

### AD-SDI / TAMM — Aldar Properties

[Service officiel](https://arcgis.sdi.abudhabi.ae/agshost/rest/services/TAMM/ALDAR_Properties/MapServer), [couche 4 Plots_Poly](https://arcgis.sdi.abudhabi.ae/agshost/rest/services/TAMM/ALDAR_Properties/MapServer/4). **Données testées**, cinq objets de la fenêtre Reem portent explicitement une adresse Reem :

| Nom source | Secteur | Lot source |
| --- | --- | --- |
| Meera | RS3 | C25_C25 |
| The Bridges | RS2 | C27 |
| Reflection B | RS5 | C21_C22 |
| Sun & Sky Tower | RS6 | C10_C11 |
| The Arc | RS6 | C12 |

Ils possèdent chacun une géométrie. C'est un complément concret pour rapprocher des noms commerciaux de codes de lots, **pas** un catalogue exhaustif d'Aldar ou une preuve de disponibilité actuelle à la vente. Maryah retourne zéro dans la fenêtre testée. Le copyright 2018 ne date pas chaque objet ; aucune fraîcheur métier actuelle n'a été établie. Le champ demandé `Area` ressort avec un nom qualifié de table dans la réponse : l'adaptateur devra normaliser explicitement cet alias.

### Éviter les faux comptes géographiques

| Test | Fenêtre rectangulaire Maryah | Contour officiel Maryah |
| --- | ---: | ---: |
| Developer Projects 207 | 10 | 2 |
| Building 353 | 98 | 30 |
| Fountain 21 | 15 | 3 |

La première fenêtre incluait Al Zahiyah, sur le continent ; le bâtiment échantillonné le confirme par son district et sa géométrie. Les fenêtres Reem et Saadiyat se recouvrent aussi. Les comptes exploratoires par rectangles ne doivent jamais être affichés comme des effectifs par île. Les requêtes avec le contour ont réussi en **POST de lecture** ; les longues URL GET avaient retourné du contenu non JSON.

## 2. ADGM : ce qui concerne effectivement Reem et Maryah

| Source primaire | Informations utiles | Accès constaté et conséquence |
| --- | --- | --- |
| [Real Estate Services](https://www.adgm.com/registration-authority/real-estate-services) | Enregistrement immobilier et services pour les deux îles ; annuaire de projets annoncé | Page officielle lisible. Source prioritaire pour vérifier l'autorité et les références de projets. |
| [AccessRP](https://accessrp.adgm.com/), [présentation officielle](https://www.adgm.com/operating-in-adgm/e-services/accessrp) | Annuaire, transactions, projets existants/à venir, services aux terrains et unités | Portail dynamique non exploité ici : extraction textuelle vide et connexion navigateur réinitialisée ; présentation directe en 403. L'indexation de l'annuaire n'est pas une preuve de son contenu ni d'une API publique. |
| [MoU ADGM–DMT, 18 septembre 2024](https://www.adgm.com/media/announcements/adgm-and-dmt-sign-landmark-mou) | Transfert des services immobiliers Reem et collaboration sur urbanisme/infrastructure | Document institutionnel. Il justifie de rechercher des deux côtés, sans attribuer tous les permis à une autorité unique. |
| [Real Property Regulations 2024, partie 18, §151](https://en.adgm.thomsonreuters.com/sites/default/files/net_file_store/ADGM1547_26994_VER1.pdf) | Accès au registre pour les parties concernées ; certificats de recherche sur demande écrite avec frais | Texte officiel consultable via indexation ; récupération directe du PDF bloquée lors d'un essai. Ce n'est pas une API cadastrale ouverte. Le §151(4) traite explicitement les limites des informations Reem enregistrées avant le 1er janvier 2025. Conserver date, origine et qualification de chaque assertion. |
| [Classification commune DMT–ADGM, mars 2026](https://dmt.gov.ae/en/Media-Centre/News/DMT-ADGM-Launch-Unified-Engineering-Classification-System-for-Abu-Dhabi) | Classification des bureaux et entreprises d'ingénierie | Service documenté, utile pour vérifier des acteurs ; pas une liste de permis délivrés. |
| [Consultation sur les terrains commerciaux non développés](https://www.adgm.com/media/announcements/adgm-registration-authority-publishes-consultation-paper-on-proposal-to-enact-undeveloped-commercial-land-regulations), [état officiel des consultations](https://raconsultations.adgm.com/browse) | Piste sur la future traçabilité permis/démarrage/avancement des terrains vacants | Consultation 3/2026 close le 4 octobre. **Adoption non vérifiée** ; aucune taxe ou obligation proposée n'est présentée ici comme une règle en vigueur. La consultation Strata 4/2026 apparaît ouverte jusqu'au 22 octobre. |

Les registres de sociétés, les autorisations commerciales, le registre foncier, l'annuaire de projets et les permis de construire restent des ensembles distincts. Une société domiciliée dans une tour n'en devient pas le promoteur ou le propriétaire.

## 3. Permis, chantiers, infrastructures : meilleures pistes Abu Dhabi

| Producteur et lien | Utilité pour la plateforme | Ce qu'il reste à qualifier |
| --- | --- | --- |
| [DMT — QR codes de chantier / MePS](https://www.dmt.gov.ae/en/Media-Centre/News/New-Guidelines-for-Construction-Signboards-in-the-Emirate-of-Abu-Dhabi) | L'annonce indique un accès public au lieu, numéro, type et aperçu du permis, avec les entreprises concernées et les mises à jour | Trouver un QR réellement publié sur une photo de chantier ou une pièce publique, vérifier sa destination et son accès sans connexion. Aucun permis individuel n'a été récupéré ici. Ne pas énumérer des numéros ou inventer une API MePS. |
| [DMT — Binaa, lancement du 18 juin 2025](https://www.dmt.gov.ae/en/Media-Centre/News/Binaa-Construction-Permits-Platform-Launched) | Nouvelle plateforme d'autorisation, BIM et suivi des demandes | Déploiement initial annoncé pour de nouvelles villas privées. Pas d'export ouvert confirmé ; existence de la plateforme ≠ inventaire public de tous les permis. |
| [Aldar — Tasareeh](https://www.aldar.com/properties/en/tasareeh) | Parcours par étapes : sol, permis phasé, démarrage, inspections, occupation, maintenance/démolition ; modèles documentaires | Services aux parties concernées via TAMM. Utile pour comprendre les documents et jalons ; ni formulaire vierge ni modèle CAD avec codes fictifs ne prouvent un chantier. |
| [DARI — Project Survey / Progress Report](https://services.dari.ae/business-services/request-project-survey-progress-report/?adrec=businessservices) | Rapports de progression, plans de site/projet, permis de construction et de fondations figurent parmi les pièces | Service de dépôt et validation pour professionnels ; pas une publication automatique des pièces jointes. Ne pas confondre rapport d'avancement et livraison des logements. |
| [DARI — catalogue des services](https://services.dari.ae/business-services/) | Site plan, enregistrement de lots hors plan, titres et documents fonciers | Service documenté, accès et qualité du demandeur à respecter. Utilisable pour un futur import de documents apportés avec autorisation. |
| [Procurement Gate — appels d'offres publics](https://supplier.adgpg.gov.ae/pages/tender-list.html) | Détection précoce de voirie, réseaux, aménagement, études ; identités d'entité et références de marché | Page et filtres publics, extraction détaillée non qualifiée ici. Un appel d'offres n'est ni une attribution ni un démarrage. Pièces de soumission et inscription fournisseurs séparées. |
| [DMT / Al Ain — plans d'achats](https://www.dmt.gov.ae/en/aam/Supplier-Services/Projects) | Exemple de plans de travaux et fenêtres de publication au-delà des trois îles | Dates prévisionnelles ; vérifier les avis ultérieurs. Ne pas importer chaque ligne comme un bâtiment commercial. |
| [DoE — Public Register et Public Notices](https://www.doe.gov.ae/Legislation-and-Compliance/Licensing) | Licences, consentements, dérogations et permis pour énergie, eau et refroidissement urbain | La page officielle désigne deux portails publics ; leur chargement a expiré pendant le test. Documents et cartes de desserte à qualifier. Ce sont des autorisations sectorielles, pas des permis de construction immobilière. |
| [EAD — environnement et géographie](https://ead.gov.ae/en/About-Us/What-We-Do/Monitor-and-Manage) | Habitats marins, zones protégées et contraintes contextuelles ; utile à Saadiyat et aux fronts de mer | Portail environnemental décrit officiellement, géométries/licences à vérifier. Aucun registre public exhaustif des études d'impact n'a été identifié. |
| [EAD — reporting environnemental](https://www.ead.gov.ae/en/Join-the-Movement/Government-and-Businesses/Self-Monitoring-and-Reporting-Program) | Comprendre l'existence de rapports et livrables associés aux autorisations environnementales | Obligation de fournir des données à l'autorité ≠ droit public de télécharger les dossiers des entreprises. |
| [ADSC — Investment Plots / Plot Map](https://adsc.gov.ae/investment-plots/plot-map/) | Carte publique d'opportunités foncières sportives, bon complément thématique | Page carte/liste confirmée ; lignes et géométries non obtenues dans l'extraction. Sous-ensemble d'opportunités, pas cadastre général. |

La bonne unité de suivi est un **événement daté et attribué** : annonce, demande, autorisation, travaux préparatoires, démarrage, inspection, certificat de fin/occupation, puis livraison commerciale lorsqu'elle est prouvée. Ces événements peuvent concerner une phase, une infrastructure ou une mission d'étude, sans se rapporter à tout le programme.

## 4. Cas d'enquête : la fontaine IA d'Al Maryah

| Pièce primaire | Ce qu'elle établit | Limite |
| --- | --- | --- |
| [Mubadala, 20 juillet 2025](https://www.mubadala.com/en/news/mubadala-breaks-ground-on-landmark-ai-maryah-island-waterfront-transformation) | Début officiel du Waterfront enhancement ; WET concepteur des jeux d'eau ; promenade et espaces publics | Pas de numéro de lot ou plan cadastral joint dans le texte consulté. |
| [ALNASR — Al Maryah Waterfront](https://alnasruae.com/projects/) | Le constructeur présente le projet pour Mubadala et le classe en cours | Déclaration de son propre portefeuille, sans date d'inspection. La même page présente séparément **Project DIVE**, extension du front de mer des hôtels Four Seasons/Rosewood avec deux îles et leurs infrastructures : conserver les deux périmètres tant que leur relation contractuelle précise n'est pas prouvée. |
| [Green Vision — Waterfront Enhancement](https://www.greenvisioncons.com/project/al-maryah-island/) | Mission de conception de gestion des déchets ; client Mubadala/WET ; période annoncée 2022–2024 | Cette période peut décrire la mission d'étude ; elle ne prouve pas une ouverture en 2024 ni une contradiction avec le démarrage 2025. |
| [Abu Dhabi Media Office, 10 décembre 2025](https://www.mediaoffice.abudhabi/en/economy/mubadala-investment-company-and-aldar-launch-more-than-aed60bn-expansion-of-al-maryah-islands-financial-district/) | Expansion du district financier au nord et évocation de la fontaine dans le programme plus large | Le terrain nord de près de 500 000 m² n'est pas démontré comme le lot cadastral de la fontaine. Ponts proposés et travaux programmés restent des intentions datées. |
| [Utile / OverUnder — urbanisme Al Maryah](https://www.utiledesign.com/project/al-maryah-island/) | Travail de conception et règles d'implantation pour Mubadala, illustrations de masterplan | Portfolio d'urbanisme, sans version approuvée du cadastre ; son statut « Completed » ne signifie pas que toutes les constructions de l'île sont livrées. |

**Conclusion géographique :** la baie et le waterfront sont prouvés comme zone générale ; aucun lien exact fontaine ↔ `PLOTID`, aucune emprise autorisée et aucun numéro de permis n'ont été établis. Les trois points Fountain AD-SDI ne prouvent pas l'identité de cette nouvelle installation. Une illustration ou un centroïde de l'île ne suffit pas à créer un emplacement précis.

**Suite d'investigation ciblée :** pièces publiques de WET/ALNASR et des missions d'ingénierie, QR de chantier publiés, plans de limites de travaux, références d'appels d'offres et documents d'autorisation marine/environnementale s'ils sont rendus publics. Pour les remblais DIVE, il faudra vérifier la version des limites terrestres : c'est une hypothèse de contrôle, pas la conclusion que le cadastre actuel serait erroné.

## 5. Les concepteurs et entreprises donnent parfois le code de lot manquant

- [TCR — Radiant Square](https://tcrgroup.ae/projects_tcr/radiant-square-project/) publie **RT3-13, City of Lights, Reem**, avec client et consultant. Bonne assertion de localisation à croiser avec le cadastre, sans transformer les autres descriptions du chantier en jugement sur le bâtiment.
- [ECG — Reem Hills Phase 2D Town Plaza](https://www.ecgsa.com/reem-hills-phase-2d-town-plaza/) décrit un super-lot d'environ 75 000 m², plusieurs groupes de bâtiments et une mission allant des études aux documents d'exécution/appels d'offres. Le statut « Completed » de son portfolio ne suffit pas à prouver la livraison des logements. Phase et programme parent doivent rester liés.
- [A&M International — profil 2025](https://aminternational.ae/wp-content/uploads/2025/04/1for-website-business-profile-AM-2025.pdf), page PDF 11 / pages imprimées 20–21 : Vista II est associé aux codes **SB10 & SB11**. Aucune correspondance textuelle `SB` n'apparaît dans les 73 `PLOTNUMBER` Maryah reçus. Cela reste une piste de référentiel/alias à résoudre, pas une localisation validée. Le texte indexé de sa fiche web mélangeait aussi un descriptif de musée à Los Angeles ; le chargement direct a ensuite présenté une vérification d'accès. La provenance primaire ne dispense pas de contrôler le contenu.

Les codes de lots d'un ancien masterplan, ceux du registre, les secteurs municipaux et le nom commercial ne sont pas nécessairement interchangeables. Les portfolios aident à découvrir une relation, sans remplacer la preuve géométrique et sa date.

## 6. Autres émirats et zones franches

| Source primaire | Intérêt réel | État / distinction à conserver |
| --- | --- | --- |
| [Dubai Pulse — DLD Registration](https://www.dubaipulse.gov.ae/organisation/dld/service/dld-registration?dataset=dld_units-open-api&organisation=dld&page=1&service=dld-registration) | Projets, bâtiments, unités et identités DLD | Catalogue indexé ; API « Get Access » et conditions propres. Les pages individuelles ont expiré pendant cette enquête ; pas de nouvelle API ni d'effectifs vérifiés. Voir les sources Dubai déjà recensées dans l'inventaire national. |
| [Dubai Pulse — DM Building Permits](https://www.dubaipulse.gov.ae/data/dm-general/dm_building_permits-open) | Piste d'applications de permis par lot | Référence découverte via des réutilisateurs ; page officielle non récupérée ici. État **à qualifier**, aucune licence ou granularité déduite des tableaux des concurrents. |
| [Dubai Municipality — services GIS](https://www.dm.gov.ae/municipality-business/planning-and-construction/geographic-information-systems/) | Données spatiales, terrains, bâtiments et plans selon habilitation | Demande officielle possible pour plusieurs catégories d'acteurs ; accès Amakin explicitement réservé aux entités gouvernementales connectées au GIN. Pas un cadastre libre d'accès démontré. |
| [DLD — Property Map Request](https://dubailand.gov.ae/en/eservices/property-map-request/) | Plans officiels de terrains, immeubles, unités et parties communes | Démarche propriétaire/représentant avec conditions et frais, pas téléchargement public en masse. |
| [DDA — Site Plan Issuance](https://dda.gov.ae/ar/planning-development/master-planning/site-plan-issuance), [Buildings eServices](https://webzoning.dda.gov.ae/Zoning) | Plans dans le périmètre de l'autorité de développement | Service pour propriétaire, master developer ou représentant, portail avec connexion. Ne pas traiter DDA comme une autorité couvrant Reem ou tout Dubai. |
| [Trakhees / PCFC — obtention de site plan et lease drawing](https://pcfc.ae/en/Service%20Documents/PCFC-TRK-CED-PL-CP-02%2C%20Obtaining%20Site%20Plan%2C%20Lease%20drwg.pdf) | Plans et règles des zones concernées par Trakhees | Procédure officielle et périmètre spécifique ; aucun fichier cadastral ouvert n'est démontré par cette procédure. |
| [DIFC — Registrar of Real Property](https://www.difc.com/business/registrars-and-commissioners) | Autorité foncière propre, enregistrements et manuel de démarches | Service documenté, pas de cadastre GIS public qualifié ; registre foncier distinct des registres de sociétés et sûretés. |
| [Masdar City — brochure officielle](https://www.masdarcity.ae/docs/default-source/general-information/masdar-city-commercial-office-portfolio.pdf?sfvrsn=f59556ac_7) | Terrains à acheter/louer en Musataha, opérations et opportunités de développement | Source primaire de programme et type de tenure ; pas d'inventaire public de polygones/occupations validé. |
| [KEZAD — Business Facilities](https://www.kezadgroup.com/business-facilities/) | Terrains viabilisés, secteurs, logistique, build-to-suit et périmètres free zone/mainland | Offre et services officiels, pas un cadastre général. Le registre de licences d'entreprise est une autre ressource. |
| [RAK — Urban Planning / GIS](https://mun.rak.ae/home/rak-municipality/organizational-structure/urban-planning-and-development-sector-2/), [manuel RAK Geo Map](https://maps.rak.ae/Addressing/static/media/manual_Ar.da0dac72.pdf) | Fournisseur géographique et système d'adressage | Documentation institutionnelle, manuel de 2021 ; API ouverte, droits et couverture actuelle non établis. |
| [Sharjah — annuaire gouvernemental SEDD 2025](https://sedd.ae/documents/32114/0/Industrial%2BDirectories%2B2025%2BArabic%2BS%2B%282%29.pdf/40a63112-8346-8f20-91fc-8f80a91060f8?t=1736921132112), [SDTPS](https://www.sdtps.gov.ae/portlets2/eservicesUsageReport.do) | Plans officiels, urbanisme et service « connais ton emplacement » | Services administratifs, pièces et habilitations à vérifier ; pas de cadastre ouvert inféré de l'existence d'un service. |
| [Portail national — plateformes géospatiales](https://u.ae/en/about-the-uae/digital-uae/data/geospatial-data-platforms) | 1Map, Bayanat, Ajman Geo Map, AD-SDI ; point de départ pour les autres territoires | Bon annuaire d'autorités, sans preuve de polygones parcellaires ouverts nationaux. Les pistes Ajman, Fujairah et UAQ de l'inventaire précédent restent à qualifier pour ce besoin précis. |

L'intérêt de ces sources hors périmètre actuel est d'identifier les producteurs et les mécanismes réutilisables. Aucune couverture nationale des parcelles ou des permis n'est annoncée comme acquise.

## 7. Ce que les forums ont apporté, et ce qui a été écarté

| Discussion / piste publique | Apport | Qualification |
| --- | --- | --- |
| [Recherche de statistiques et données à l'unité](https://www.reddit.com/r/offplanabudhabi/comments/1tqsjyq/abu_dhabi_real_estate_stats/) | Renvoie aux tableaux et rapports ADREC ; confirme le besoin de distinguer statistiques agrégées et données projet/unité | Piste de recherche, pas un registre cadastral. |
| [Débat sur la transparence des données Abu Dhabi](https://www.reddit.com/r/AbuDhabi_Real_Estate/comments/1qhzxdb/opinion_why_abu_dhabi_real_estate_is_years_if_not/) | Fait ressortir des besoins d'historique, de couverture et de charges ; commentaires contradictoires et texte déclaré structuré avec IA | Aucune affirmation de qualité, droit ou rendement reprise comme un fait. |
| [Signalement d'une possible interruption ADREC](https://www.reddit.com/r/abudhabi/comments/1wutjar/has_adrec_stopped_publishing_transaction_data/) | Piste pour les alertes de fraîcheur et trous de séries | Résultat indexé, page directe non récupérée ; **interruption non confirmée**. |

Des recherches ciblées sur SkyscraperCity et les anciens noms des îles n'ont pas produit de géométrie parcellaire publique qualifiée. Les promotions d'agents, tableaux de concurrents et guides commerciaux d'API peuvent fournir des liens, jamais remplacer la vérification à la source. Aucune assertion de forum n'a été importée dans les fiches.

Écartés : confusion MePS municipal / portail médical, Tasareeh au Bahreïn, sites au nom institutionnel sans provenance gouvernementale démontrée, permis publicitaires Madhmoun présentés comme permis de construire, emplacements d'annonces centrés sur un quartier, anciens projets de règlements utilisés comme droit actuel. Les états « en cours », « achevé » et les prix commerciaux ne sont pas homogènes entre ces sources.

## 8. Ordre d'intégration recommandé dans le dépôt et Prefect

Cette section est une proposition d'implémentation, **pas la description de pipelines déjà déployés par cette enquête**. Elle réutilise les frontières `ingestion → evidence → catalog` et le [journal existant](../engineering/DATA_HISTORY.md).

1. **AD-SDI Plots Maryah, puis comparaison Reem/Saadiyat.** Établir la classification/licence de la couche, archiver sa métadonnée et les réponses minimales ; implémenter un profil source distinct d'Onwani. Tester validité PostGIS, unités, référentiels, doublons et pagination. Préserver `PLOTID` comme identifiant source dans un espace de noms, puis créer des rapprochements réversibles avec les objets existants. Ne pas doubler les parcelles ni déplacer des projets par proximité seule.
2. **Relations nom ↔ lot et bâtiments.** Qualifier la publication TAMM/Aldar et Building 353. Garder les périmètres 207/828 comme programme/phase selon preuve ; préserver consultant, constructeur, développeur et marque comme rôles distincts. Normaliser les domaines source avant toute légende. Une valeur inconnue reste inconnue.
3. **Annuaire AccessRP.** Vérifier le parcours public réel et les conditions de réutilisation ; seulement ensuite définir un collecteur borné, des identifiants stables et une comparaison ADGM/ADREC/promoteurs. Un annuaire dynamique vide dans un extracteur n'autorise pas à supprimer les anciens projets.
4. **Pilote permis sur quelques QR publics.** Liste explicite de documents/URLs découverts légalement, hôtes autorisés, anti-SSRF et contrôle des redirections, conservation de l'original, parseur typé de permis et événements. Séparer l'identifiant du permis des références de publicité/entreprise/adresse. Pas de collecte massive ou d'énumération d'identifiants.
5. **Veille infrastructures et contraintes.** Appels d'offres publics, DoE, EAD, masterplans et portfolios qualifiés. Les annonces et permis restent visibles comme événements sourcés ; aucune attribution ou livraison implicite.

Pour chaque acquisition future : heure UTC précise, URL et paramètres, empreinte, référence du run Prefect, version de parseur et date métier lorsqu'elle existe. Captures brutes dans le stockage privé autorisé, faits typés et provenance en DB, conservation des versions manquantes sans effacement. La relecture publique distingue **donnée courante**, **dernière valeur connue** et **contradiction à examiner** ; elle ne mélange pas silencieusement une ancienne géométrie et un nouveau statut.

L'import devra détecter réponse vide anormale, chute de couverture, limite de transfert, échec partiel et changement de schéma. Un run interrompu ne constitue pas un snapshot complet. Les suppressions/fusions prouvées sont des événements métier, pas des objets ressuscités à l'infini par le fallback. La reconstruction sur PostGIS vide devra rejouer les archives via Prefect et comparer identités, géométries, faits et preuves ; une reprise du Web seul ne démontre pas la reproductibilité de l'historique.

## 9. Livraison et limites de cette enquête

Livré : le présent dossier, les références primaires, des requêtes métier exécutées, un relevé technique avec paramètres/heures/empreintes, et la correction documentaire de la conclusion trop large que pourrait suggérer l'absence Onwani. Aucun nouvel import, calendrier Prefect, changement de schéma ou déploiement du site n'a été effectué dans ce lot de recherche.

Les réponses brutes de recherche restent localement sous `.cache/validation/source-research-20261022/`, hors Git ; le relevé versionné publie seulement des observations minimales. Les caches locaux ne sont pas une nouvelle archive de production ni une reconstruction DB démontrée. Les erreurs et limitations d'accès sont conservées comme telles, sans être transformées en absence de données.

Restent non démontrés : licence spécifique des publications `/Pub/` et `/TAMM/`, actualité et exhaustivité cadastrales, récupération automatique AccessRP, inventaire ouvert de tous les permis Abu Dhabi, emplacement cadastral exact de la fontaine IA, et accès aux documents réservés aux parties concernées. Ces limites n'empêchent pas de prioriser les sources qui ont déjà répondu avec des données réelles.

Validation de la livraison : structure des 39 observations, unicité de leurs références, heures UTC, hôtes et empreintes contrôlés ; dix empreintes importantes recomparées aux réponses brutes locales. Deux délais dépassés restent des échecs explicites. Format JSON et liens locaux des 49 fichiers Markdown du dépôt vérifiés. Aucun test applicatif ou GIS d'import n'a été relancé : ce lot change la documentation et ne livre pas de connecteur.
