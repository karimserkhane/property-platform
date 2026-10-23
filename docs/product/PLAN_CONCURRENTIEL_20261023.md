# Plan pour dépasser les plateformes concurrentes — 23 octobre 2026

Plan rédigé par Claude Code à la demande de Karim. Il prolonge le [benchmark du 11 octobre](BENCHMARK_CONCURRENTIEL.md), la [stratégie produit](STRATEGIE_PRODUIT_PROPERTY_PLATFORM.md) et la [revue de plateforme du 21 octobre](../engineering/PLATFORM_REVIEW_20261021.md) ; il ne les remplace pas. Les fonctions des concurrents sont celles **annoncées par leurs éditeurs ou la presse** aux dates citées ; elles n'ont pas été testées derrière connexion. Aucun abonnement n'a été pris.

## 1. En bref

- **Le marché a basculé vers l'achat sur plan à Abu Dhabi** : selon ADREC, le sur-plan représente 89 % de la valeur et 82 % du nombre des ventes résidentielles du premier semestre 2026 ([A&O Shearman, 8 septembre 2026](https://www.aoshearman.com/en/insights/abu-dhabis-new-escrow-and-off-plan-sales-regime-from-momentum-to-regulated-delivery)). L'acheteur décide sur des promesses : livraison, avancement, séquestre, fiabilité du promoteur. C'est là que la plateforme peut être la meilleure.
- **Les grands portails gagnent sur l'annonce et l'IA conversationnelle, pas sur la preuve.** Bayut a lancé une recherche en langage naturel et une app dans ChatGPT ([Gulf Business](https://gulfbusiness.com/en/2026/artificial-intelligence/bayut-launches-ai-powered-property-search-in-uae/)) ; Property Finder propose une estimation avec projection à six mois dans son application ([Arabian Business](https://www.arabianbusiness.com/industries/real-estate/dubai-investors-get-6-month-price-outlook-as-property-finder-launches-ai-home-valuation-tool)). Leurs prix affichés restent des prix demandés.
- **Les plateformes de données se multiplient** (dataHabibi, Dhabi AI de District Real Estate, Daar, PropRobin, Rendr, Aqarcheck), surtout autour des transactions et des scores. Personne, dans ce qui a été observé, ne relie systématiquement **chaque affirmation à sa preuve datée, à la bonne parcelle et à son historique**.
- **L'État ouvre des vérifications officielles** : ADREC permet de vérifier un projet enregistré (promoteur, licence, unités vendues, **pourcentage d'avancement**, compte séquestre), un titre, un bail et un permis Madhmoun ([A&O Shearman, 4 septembre 2026](https://www.aoshearman.com/en/insights/abu-dhabi-real-estate-five-changes-and-what-they-mean-for-your-next-transaction)). Ces vérifications existent mais sont dispersées et non expliquées.
- **Positionnement proposé** : *le dossier de vérification d'un achat immobilier aux Émirats, preuve à l'appui*. Pas un portail d'annonces de plus. Huit piliers (section 5), livrés en six phases (section 6), avec d'abord un **vérificateur de projet sur plan pour Abu Dhabi**.

## 2. Ce que font les concurrents aujourd'hui

| Catégorie | Acteurs | Ce qu'ils font bien | Limites observées ou probables | Notre réponse |
| --- | --- | --- | --- | --- |
| Portails d'annonces | Bayut, Property Finder, dubizzle | Volume d'annonces, recherche conversationnelle (Bayut, août 2026), app ChatGPT, estimation et projection (Property Finder, déc. 2025), transactions Dubai liées (Bayut) | Prix demandés ≠ prix enregistrés ; outils de valorisation centrés sur Dubai ; données projet issues du marketing ; pas de lien parcelle/preuve | Ne pas concurrencer l'annonce ; montrer l'écart entre prix demandé et prix enregistré, et la preuve de chaque fait |
| Intelligence de marché | dataHabibi ([Khaleej Times, août 2026](https://www.khaleejtimes.com/business/property/dubai-startup-datahabibi-launches-ai-platform-for-property-intelligence)), Dhabi AI ([communiqué DRE](https://www.zawya.com/en/press-release/companies-news/district-real-estate-emerges-stronger-from-regional-uncertainty-with-launch-of-uaes-most-advanced-property-intelligence-platform-nysu04m3) : 1 300 fiches d'immeubles, 94 communautés, 38 promoteurs), Daar, PropRobin, REIDIN, Property Monitor | Transactions, rendements, prévisions, profils d'immeubles, assistants IA | Agrégats par communauté ou immeuble ; méthodes peu explicites ; prévisions mêlées aux observations ; peu ou pas de géographie cadastrale | Séparer strictement observé / estimé ; descendre à la parcelle et au projet exact |
| Dossiers projet et due diligence | Aqarcheck, Knownable, Rendr | Sources et dates, échéanciers, livraison promise/actuelle, scores promoteurs | Couverture et fraîcheur variables ; scores dont la formule ou les données manquantes sont peu visibles | Dossier vivant avec historique des affirmations, contradictions visibles, avancement vérifié |
| Cartes et parcelles | Ardhi, DXBinteract / Investment Map, Doment, GenieMap | Parcelles, masterplans, 3D, soleil/ombre, comparaison de zones (surtout Dubai) | Couches surtout Dubai ; permis agrégés par communauté ; Abu Dhabi partiel | Cadastre officiel d'Abu Dhabi déjà ingéré (Onwani, AD-SDI), tuiles vectorielles, contexte public sourcé |
| Suivi de livraison | Dubai Handover, trackers promoteurs, DLD/Oqood | Instantanés de l'avancement Dubai, photos d'inspection | Dubai uniquement ; pas de lien avec le portefeuille de l'acheteur | Alertes par projet suivi, avancement ADREC + indices satellite datés pour Abu Dhabi |
| Plateformes officielles | ADREC / Madhmoun / DARI (Abu Dhabi), Dubai REST, Building Intelligence Platform de Dubai Municipality ([WAM](https://www.wam.ae/en/article/bi6kalj-dubai-municipality-launches-‘building-intelligence)) | Données faisant foi, vérifications d'authenticité, MLS vérifié (Madhmoun) | Outils de vérification, pas de parcours de décision ; un document vérifié n'est pas expliqué | Être la meilleure interface **au-dessus** des sources officielles, avec liens directs vers la vérification |

## 3. Ce qui change aux Émirats et crée une fenêtre

1. **Sur-plan dominant et désormais encadré à Abu Dhabi.** Pas de retrait du séquestre avant 20 % de construction, sauf exception encadrée par la décision administrative n° 24 de 2025 (garantie bancaire, ancienneté et historique de livraison du promoteur). La décision n° 165 de 2025 fixe la retenue du promoteur en cas d'annulation selon l'avancement : 0 % si les travaux n'ont pas commencé pour une cause extérieure, 10 % sous 10 %, 15 % de 10 à 30 %, 25 % de 30 à 60 %, 40 % au-delà ([A&O Shearman](https://www.aoshearman.com/en/insights/abu-dhabis-new-escrow-and-off-plan-sales-regime-from-momentum-to-regulated-delivery)). **Ces règles se calculent pour un acheteur précis** : c'est une fonction utile que personne ne présente simplement.
2. **Enregistrement numérique des réservations (EOI) via Madhmoun depuis le 17 février 2026**, avec fonds dans un séquestre préparatoire géré par l'État ([WAM](https://www.wam.ae/en/article/bysbi4m-adrec-launches-digital-eoi-registration-for)).
3. **Annonces vérifiées obligatoires** : toute annonce à Abu Dhabi doit porter un permis Madhmoun depuis juillet 2025 ; les portails le synchronisent ([Gulf News](https://gulfnews.com/amp/story/business%2Fproperty%2Fbuying-or-renting-an-abu-dhabi-property-check-for-madhmoun-permits-1.500228377)). Afficher une annonce sans permis est exclu ; vérifier un permis est une fonction de confiance.
4. **Course à l'IA conversationnelle** chez les portails. Une IA qui répond sans citer ses sources est banale en 2026 ; une IA qui **refuse de conclure sans preuve** et cite chaque valeur reste rare.
5. **Données publiques plus riches** : rapports semestriels ADREC (transactions, 233 000 baux résidentiels actifs au S1 2026 selon la presse), indice locatif, contexte officiel déjà ingéré (santé, écoles, bus, quartiers, recensement).

## 4. Positionnement

**Promesse** : avant de signer, savoir exactement ce que l'on achète, où, à quel prix réel, avec quel risque de livraison — chaque réponse étant vérifiable.

**Utilisateurs prioritaires**, dans cet ordre :

1. **Acheteur sur plan résident ou expatrié** (y compris à distance, d'où les 16 langues) qui hésite entre deux ou trois projets.
2. **Investisseur qui suit plusieurs projets** et veut être alerté d'un retard, d'un changement de promoteur ou d'un écart de prix.
3. **Agents et conseillers sérieux** qui veulent partager un dossier vérifiable à leurs clients (canal de diffusion, pas cible de monétisation immédiate).

**Ce que la plateforme ne fera pas** : publier des annonces sans permis Madhmoun ; donner un conseil en investissement personnalisé ; inventer une position, une date, un prix ou un statut « officiel » ; présenter une prévision comme une observation.

## 5. Les huit piliers différenciants

Chaque pilier indique le besoin, la référence concurrente, notre version, les données nécessaires et ce qui existe déjà dans le dépôt.

### P1 — Vérificateur de projet sur plan (Abu Dhabi d'abord)

- **Besoin** : « Ce projet est-il enregistré, où en est-il, mon argent est-il protégé, ce promoteur livre-t-il à l'heure ? »
- **Concurrents** : Aqarcheck et Rendr montrent des scores et dates ; ADREC permet de vérifier un projet enregistré. Aucun ne réunit ces éléments dans un parcours expliqué, lié à la parcelle et à l'historique.
- **Notre version** : une fiche « Vérification » par projet avec :
  - statut d'enregistrement ADREC, numéro, promoteur et licence, date d'enregistrement, unités vendues, **avancement déclaré daté**, compte séquestre enregistré — chacun avec lien vers la vérification officielle et date de relevé ;
  - **historique de livraison du promoteur** : dates annoncées successives (déjà collectées dans les dossiers) contre livraison constatée ;
  - **calculateur d'annulation** selon la décision n° 165 de 2025 : « au stade actuel, la retenue serait de X % sur un contrat de Y AED », avec la source du barème ;
  - contradictions visibles : date de livraison différente entre promoteur, agence et registre.
- **Données** : registre des projets ADREC (accès et conditions de réutilisation à qualifier avant toute collecte automatique), dossiers projets existants, textes réglementaires.
- **Existant** : modèles projets/snapshots, `project_registry.json`, historique des affirmations, exclusions réversibles.

### P2 — Avancement de chantier vérifiable

- **Besoin** : savoir si le chantier avance vraiment, pas seulement ce qu'annonce le marketing.
- **Concurrents** : Dubai Handover (Dubai, registre DLD) ; trackers promoteurs.
- **Notre version** : frise par projet combinant avancement déclaré ADREC, permis et QR de chantier MePS (piste de l'[enquête du 22 octobre](ENQUETE_FONCIER_PERMIS_20261022.md)), et un **indice d'activité satellite** sur la parcelle (scènes Sentinel-2 récentes déjà acquises par l'imagerie). L'indice est présenté comme un signal de changement au sol, pas comme un pourcentage d'avancement : 10 m par pixel ne mesure pas les étages.
- **Évolution** : imagerie très haute résolution payante (à budgéter) seulement si les utilisateurs en montrent le besoin.

### P3 — Prix réels contre prix affichés

- **Besoin** : « Le prix proposé est-il cohérent avec ce qui se vend réellement ? »
- **Concurrents** : TruEstimate (Bayut, Dubai), estimation Property Finder, dataHabibi, Daar.
- **Notre version** : pour un projet ou un immeuble, transactions ADREC observées (déjà ingérées par fenêtres de snapshot), par type et surface, comparées au prix demandé avec sa source. Fourchette observée et effectif, jamais une valeur unique sans intervalle. Les estimations éventuelles sont étiquetées « estimation », avec méthode, erreur passée et date.
- **Existant** : pipeline ADREC, page Marché, carte des quartiers.

### P4 — Coût total et échéancier

- **Besoin** : comprendre l'effort réel de paiement, pas seulement le prix.
- **Notre version** : simulateur d'échéancier (plan de paiement du promoteur, frais d'enregistrement et de service sourcés, crédit) tracé dans le temps à côté du risque de livraison de P1 : « vous aurez payé 60 % quand l'avancement déclaré sera de 30 % ». Les frais officiels sont cités avec leur texte ; un frais inconnu reste affiché comme inconnu.

### P5 — Carte cadastrale nationale et ce qui va changer autour

- **Besoin** : voir le terrain exact, ses voisins, et ce qui sera construit à côté.
- **Concurrents** : Ardhi et DXBinteract (surtout Dubai).
- **Notre version** : parcelles officielles sur tout l'émirat d'Abu Dhabi (AD-SDI couvre bien plus que les trois îles), puis Dubai ; couche « à venir » : parcelles non construites, permis et projets enregistrés autour d'un bien, avec leur date. Tuiles vectorielles pour toutes les couches (chantier 3 de la [feuille de route technique](../engineering/ENGINEERING_ROADMAP.md)).

### P6 — Le quartier vécu

- **Besoin** : écoles, santé, transports, commerces, temps de marche, soleil, bruit.
- **Notre version** : déjà avancée (isochrones Valhalla, contexte officiel, soleil et ombres). À ajouter : comparaison de deux adresses côte à côte, trajet vers le lieu de travail saisi par l'utilisateur, ensoleillement d'un étage donné, distances réelles plutôt que « à X minutes » marketing.

### P7 — Suivi et alertes explicables

- **Besoin** : être prévenu quand quelque chose change sur ce que l'on suit, et comprendre pourquoi cela compte.
- **Concurrents** : alertes de prix et de nouvelles annonces chez les portails.
- **Notre version** : liste de suivi (projets, parcelles, immeubles) ; une alerte = un changement daté avec la preuve avant/après : date de livraison repoussée, avancement mis à jour, nouvelle transaction, permis déposé à côté, source retirée. Le journal `evidence.row_revision` contient déjà tous les changements nécessaires.
- **Prérequis** : comptes utilisateurs (inexistants aujourd'hui), consentement et protection des données personnelles.

### P8 — Assistant IA qui cite ses preuves

- **Besoin** : poser une question en langage naturel, dans sa langue.
- **Concurrents** : BayutGPT, recherche IA Bayut, Dhabi AI, Ask Robin.
- **Notre version** : assistant fondé uniquement sur nos dossiers (recherche dans les preuves puis réponse) ; chaque phrase factuelle porte un lien vers sa source ; « je ne sais pas » quand la preuve manque ; réponses dans les 16 langues, avec les textes originaux conservés. Garde-fous : pas de recommandation d'achat personnalisée, pas de calcul financier sans afficher ses hypothèses.

### Socle de confiance transversal

- Indice de **complétude du dossier** (quelles preuves existent, lesquelles manquent), à la place d'un score de « qualité » opaque.
- Vérification de permis Madhmoun pour tout prix demandé ou annonce affichés.
- Mention systématique : observé / déclaré / estimé, avec date de relevé et date de la source.

## 6. Feuille de route proposée

Durées indicatives pour une personne aidée de deux agents ; il n'y a pas d'échéance imposée. Chaque phase se termine par une démonstration sur téléphone et des essais avec cinq utilisateurs cibles.

| Phase | Contenu | Livrable démontrable | Critère de réussite |
| --- | --- | --- | --- |
| **A. Fondations** (3–5 semaines) | Hiérarchie programme → phase → résidence → tour (P1 de la revue du 21 octobre) ; qualification des positions ; sauvegardes et restauration testée ; tests de parcours navigateur ; index et bâtiments servis par zone ; version de cache par famille de tables | Un projet complexe (Gate/Arc, Radiant) correctement structuré et localisé | Aucun projet rattaché à la mauvaise parcelle sur l'échantillon audité ; restauration complète réussie |
| **B. Vérificateur sur plan Abu Dhabi** (4–6 semaines) | P1 complet sur Reem, Saadiyat, Maryah ; calculateur d'annulation ; historique de livraison des promoteurs ; contradictions visibles | Fiche « Vérification » de 20 projets réels | Un acheteur test retrouve en moins de 2 minutes statut, avancement et séquestre d'un projet, avec la preuve |
| **C. Prix et coût** (3–4 semaines) | P3 et P4 ; écarts prix demandé / transactions ; simulateur d'échéancier | Comparaison de 3 projets concurrents avec coût total | Aucune valeur affichée sans source, date et nature (observé/déclaré/estimé) |
| **D. Suivi et alertes** (4–6 semaines) | Comptes, liste de suivi, alertes explicables (P7), avancement satellite (P2) | Alerte reçue sur téléphone après un changement réel | Chaque alerte ouvre la preuve avant/après |
| **E. Assistant sourcé** (3–5 semaines) | P8 sur les dossiers existants, multilingue | Questions courantes répondues avec sources dans 5 langues tests | 0 affirmation non sourcée sur un jeu d'évaluation de 100 questions |
| **F. Extension** (continu) | Autres zones d'Abu Dhabi, puis Dubai (DLD, Dubai REST, Building Intelligence Platform selon conditions) ; P5 et P6 enrichis | Même parcours sur une communauté de Dubai | Mêmes critères qu'en B et C |

**Ordre justifié** : B s'appuie directement sur ce qui existe (dossiers, historique, preuves) et vise le segment qui fait 89 % des ventes ; C et D en dépendent ; E n'a de valeur que lorsque les dossiers sont riches ; l'extension à Dubai vient quand le parcours est prouvé.

## 7. Architecture et choix techniques

- **Modules** : P1/P2 restent dans `evidence` (affirmations, captures) et `publication` (projection de la fiche). Nouveaux sous-paquets plutôt que nouveaux services : `evidence/projects/verification`, `evidence/market` (transactions et indices), `publication/alerts`. Comptes et préférences dans un module `accounts` séparé, seul détenteur de données personnelles.
- **Collecte** : un déploiement Prefect par source officielle, horaires désactivés par défaut, budget par source, reçus et captures comme aujourd'hui. Accès aux registres officiels uniquement selon leurs conditions ; sinon saisie opérateur sourcée.
- **Lecture** : toutes les couches de carte en tuiles vectorielles ; fiches servies avec le cache par version de données ; API publique en lecture plus tard, si un partenaire le justifie.
- **Assistant** : recherche hybride (texte + vecteurs) sur les affirmations publiées, génération contrainte à citer des identifiants de preuve, refus sans preuve ; évaluation automatique en CI sur un jeu de questions figé.
- **Alertes** : abonnement → filtre sur `evidence.row_revision` par tables et identités suivies → notification ; idempotence et regroupement quotidien.
- **Qualité** : tests PostGIS par règle métier (barème d'annulation, séparation observé/estimé), tests de parcours navigateur, budgets de performance en CI.

## 8. Mesures de succès

- Temps pour retrouver la preuve d'une affirmation (cible : moins de 30 secondes).
- Part des valeurs affichées avec source, date et nature : 100 %.
- Couverture : projets d'Abu Dhabi avec fiche « Vérification » complète.
- Essais utilisateurs : décisions mieux justifiées et conclusions injustifiées évitées, mesurées comme dans le protocole du [benchmark](BENCHMARK_CONCURRENTIEL.md#comparaison-à-réaliser).
- Technique : carte interactive en moins de 2 secondes sur 4G, zéro régression des parcours testés.

## 9. Risques et garde-fous

| Risque | Garde-fou |
| --- | --- |
| Droits de réutilisation des données officielles ou d'agences | Qualifier chaque source avant collecte automatique ; liens vers la vérification officielle plutôt que copie quand les conditions l'exigent |
| Publicité immobilière sans permis Madhmoun | Ne pas publier d'annonces ; un prix demandé n'est cité que lié à une annonce porteuse d'un permis vérifié |
| Assimilation à un conseil en investissement | Faits sourcés et calculs transparents, sans recommandation personnalisée ; revue juridique avant toute fonction de « score » d'investissement |
| Données personnelles (comptes, alertes) | Module `accounts` isolé, minimisation, consentement explicite, conformité à la loi fédérale sur la protection des données à vérifier avec un juriste |
| Hallucinations de l'assistant | Réponses limitées aux preuves indexées, citations obligatoires, évaluation automatique bloquante |
| Imagerie satellite insuffisante | Présenter un signal de changement, jamais un pourcentage d'avancement ; imagerie payante seulement sur demande prouvée |
| Concurrence des grands portails | Rester complémentaire : la plateforme où l'on vérifie ce que l'on a vu ailleurs |

## 10. Décisions à prendre par Karim

1. Valider le positionnement « vérification de l'achat » et la cible n° 1 (acheteur sur plan).
2. Valider l'ordre des phases, en particulier B avant C.
3. Accepter la création de comptes utilisateurs (nécessaire pour la phase D).
4. Budget éventuel : imagerie très haute résolution, accès payants à des données, revue juridique.
5. Moment de l'extension à Dubai.

## Sources consultées le 23 octobre 2026

- [Bayut — recherche IA (Gulf Business)](https://gulfbusiness.com/en/2026/artificial-intelligence/bayut-launches-ai-powered-property-search-in-uae/) ; [Bayut — AI Search, ChatGPT, TruEstimate (The National)](https://www.thenationalnews.com/advertorial/2026/09/28/bayut-expands-conversational-property-discovery-with-new-ai-search/)
- [Property Finder — Home Valuation et projection à six mois (Arabian Business)](https://www.arabianbusiness.com/industries/real-estate/dubai-investors-get-6-month-price-outlook-as-property-finder-launches-ai-home-valuation-tool)
- [dataHabibi (Khaleej Times)](https://www.khaleejtimes.com/business/property/dubai-startup-datahabibi-launches-ai-platform-for-property-intelligence) ; [District Real Estate — Dhabi AI (Zawya)](https://www.zawya.com/en/press-release/companies-news/district-real-estate-emerges-stronger-from-regional-uncertainty-with-launch-of-uaes-most-advanced-property-intelligence-platform-nysu04m3)
- [A&O Shearman — cinq changements à Abu Dhabi](https://www.aoshearman.com/en/insights/abu-dhabi-real-estate-five-changes-and-what-they-mean-for-your-next-transaction) ; [A&O Shearman — séquestre et ventes sur plan](https://www.aoshearman.com/en/insights/abu-dhabis-new-escrow-and-off-plan-sales-regime-from-momentum-to-regulated-delivery)
- [ADREC — EOI numériques via Madhmoun (WAM)](https://www.wam.ae/en/article/bysbi4m-adrec-launches-digital-eoi-registration-for) ; [Permis Madhmoun (Gulf News)](https://gulfnews.com/amp/story/business%2Fproperty%2Fbuying-or-renting-an-abu-dhabi-property-check-for-madhmoun-permits-1.500228377)
- [Dubai Municipality — Building Intelligence Platform (WAM)](https://www.wam.ae/en/article/bi6kalj-dubai-municipality-launches-‘building-intelligence)
- [Transactions Abu Dhabi 2026 (Khaleej Times)](https://www.khaleejtimes.com/business/property/abu-dhabi-property-deals-top-dh155-billion-beat-2025s-full-year-total-in-8-months)
