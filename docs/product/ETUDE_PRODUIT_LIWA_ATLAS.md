# Étude de cadrage — atlas immobilier évolutif

Date de recherche : 9 octobre 2026. Nom de travail : Liwa Atlas, à confirmer.

## 1. Proposition de produit

Créer un dossier évolutif pour chaque bien et son environnement, consultable sur une carte, par recherche ou dans une liste. Relier parcelle, projet, phase, bâtiment, étage, type de plan et logement lorsque les preuves permettent ce niveau de précision.

Promesse proposée : « Comprendre ce que vous achetez, ce qui peut changer autour et les preuves disponibles. »

Les cibles initiales sont les acheteurs et propriétaires d’Al Reem Island, notamment ceux qui achètent à distance. Les agents peuvent acheter des dossiers de comparaison et des outils de présentation. L’expansion vers d’autres quartiers doit réutiliser le même modèle métier, avec des sources et règles locales propres à chaque zone.

La différenciation envisagée est une hypothèse à tester. Les recherches sur les pages publiques des concurrents ne démontrent pas qu’une fonctionnalité est absente de leurs offres privées.

## 2. Audit du fichier fourni

Fichier examiné : Atlas_Parcellaire_Al_Reem (3).html. Inspection du code et des données embarquées ; aucun audit visuel ou test complet de l’interface n’a été réalisé dans cette étude.

Les données embarquées sont datées du 5 octobre 2026. Elles contiennent :

| Ensemble | Nombre |
|---|---:|
| Géométries de parcelles / emprises | 2 432 |
| Repères nommés | 149 |
| Enregistrements de projets dans projectdata | 73 |
| Entrées dans la couche future | 56 |
| Entrées de voirie dans roads | 69 |
| Références dans sourcedata | 354 |

Les attributions sont classées ainsi : 100 documentées, 951 probables, 604 pistes, 777 inconnues. Parmi les 1 655 parcelles avec une attribution, 1 454 sont rattachées à un quartier et seulement 201 ont une attribution au niveau parcellaire. Ces chiffres décrivent les catégories du prototype ; les 354 sources n’ont pas été revérifiées individuellement ici.

Une nouvelle inspection des données embarquées confirme ces comptes. Elle trouve 104 géométries avec une date et un type de permis non vides, 191 avec un statut MEPS et sa date, et 95 avec un lien DCR. Le drapeau `dcr_read` vaut vrai pour 94 géométries : c’est une indication du prototype, pas une nouvelle vérification des PDF. Les 100 attributions documentées ont une portée parcellaire. Ces comptes mesurent le contenu du fichier du 5 octobre, pas la couverture actuelle du registre officiel.

Le prototype a déjà des éléments précieux : séparation des hypothèses et annonces, motifs de rejet des localisations contradictoires, liens vers les sources, recherche par nom ou code, contexte spatial et dates d’imagerie.

Améliorations nécessaires :

- Préserver la différence entre un nom de quartier et l’identité précise d’un bâtiment.
- Calculer automatiquement les compteurs : enrichment.future_count indique 53 alors que future contient 56 entrées.
- Séparer les dates de publication, d’observation, de réception administrative et de vérification.
- Conserver les géométries originales et leurs versions ; prévoir fusions, divisions et anciens identifiants des parcelles.
- Remplacer les distances depuis le terrain entier par des distances adaptées au besoin : bord, entrée, chemin piéton ou point du logement.
- Charger les données par zone et les médias à la demande. Le fichier autonome pèse environ 11,3 Mo ; son poids ne constitue pas un benchmark de performance.

## 3. Concurrents prioritaires

Classement par proximité avec le produit envisagé, pas par qualité globale. Fonctionnalités présentées sur leurs pages publiques, sans validation indépendante de leur exactitude ou de leur couverture exhaustive.

| Priorité | Acteur | Offre publique observée | Implication |
|---|---|---|---|
| 1 | Ardhi | Parcelles, masterplans, permis, hauteurs, infrastructures et ombres ; de nombreuses couches décrites concernent Dubai | Il faut tester sa profondeur réelle sur Reem avant de revendiquer un avantage sur l’urbanisme |
| 2 | PropRobin | Intelligence Abu Dhabi, transactions, comparaisons, projections par layout, alertes et visites ; Pro affiché à 199 AED/mois | Les tableaux de prix et une promesse générale d’IA sont déjà concurrencés |
| 3 | Investment Map / DXBinteract | Carte 3D Dubai, offre future, avancement, fiches, plans, échéanciers et disponibilités | Les fiches riches sur carte constituent un niveau attendu |
| 4 | Knownable | Guides Abu Dhabi avec sources, distinction entre dossiers éditoriaux et index de découverte | La présence de sources seule ne suffit pas à se différencier |
| 5 | Dubai Handover | Historique des changements de statut, avancement, photos d’inspection et alertes DLD | Le suivi des changements doit apporter une précision et un contexte supplémentaires |
| 6 | OPPS / GenieMap | Inventaire, disponibilité, plans de paiement et catalogues ; OPPS présente une API | Potentiels fournisseurs à examiner autant que concurrents |
| 7 | Property Monitor | Comparables, données de projets/bâtiments/unités, médias, offre future et API | Une couverture financière professionnelle demande des données coûteuses et solides |
| 8 | Daar | Analyses Abu Dhabi fondées sur les transactions ADREC, avec accès de base annoncé gratuit | Difficile de monétiser uniquement des statistiques générales |

Doment propose également une carte immobilière 3D ; Realiste présente un parcours d’investissement assisté par IA et experts. Ils confirment que la visualisation ou le mot « IA » ne constituent pas à eux seuls une proposition distinctive.

Sources : [Ardhi](https://www.ardhiuae.com/ardhi-home), [PropRobin](https://proprobin.com/abu-dhabi/pricing), [Investment Map](https://investmentmap.ai/), [Knownable](https://www.knownable.com/en/developments), [Dubai Handover](https://dubaihandover.com/), [OPPS](https://opps.ae/for-agencies), [GenieMap](https://promo.geniemap.net/), [Property Monitor](https://propertymonitor.com/products-and-services/pm/pmiq), [Daar](https://daarintel.com/faq), [Doment](https://dubaimap.doment.ai/), [Realiste](https://realiste.ai/en/investors).

## 4. Axes de valeur à tester

### A. Dossier de preuves par information

Un bâtiment peut être bien identifié mais avoir une hauteur inconnue, une livraison seulement annoncée et une disponibilité ancienne. La fiabilité doit être attachée à chaque affirmation.

Pour chacune : valeur, objet concerné, portée géographique, source originale, passage ou page, dates, méthode de rapprochement, sources contradictoires, statut éditorial et droits d’utilisation. Plusieurs reprises du même communiqué ne comptent pas comme des confirmations indépendantes.

Séparer trois dimensions : état du projet (annoncé, autorisé, en chantier…), qualité de preuve (primaire, secondaire, témoignage…) et précision spatiale (quartier, parcelle, bâtiment, unité). Une source primaire de promoteur est pertinente pour son offre annoncée, sans prouver sa livraison future.

### B. Comprendre l’environnement de son logement

L’utilisateur choisit un bien puis voit les constructions, voiries, équipements et changements connus dans son voisinage. Le dossier explique les effets possibles : vis-à-vis, ensoleillement, accès ou proximité d’un chantier.

Quand étage, orientation, implantation ou hauteur manquent, afficher les paramètres inconnus. Une simulation ne doit pas convertir une hauteur maximale réglementaire en bâtiment futur certain. L’absence d’information ne signifie pas absence de projet.

### C. Journal des changements et alertes expliquées

Comparer les nouvelles sources aux versions précédentes : changement de date de livraison, nouvelle brochure, modification de plan ou évolution de statut. Expliquer ce qui a changé, à quelle date et pourquoi cela concerne le bien suivi.

Une alerte « une nouvelle attribution est proposée sur la parcelle voisine ; validation en cours » est différente d’une alerte de construction confirmée. Les rumeurs sont consultables dans une couche explicite et désactivée par défaut.

### D. Comparer des logements et leurs offres réelles

Conserver séparément le type de plan et l’unité effectivement proposée. Comparer étage, orientation, surface intérieure, balcon, parking, calendrier de paiement, frais connus, prix demandé et transactions comparables disponibles.

Les surfaces doivent être normalisées : surface totale, intérieure, vendable et balcon ne sont pas interchangeables. Une offre comprend une source, une date de validité et un état de disponibilité. Un « prix à partir de » n’est pas le prix de chaque logement.

Afficher les échéances de paiement en montants et dates ; distinguer celles liées au calendrier de celles liées à des jalons de construction. Les frais manquants restent visibles comme inconnus. Les calculs utilisent des hypothèses choisies et ne promettent pas une performance financière.

### E. Documents et plans versionnés

Permettre l’import de brochures numériques et la numérisation de documents papier autorisés. Conserver l’original, les pages, la version et le niveau de validation de l’extraction. Comparer deux plans pour signaler une pièce, une dimension ou un balcon modifié, après contrôle des extractions.

Ce travail produit un actif réutilisable pour la recherche, les fiches, la comparaison et la 3D. Le détenteur d’un exemplaire papier ne possède pas automatiquement les droits de publication du plan.

### F. Retours d’expérience contextualisés

Séparer promoteur, agence commerciale, chantier, bâtiment livré et gestionnaire. Un avis sur le bureau de vente ne décrit pas nécessairement le logement.

Pour les contributions propres : thèmes structurés (entretien, ascenseurs, parking, isolation…), période, bâtiment concerné, statut déclaré du contributeur, modération et possibilité de réponse. Une vérification privée du lien au bâtiment peut exister sans exposer les documents personnels.

Les synthèses indiquent nombre, période et couverture des témoignages. Éviter une note globale mélangeant des lieux et populations différents, et distinguer opinions et faits vérifiés.

### G. Collecte locale avec l’application mobile

L’app mobile sert à photographier un panneau ou un chantier, scanner une brochure et proposer une correction. Elle permet aussi d’accéder aux dossiers, comparer et recevoir les alertes.

La date et la géolocalisation sont des indices, pas des preuves absolues. Les observations passent par une validation avant de modifier les fiches. Prévoir consentement, retrait, traitement des personnes visibles et stockage privé des justificatifs.

### H. 3D utile à la décision

Trois niveaux distincts : volumes urbains avec hauteurs documentées ; logement construit depuis un plan contrôlé ; décoration ou vidéo générative illustratrice.

La visite et la vidéo peuvent partager une géométrie vérifiée. Afficher dimensions connues, éléments estimés, version du plan et hypothèses. Ne pas reconstruire automatiquement une visite métriquement fiable à partir de quelques photos non calibrées.

## 5. Faisabilité des données

| Famille | Constat | Décision de produit |
|---|---|---|
| Parcelles DMT/Onwani | Service public avec géométries, identifiants, usages, statuts et champs de permis/hauteurs | Tester données réellement remplies sur Reem, définitions, fraîcheur et droits |
| Voirie/adressage | Couches Onwani de rues et adresses disponibles | Distinguer nom de rue, accès physique et itinéraire |
| Registres ADREC/Madhmoun | ADREC présente aussi des abonnements API par module, service et intégration personnalisée, sur demande | Examiner accès, champs, couverture, historique, tarification et redistribution ; l’offre d’API ne prouve pas un accès ouvert à toutes les données |
| Inventaire commercial | API OPPS présentée pour projets, médias et unités | Vérifier couverture Reem, latence, quotas, droits de redistribution et tarifs |
| Comparables | Property Monitor présente des API | Examiner contrats et couverture avant de bâtir une fonction dépendante |
| Avis Google | Places API renvoie au maximum cinq avis par lieu | Affichage conforme ou lien ; ne pas promettre l’exhaustivité |
| Forums/réseaux | Accès et conditions différents selon plateforme ; Reddit exige un accord séparé pour l’usage commercial de son API | Références autorisées et collecte ciblée, sans promesse de couverture totale |
| Satellite Sentinel-2 | Certaines bandes à 10 m ; données disponibles aux utilisateurs commerciaux | Observation de changements importants ; insuffisant pour détails fins d’un logement |
| Photos/plans/vidéos | Présence publique ne garantit pas le droit de republication | Autorisations, licences ou intégrations permises ; politique par source |

Le schéma DMT comporte notamment Permit_LastDate, Permit_LastType, MAXALLOWABLEHEIGHTS et DMT_DCR_URL. Cela prouve l’existence de champs, pas leur remplissage ni l’exhaustivité d’un historique de permis. Les PDF DCR doivent être validés séparément ; un PDF testé n’a pas pu être récupéré via l’outil web pendant cette étude.

Le choix de MapLibre doit être compatible avec les conditions des autres fournisseurs. L’affichage, la conservation et les attributions du contenu Google ont des règles spécifiques. Les données OpenStreetMap et le service public de tuiles sont deux ressources différentes ; prévoir un fournisseur ou un hébergement adapté à la production.

Sources : [Parcelles DMT](https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/0), [Adressage Onwani](https://onwani.abudhabi.ae/arcgis/rest/services/Onwani/UDM_AddressingLayers/MapServer), [ADREC](https://adrec.gov.ae/en/verify-document), [API OPPS](https://opps.ae/integration-for-agencies), [API Property Monitor](https://propertymonitor.com/products-and-services/pm/pm-api), [Google Places — référence](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places), [Google — politiques](https://developers.google.com/maps/documentation/places/web-service/policies?hl=fr), [Reddit](https://redditinc.com/policies/data-api-terms), [Sentinel-2](https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-2), [Tuiles OSM](https://operations.osmfoundation.org/policies/tiles/).

Compléments vérifiés le 9 octobre 2026 : [abonnements API ADREC](https://adrec.gov.ae/en/apisubscription), [gestion des communautés et charges ADREC](https://adrec.gov.ae/en/sectors/regulatory-services/community-affairs). La fraîcheur de cache annoncée par OPPS (~90 secondes) décrit la propagation d’une mise à jour de son catalogue ; elle ne démontre pas que chaque promoteur actualise son inventaire à cette fréquence. Google impose des conditions de conservation, d’attribution et d’affichage : son contenu Places affiché sur une carte doit respecter les règles Google Maps. Une intégration dans une carte MapLibre ne peut donc pas être supposée permise.

## 6. Modularité du site et de l’app

Un cœur métier partagé dessert le site, l’app et, éventuellement, une API partenaire. Les interfaces peuvent différer ; données, permissions et règles restent communes.

Modules envisagés : géographie/identités, preuves, dossiers immobiliers, prix/offres, documents/médias, observations/avis, changements/alertes et scènes 3D. Les extractions et rendus longs s’exécutent séparément de la consultation.

L’extension géographique ajoute des connecteurs, langues, conventions d’adresse, unités et règles locales. Un tableau de couverture explique quelles couches sont disponibles dans chaque territoire. Une zone sans données de permis reste utilisable mais ne doit pas sembler aussi complète qu’une zone documentée.

Le choix final des frameworks, du cloud et de l’app native doit suivre les essais de données et les parcours prioritaires. Aucun besoin ne justifie encore de figer une architecture exhaustive ou un calendrier de production précis.

## 7. Première version et validation avant développement

Vision conservée : site et application mobile, extensibles hors Reem. Pour apprendre rapidement, le premier parcours mobile peut être testé dans un site responsive/installable ; l’app dédiée vient avec les besoins de capture, synchronisation et notifications confirmés.

Périmètre initial proposé : carte générale de Reem, dossier complet de The District et ses voisins, puis 15 à 20 projets détaillés. Présenter les parcelles inconnues honnêtement. Prévoir carte/recherche/liste, sources par information, comparaison limitée de logements, documents, historique et suivi. Une démonstration 3D contrôlée peut accompagner le pilote.

Avant le développement, réaliser :

1. Un échantillon de 30 parcelles et 5 projets : identité, usages, champs de permis, hauteurs, sources et fraîcheur réellement disponibles.
2. Trois dossiers manuels complets : un bien existant, un projet sur plan et une parcelle d’avenir incertain.
3. Un test de l’offre commerciale : obtenir ou documenter une source viable de disponibilités et droits d’utilisation.
4. Quinze entretiens proposés avec acheteurs/propriétaires/agents, centrés sur leurs décisions réelles ; ces entretiens n’ont pas été conduits ici.
5. Une maquette du parcours « mon bien → environnement → sources → comparaison → suivi ».
6. Un essai de plan vers 3D avec mesures de référence et vérification humaine.

Mesurer : erreurs d’attribution spatiale, part des informations reliées à une preuve, ancienneté des offres, temps de correction, temps d’entretien par dossier, coût par utilisateur et intérêt à payer.

Décisions conditionnelles : sans droits d’inventaire, proposer des offres datées plutôt qu’un stock temps réel ; sans historique complet des permis, suivre les observations et sources disponibles ; sans géométrie suffisante, conserver une 3D indicative. Lancer quand la valeur de trois dossiers est démontrée et que leur entretien est soutenable.

## 8. Modèle économique à expérimenter

Accès gratuit : carte, fiches essentielles, statuts et sources. Les preuves et limites restent visibles dans toutes les formules.

Offres possibles : dossier d’achat ponctuel, pass de recherche, suivi propriétaire, comparaison et rapports pour agents, accès API ultérieur. Un achat immobilier ponctuel ne justifie pas forcément un abonnement durable ; les alertes utiles après achat peuvent créer la récurrence.

Les tarifs évoqués dans la conversation précédente restent des hypothèses. Les coûts déterminants sont les licences et médias, l’entretien éditorial, les données commerciales, la collecte locale et la 3D, autant que l’hébergement. Déterminer les prix après les tests utilisateurs et un calcul de marge par formule. Toute relation commerciale avec un promoteur doit être visible ; elle ne modifie pas le niveau de preuve.

## Recommandation

L’approfondissement concurrentiel, les axes supplémentaires, la répartition construire/acheter et les critères de lancement figurent dans [STRATEGIE_PRODUIT_LIWA_ATLAS.md](STRATEGIE_PRODUIT_LIWA_ATLAS.md). Il complète cette étude et affine ses hypothèses ; aucun développement du site ou de l’app n’a été commencé.

Construire progressivement un atlas où l’on peut retrouver chaque information jusqu’à sa preuve, comprendre les inconnues et suivre les changements propres à son bien. La valeur défendable vient de l’identité spatiale exacte, des documents versionnés, des observations utiles et de l’historique accumulé. Rassembler les fonctions concurrentes fournit une base ; leur cohérence à l’échelle du logement donne une direction de produit à tester.
