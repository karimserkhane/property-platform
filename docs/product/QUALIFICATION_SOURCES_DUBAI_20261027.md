# Qualification des sources de Dubai — 27 octobre 2026

Note de la tâche [F02](../tasks/F02.md). Elle qualifie trois sources pour préparer une extension à Dubai : les données ouvertes de la Dubai Land Department (DLD), l'application Dubai REST et la Building Intelligence Platform de Dubai Municipality. Elle complète les entrées 06 à 16 de l'[inventaire du 13 octobre](SOURCES_DONNEES_UAE.md#dubai). Observations du 27 octobre 2026, entre 03:45 et 04:00 UTC. **Aucune donnée n'a été collectée ni importée** : toute collecte attend la validation de Karim.

## Méthode

Même méthode que l'[enquête du 22 octobre](ENQUETE_FONCIER_PERMIS_20261022.md#méthode-et-niveaux-de-preuve) et la [qualification ADREC](QUALIFICATION_REGISTRE_ADREC_20261024.md#méthode) :

- recherches en anglais ; lecture des pages officielles (DLD, Data.Dubai, Dubai Municipality) ; les articles de presse et les sites tiers servent seulement à trouver des pistes ;
- requêtes HTTPS directes bornées (TLS vérifié, une à la fois, délai de 30 s), sans compte, sans connexion UAE PASS, sans formulaire envoyé ;
- **aucun CAPTCHA résolu ni contourné**, aucune recherche lancée dans un formulaire protégé, aucun service tiers de collecte (les « scrapers » payants de DLD trouvés en recherche ne sont pas des sources) ;
- niveaux de preuve de l'enquête du 22 octobre : données testées, métadonnées testées, service documenté, piste.

## Sondes HTTP

Heure UTC de la requête, statut final, URL finale après redirection et début de l'empreinte SHA-256 du corps reçu. Un `200` sur une page d'accueil n'est pas un accès au jeu demandé.

| Heure | URL demandée | Résultat | Empreinte |
| --- | --- | --- | --- |
| 03:46:57 | `https://dubailand.gov.ae/en/open-data/real-estate-data/` | `200`, même URL, 160 049 octets HTML | `bd0dcc3a54b0ca3b` |
| 03:47:00 | `https://www.dubaipulse.gov.ae/data/dld-transactions/dld_transactions-open` | `301` puis `200` sur `https://data.dubai/en/` (accueil) | `39303a54ccf3b286` |
| 03:47:02 | `https://www.dubaipulse.gov.ae/organisation/dld/service/dld-transactions` | idem, accueil Data.Dubai | `2cc9859845ec2aef` |
| 03:47:10 | `https://www.dubaipulse.gov.ae/data/dld-registration/dld_projects-open` | idem, accueil Data.Dubai | `ff2a0f5270a7e317` |
| 03:47:11 | `https://www.dubaipulse.gov.ae/terms-and-conditions` | idem, accueil Data.Dubai | `4b9ae0b56db58ae0` |
| 03:47:06 | page Dubai Municipality sur la Building Intelligence Platform (lien plus bas) | `200`, communiqué | `8df341eb9b5c7f79` |
| 03:47:08 | `https://dubailand.gov.ae/en/eservices/dubai-rest/` | `200`, page de présentation | `4423472432e8257a` |

Les empreintes de pages HTML dynamiques changent d'une requête à l'autre (les trois redirections vers le même accueil ont des empreintes différentes) : elles datent l'observation, elles ne versionnent pas un jeu de données.

## 1. DLD — Real Estate Data (données ouvertes du site DLD)

[Page officielle](https://dubailand.gov.ae/en/open-data/real-estate-data/). Niveau : **métadonnées testées** (formulaires et champs lisibles) ; aucune ligne de données obtenue.

| Onglet | Filtres affichés | Remarques |
| --- | --- | --- |
| Transactions | dates de début et de fin (obligatoires), type (ventes, hypothèques, donations), enregistrement (prêt, sur plan), pleine propriété, zone, usage, type de bien (terrain, bâtiment, unité) | Comparables historiques, au cœur du prix observé |
| Rents | type de date (enregistrement, début, fin), dates, pleine propriété, version (nouveau, renouvellement), zone, usage | Baux Ejari |
| Project | type de date (début, fin, adoption, achèvement), dates, zone, statut du projet (dix valeurs, dont actif, terminé, annulé, gelé) | Statut et dates d'un projet : équivalent de ce qui manque à Abu Dhabi |
| Valuations | dates, zone, type de bien | |
| Land, Building, Unit | projet, type de terrain, zone, pleine propriété ou bail, enregistrement (achevé, sur plan) | Référentiel des actifs ; pas de géométrie annoncée |
| Broker, Developer | genre ; nom du promoteur et dates | Référentiels professionnels |

**Accès.** Chaque onglet produit un tableau et un bouton « Download as CSV », après un **CAPTCHA** exigé par la recherche. Aucun compte n'est demandé. Aucune API n'est annoncée sur la page. Le pied de page renvoie à Data.Dubai pour les années antérieures et indique une mise à jour du site le 14 octobre 2026 (date du site, pas des données).

**Conditions.** Les [conditions générales DLD](https://dubailand.gov.ae/en/terms-conditions/) réservent tous les droits de propriété intellectuelle. Elles limitent l'usage à la consultation, au téléchargement ou à l'impression de parties des contenus, pour un « personal, noncommercial use ». Toute reproduction, distribution ou affichage public demande un accord écrit avec la DLD. Elles ne mentionnent ni licence de données ouvertes propre à ces CSV, ni robots ou collecte automatique.

**Conséquence.** Le CAPTCHA exclut une collecte automatique par nos pipelines (règle de [SOURCES_DONNEES_UAE.md](SOURCES_DONNEES_UAE.md#règles-de-qualification-avant-import) : aucun contournement). Les conditions du site n'autorisent pas, sans accord écrit, la republication de ces données dans une plateforme publique. Un CSV téléchargé à la main par un opérateur ne lève pas cette limite.

## 2. Data.Dubai, successeur de Dubai Pulse

Toutes les adresses Dubai Pulse testées, y compris les fiches des jeux DLD (`dld_transactions-open`, `dld_projects-open`) et ses conditions, redirigent en `301` vers l'accueil de [Data.Dubai](https://data.dubai/en/), opéré par la Dubai Data and Statistics Establishment (DDSE). Les sites tiers qui citent encore ces fiches (taille du CSV de transactions, licence « CC0 » ou « CC BY 4.0 ») décrivent un état antérieur, sans confirmation officielle : ces licences ne sont pas retenues.

Niveau : **service documenté**. Dans le navigateur, le thème Infrastructure › Housing and Buildings décrit des statistiques sur les bâtiments, les permis et les transactions immobilières. La liste de ses jeux ne s'est pas affichée pendant l'essai, et aucune fiche de jeu DLD n'a été retrouvée sur Data.Dubai par recherche. Les [conditions Data.Dubai](https://data.dubai/en/terms-conditions) soumettent les jeux classés « Open Data » à l'[Open Data Licence](https://data.dubai/documents/d/guest/open-data-license-english-1-1-pdf) (PDF de 4 pages, 92 998 octets, empreinte `f380f9fe755c9f29`, lu à 03:51:52 UTC). Elles distinguent le Dubai Data Exchange Hub, réservé aux entités gouvernementales et utilisateurs autorisés, et proposent un parcours [Request Data](https://data.dubai/en/request-data).

L'Open Data Licence est favorable à une plateforme comme la nôtre, pour les seuls jeux qu'elle couvre :

- licence mondiale, gratuite et non exclusive, pour usage commercial comme non commercial (§2.1) ;
- exclus : marques, logos et images des bases, données personnelles et données d'entreprises privées (noms, objet, statut compris), qui demandent une permission séparée (§2.2) ; une liste de promoteurs ou de courtiers n'est donc pas couverte d'office ;
- interdiction de présenter les données de façon trompeuse (§2.3) ;
- attribution : créateur, mention de droits et lien vers l'original quand ils sont fournis (§3.2.1) ; interdiction d'associer l'œuvre dérivée au gouvernement de Dubai ou à l'autorité (§3.2.2) ;
- une donnée traduite ou réarrangée (« Adapted Material ») doit être republiée sous la même licence ; une application ou une carte (« Work Product ») n'y est pas tenue (§3.3) ;
- revente des données d'origine interdite (§3.6) ; données fournies sans garantie (§4).

**Conséquence.** Pas de collecteur possible avant d'avoir trouvé, pour chaque jeu DLD : sa fiche actuelle sur Data.Dubai, sa classification (ouvert ou partagé) et son mode de téléchargement (fichier, API, compte). Pour un jeu effectivement ouvert, la licence permettrait l'affichage sur la plateforme avec attribution, sans les noms d'entreprises privées sans permission ; la frontière entre « Adapted Material » (à republier) et « Work Product » serait à documenter avant import.

## 3. Dubai REST (DLD)

[Présentation officielle](https://dubailand.gov.ae/en/eservices/dubai-rest/). Niveau : **service documenté**.

Application mobile et web de la DLD pour propriétaires, locataires, courtiers, promoteurs et investisseurs : portefeuille du propriétaire (prix, rendement, charges), demandes de documents, baux et litiges, indices de loyers, de ventes et de charges, annuaires (courtiers, promoteurs certifiés), et **projets sur plan** avec pourcentage d'avancement, photos, numéro de compte séquestre et échéances de paiement des acquéreurs.

Aucune API publique ni export n'est annoncé ; les services personnels passent par une connexion (« MyDLD »). Les informations de projet sont celles qui manquent à Abu Dhabi (séquestre, avancement), mais leur forme publique observable est une application, pas un jeu de données. Les mêmes conditions DLD s'appliquent. Aucune extraction de l'application n'est envisagée ; un service tiers payant qui la « scrape » a été vu en recherche et est écarté.

**Conséquence.** Même traitement que DARI pour Abu Dhabi ([B01](QUALIFICATION_REGISTRE_ADREC_20261024.md#décision)) : au mieux un lien de vérification vers la DLD (par exemple [Project Status Enquiry](https://backoffice.dubailand.gov.ae/en/eservices/real-estate-project-status-landing/), entrée 10 de l'inventaire), sans recopie des valeurs.

## 4. Building Intelligence Platform (Dubai Municipality)

[Communiqué officiel du 12 février 2025](https://www.dm.gov.ae/building-intelligence-platform-showcased-at-the-world-government-summit-2025/). Niveau : **piste**. La plateforme est de **Dubai Municipality**, pas de la DLD.

Le communiqué annonce, pour les bâtiments de l'émirat, nombre d'étages, hauteur, surface totale et brute (GFA), usages, nombre et taille des logements, et des indicateurs économiques : activité commerciale, loyers, démographie, coûts d'entretien, prix de base. Il ne donne ni adresse de la plateforme, ni public visé, ni conditions, ni format. Aucune page d'accès n'a été trouvée. Le portail de données foncières de la municipalité annoncé en 2023 passe par une connexion UAE PASS ; son lien avec cette plateforme n'est pas établi.

**À distinguer** : la [page Open Data de Dubai Municipality](https://www.dm.gov.ae/open-data2/) liste des jeux ouverts (permis de construire et de démolir, usages, niveaux et résumés de bâtiments, informations de projets et de demandes, communautés, secteurs, entrées, Makani). Elle exige de citer la source et renvoie toujours vers des fiches Dubai Pulse, désormais redirigées vers l'accueil de Data.Dubai (§2). Ces jeux sont la voie ouverte la plus probable pour les bâtiments ; ils restent à retrouver sur Data.Dubai.

## Exemples

Aucune ligne réelle n'a été obtenue : le CAPTCHA de la DLD bloque la recherche automatique, l'essai n'a pas tenté de le résoudre et les fiches Data.Dubai n'ont pas été trouvées. Les seuls exemples vérifiables de ce lot sont donc les **structures** ci-dessus : onglets et filtres de la DLD, services listés par Dubai REST, champs annoncés par Dubai Municipality. Aucune valeur de projet, de prix ou de bâtiment n'est recopiée.

## Bilan

| Source | Accès | Conditions | Formats | Collecte automatique |
| --- | --- | --- | --- | --- |
| DLD Real Estate Data | Public, sans compte, CAPTCHA à chaque recherche | Usage personnel et non commercial ; republication sur accord écrit | CSV par onglet | **Non** (CAPTCHA, conditions) |
| Jeux DLD sur Data.Dubai | Fiches Dubai Pulse redirigées ; fiches Data.Dubai non retrouvées | Open Data Licence : commerciale autorisée avec attribution, hors données d'entreprises privées et personnelles | Inconnu | **À qualifier** |
| Dubai REST | Application, connexion pour les services personnels | Conditions DLD | Aucun export | **Non** ; lien de vérification seulement |
| Building Intelligence Platform | Inconnu, aucune adresse publiée | Inconnues | Inconnus | **Non qualifiable** à ce jour |
| Jeux ouverts de Dubai Municipality | Liens vers Dubai Pulse, redirigés | Citer la source | Fichiers et une API annoncés | **À qualifier** sur Data.Dubai |

## Recommandation

Aucune collecte Dubai n'est prête. Ordre proposé pour une prochaine tâche, à valider par Karim avant tout code :

1. **Retrouver les jeux ouverts sur Data.Dubai** (transactions, projets, terrains, bâtiments et unités DLD ; permis et bâtiments de Dubai Municipality) et vérifier si le téléchargement exige un compte. Un compte ne serait créé que par Karim.
2. Si les jeux DLD n'y sont pas ouverts : le seul chemin est une **demande officielle** (Request Data de Data.Dubai ou accord écrit de la DLD), que seul Karim peut faire.
3. Pour Dubai REST et la Building Intelligence Platform : liens de vérification seulement, aucune extraction.
