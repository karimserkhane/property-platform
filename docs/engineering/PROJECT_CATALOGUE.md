# Catalogue Reem et Saadiyat — 21 octobre 2026

## Couverture et attribution

Le registre actuel contient **174 fiches nommées** : **117 Reem, 57 Saadiyat**, avec 58 identités de promoteurs, contre 57 fiches au départ. Les ajouts comprennent des programmes, résidences, tours et phases explicitement nommées ; ce total n'est ni un nombre de programmes maîtres indépendants ni une garantie d'exhaustivité. Les captures privées des différentes vagues restent distinctes.

La base utilisée par le site possède **136 fiches avec une identité cartographique active** et 38 sans point suffisamment justifié. Un point déclaré par une agence ne certifie pas une localisation cadastrale. Ces 38 fiches restent disponibles dans l'annuaire ; elles ne sont pas placées artificiellement au centre de l'île.

Les 315 URLs de sources de fiches se répartissent en 95 sources de promoteurs, 60 d'autorité, 157 d'agences, deux d'éditeur officiel/marque et une de presse. Une même fiche peut avoir plusieurs origines : 73 possèdent au moins une source de promoteur, 42 au moins une source ADREC et 150 au moins une source d'agence. Ces nombres se recouvrent et ne doivent pas être additionnés comme des projets indépendants.

Le registre public [ADREC](https://adrec.gov.ae/en/Directory) a fourni 325 lignes sur quatre pages, dont 65 dans le filtre Saadiyat. Soixante sources de détail sont associées à des projets examinés ; les enregistrements de composantes ne fournissent pas le total de leur parent. La réponse de détail du n°69 est absente ; One Saadiyat, SB-03 et les enregistrements de districts/precincts restent à examiner ou hors du catalogue résidentiel. L'absence de Reem dans ce répertoire public ne prouve pas l'absence de projets à Reem.

Les deux pages [Property Finder Reem](https://www.propertyfinder.ae/en/new-projects/lp/abu-dhabi/al-reem-island) couvrent 42 fiches et les deux pages [Saadiyat](https://www.propertyfinder.ae/en/new-projects/lp/abu-dhabi/saadiyat-island) 39. La pagination, les UUID et l'île sont contrôlés ; 77 références sont rapprochées de fiches ou composantes connues. Muheira Maysan, la portée de Reem Hills Phase 2, Marsa et Saadiyat Lagoons Phase 2 restent des candidats sans nouvelle identité automatique. Ces observations d'agence n'établissent ni propriété foncière ni statut juridique.

Les sites examinés incluent notamment Reportage, Aldar, SAAS, Modon, IMKAN, Radiant, Bloom, Burtville, Deyaar, ALAIN/Four Seasons, Taraf, Ohana, RAK Properties, Tiger, NBH, By M/Gefinor, Foster et MAAM. Les guides Bayut, Gravity, Square Yards et la presse complètent les résidences livrées. Forums et réseaux publics servent de pistes ; aucune identité n'est créée sur une simple discussion. Les échecs de transport ou pages ambiguës ne sont pas contournés.

`source_kind` distingue promoteur, éditeur officiel/marque, agence, autorité et média. `source_developer_name/role` garde la partie réellement nommée : NOVA dans l'enregistrement Sensi, SBR pour les Private Residences, VSM pour V Residences, sans fusion avec leurs marques commerciales. `ResidentialUnits` d'ADREC donne les **logements enregistrés** ; les autres totaux sont des **unités annoncées**, qui peuvent inclure des commerces. Aucun de ces chiffres n'est une disponibilité actuelle. `UnitCount`, les stocks d'annonces et `EndDate` ADREC ne sont pas transformés en logements ou en date de livraison.

Property Finder conserve uniquement le mois affiché de livraison ; son jour 1 et son heure CMS n'inventent pas un jour de remise des clés. Les types et chambres proviennent de paires explicites. Les guides de bâtiments vérifient le promoteur et l'île ; une année de construction passée ne devient pas une annonce de livraison future. Les fichiers, photos et vidéos externes restent des références sans autorisation de republication implicite.

Les pages By M possèdent un libellé `Project | Nom` contrôlé et une base relative des documents examinée. Canal Residence reprend un formulaire global contenant des brochures Canal by M : ces liens sont exclus et les anciennes références marquées `blocked` lors du rejeu, sans suppression des preuves. Les exclusions sont explicites dans le registre ; une simple disparition de lien ne retire pas l'histoire.

La première collecte étend le registre de 57 à **146 fiches nommées** : 100 Reem, 46 Saadiyat et 47 identités de promoteurs. Le total comprend programmes, phases et résidences ; il ne mesure ni les logements ni une couverture exhaustive. Les composantes d'un programme ne doivent pas être additionnées à leur parent pour calculer un stock.

Les 147 fiches publiques du [sitemap PSI](https://psinv.net/sitemap-properties.xml) ont été examinées et 138 sources associées au registre. Vida/V Residences, Marina Bay/Marina Bay DAMAC et The Dunes sont rapprochés de leur identité ; Lilac/Turquoise enrichissent Mamsha sans deux nouveaux programmes. Neuf entrées restent hors de cette promotion directe : un hôtel, Muheira at Maysan ambigu, six fiches sans promoteur et Al Noor Tower dont le champ promoteur désigne un bureau d'ingénierie. La découverte conserve les candidats et leurs captures en base.

`ProjectSnapshot.source_kind/source_name` distingue promoteur, agence, autorité et média. Une observation PSI reste attribuée à **Property Shop Investment (PSI)**. Une fiche d'agence n'est pas présentée comme le site officiel du projet. Les identités créées sur cette base portent une note de revue ; un site de promoteur non confirmé reste absent.

`project_psi.py` décode le JSON inerte de la page publique, sans exécuter de script ni interroger le CRM privé. Il vérifie identifiant, nom examiné, promoteur annoncé, ville et île. Rendements promis, prix d'annonces et compteurs de logements en vente ne deviennent pas des faits de programme. Des listes séparées de types et chambres ne créent pas toutes leurs combinaisons.

## Localisation et histoire

Les points génériques réutilisés sur des projets sans rapport sont exclus : `(24.4942437, 54.4068603)` et `(24.5302924, 54.4451578)`. Les coordonnées du siège PSI dans le JSON-LD sont ignorées.

Un point retenu reste **déclaré par l'agence et non vérifié cadastralement**. Son namespace `project:<slug>:broker:psi` est distinct et ne remplace pas une géométrie déjà liée par une revue ou un promoteur. Une fiche peut donc exister sans point fiable. La proximité d'une parcelle n'établit pas de propriété.

Le flow de fiches traite chaque source séparément : portée stable `territoire:slug:sha256(url)`, avec ses conditions requises dans le même lot. Un échec n'empêche pas les autres sources ; le flow signale les échecs. Les faits d'autorité puis de promoteur précèdent ceux d'agence. La projection conserve la dernière valeur non vide par source, même si une page ultérieure devient incomplète. Exclusions et révocations restent applicables.

La migration 0027 ajoute l'origine des observations ; 0028 élargit les portées d'exécution à 255 caractères. Le journal PostgreSQL distingue précisément ingestion et acquisition d'origine.

La migration 0029 ajoute les parties déclarées/enregistrées et la base du total. Un point Property Finder nécessite une localisation `TOWER` au nom examiné du projet ; une communauté ou un point à moins de 30 m des deux centres génériques connus reste sans localisation. Les points d'agence conservent un namespace distinct ; ils ne remplacent pas les liens déjà revus.

## Reconstruction par Prefect

Le flow manuel `property-platform-project-rebuild`, déploiement `empty-project-catalogue-rebuild`, applique explicitement les migrations puis refuse une cible contenant déjà des projets. Aucune table ni base n'est vidée. Le serveur web et le runner ne migrent pas automatiquement au démarrage.

Le paramètre `include_catalogues=true` rejoue également toutes les versions des vingt portées de découverte, après création des projets afin de rétablir leurs associations examinées. Les reçus des catalogues sont conservés dans `project-catalogue-archive/`, avec les mêmes contrôles de hash, horodatage, portée et pagination. Le sitemap multilingue PSI mesuré à 11 178 404 octets bénéficie seul d'une borne examinée de 16 Mio ; les autres pages restent limitées à 4 Mio. Un reçu incomplet ou trop grand n'est jamais tronqué pour fabriquer un catalogue.

L'empreinte d'idempotence d'un catalogue comprend aussi la correspondance examinée URL → projet de son île, partagée avec l'importeur. Une nouvelle association peut ainsi être rejouée à partir des mêmes octets et dates ; l'ancienne observation `pending_review` reste conservée, une nouvelle observation `registered` porte la décision actualisée. Un rejeu sans nouvelle revue réutilise le résultat existant.

La cible est `DATABASE_URL` du processus exécutant le flow : utiliser une base PostGIS neuve, distincte du site et des métadonnées Prefect. Sur le catalogue déjà alimenté du runner principal, le refus protège d'un rejeu accidentel.

- `archive` rejoue toutes les versions conservées, sans requête aux sites de projets ; une source manquante est un échec explicite.
- `archive_or_live` utilise l'archive et collecte les sources sans historique.
- `live` utilise les collecteurs ordinaires.

`include_geography=true` lance auparavant les pipelines de parcelles, districts, secteurs, rues, OSM et références des deux îles, avec leurs prérequis réseau. Sinon les faits sont importés, les associations vers des géométries absentes sont différées puis réconciliables lors d'un nouvel import. Les liens révoqués restent révoqués.

L'archive privée `project-source-archive/` du volume d'ingestion contient des **reçus de sources**, pas des lignes ORM ou un dump SQL. Les lots sont adressés par empreinte, écrits atomiquement et revalidés contre le registre fermé. Octets et instants d'acquisition restent identiques ; le nouvel instant d'ingestion et l'exécution Prefect sont auditables. L'indexation des anciens checkpoints `receipts/` ne nécessite pas l'ancienne base.

Sauvegarder ce volume privé est nécessaire pour reconstruire après disparition d'une source ; Git ne contient pas les anciennes pages. Les corps et pièces protégées restent hors du dépôt, sans nouveau droit de republication.

Cette preuve concerne le **catalogue de projets et son historique**. Elle ne certifie pas à elle seule la restauration des graphes routiers, médias, ventes ou tuiles ; leurs pipelines et archives restent nécessaires.

## Preuve de la première vague

Le 21 octobre 2026, le run Prefect `5fbc2a2d-6879-4525-bac7-e8b2b535646f` a reconstruit une base PostGIS initialement vide avec `mode=archive` et `include_geography=false`. Les 311 versions de reçus ont été rejouées sans échec, sans copier les tables de la base principale.

Le contrôle a retrouvé neuf acquisitions valides absentes de cette dernière après des échecs SQL précédents. Leur réintégration auditée par le run `441c79a1-446b-4ff7-92c1-cc1152fabc78` permet une comparaison identique des deux bases, sans changer leurs instants d'acquisition :

| Ensemble comparé, hors identifiants techniques | Lignes distinctes | Différences |
| --- | ---: | ---: |
| Identités commerciales des projets et promoteurs | 146 | 0 |
| Empreintes, URLs et horodatages des preuves | 311 | 0 |
| Faits typés des snapshots, avec leur provenance | 311 | 0 |
| Observations de typologies avec provenance | 625 | 0 |
| Observations d'équipements avec provenance | 270 | 0 |

Empreinte des identités : `ea0b747ee95e95da834f47c2a37338a35af092b729fb6140cafe2cbbd491bb98`. Empreinte des faits : `aa3b81ee8f6f96c008ab048188daa7b74d464438f637f23dd1408a5005e576cb`. Les instants d'ingestion, IDs SQL et exécutions sont naturellement nouveaux ; les dates des sources restent identiques. Ce test ne comprend pas les couches géographiques, décisions de publication de médias ni les autres domaines indiqués plus haut.

## Preuve finale des 174 fiches

Le run Prefect `46fe0ff5-2998-44f4-95c7-c7bd78328192` (`red-polecat`, terminé le 21 octobre à 00:45 UTC) a reconstruit `property_platform_catalogue_rebuild_final_20261021`. L'absence de tables applicatives avait été vérifiée avant le lancement. Le flow applique les migrations puis rejoue **315 portées de sources, 548 versions de fiches et 24 versions de catalogues**, sans collecte aux sites d'origine, clone de base ou dump. Le résultat contient **zéro source absente ou échouée**. L'image d'ingestion utilisée est `sha256:cd5bf4d64c2e56259cf93f3220dba92a9c48f5c2061a40854dd6a28b2351c73f`.

Le run `fcb54390-c21e-4b38-b266-bcc0e7676e2f` a réconcilié les versions de la base principale. Le run `bbf53598-1b28-4f3e-8119-fecd88750a37` (`grateful-pegasus`, terminé à 03:27 UTC) a ensuite rejoué séquentiellement les 24 versions de catalogues dans chaque cible avec les associations de revue actuelles. Les observations précédentes et leurs dates sont conservées.

La comparaison en lecture seule des deux bases donne :

| Ensemble comparé | Éléments distincts dans chaque base | Différences |
| --- | ---: | ---: |
| Identités commerciales des projets et promoteurs | 174 | 0 |
| Preuves de fiches : projet, URL, hash, début et fin d'acquisition | 548 | 0 |
| Preuves de catalogues avec portée, hash et dates | 24 | 0 |
| Dernières observations des liens de découverte, y compris statut et association | 412 | 0 |
| Fiches projet actuellement servies, normalisées | 174 | 0 |

La normalisation des fiches retire uniquement les IDs techniques, instants d'ingestion et `map_locations`, puis trie les collections. Résumés, livraison, nature et valeur des totaux, typologies, équipements, références média, droits et provenance avec horodatages et pointeurs restent comparés. Elle ne prétend pas rendre identiques toutes les anciennes lignes dérivées par des versions d'extracteur remplacées.

Empreintes SHA-256 communes :

- Identités : `431fb0092ed72af022df51ad0b78384eea60b7388dfaf8c3ae099108c8cce580`.
- Preuves de fiches : `a7ee9fa018230246d7428f26d8353be855eeb5d7c047307da955ff2941c0e18f`.
- Preuves de catalogues : `461ee514ea3c88b0a08dc62c96facebf1ebb159dcbb5be3d5640fa1bdb10f26b`.
- Observations courantes de découverte : `6d68c14c4b4f1ae3902403ee33257031128edab1490acf711505361771e70442`.
- Fiches actuellement servies : `632724946a15b05c96a86e403a4be21cc1e2baa8ab5a182dc05dea80a7915a86`.

Les rapports privés `project-expansion-20261021/rebuild-proof-final.json`, `final-rebuild-run-result.json`, `final-catalogue-reconciliation.json` et `final-metrics.json` sont dans le volume d'ingestion. Ils contiennent comptes, empreintes, limites et résultats, sans dump de tables. Le registre, les extracteurs et l'orchestrateur sont versionnés dans le dépôt ; la pérennité des preuves historiques nécessite toujours une sauvegarde du volume privé.

La cible a volontairement été reconstruite avec `include_geography=false` : elle possède 131 identités cartographiques issues des sources de fiches, contre 136 dans la base principale qui conserve aussi ses liens géographiques revus. Cette différence est hors du périmètre comparé. Les médias sous licence, décisions opérateur, graphes, ventes et fonds cartographiques requièrent leurs archives et pipelines propres ; le test final ne certifie pas la reconstruction intégrale de ces domaines. Le contrôle de couverture trouve 49 tables métier auditées et aucune sans pipeline déclaré ; Esri reste une couche diffusée sans archivage permanent, faute de droits établis.

Le contrôle d'histoire `56fea5f5-82ac-4bc8-8420-227f30e408f5` (`rich-tarantula`) a terminé avec succès. Prefect expose 42 déploiements ; ses métadonnées restent dans leur base séparée. Après remplacement des images API/runner et web, l'annuaire retourne 174 fiches sans troncature (`has_more=false`). Les fiches Sensi, Four Seasons, Canal by M, Canal Residence, Reem Diamond et Global Gate répondent par le relais web avec leurs sources distinctes ; les services API et ingestion sont sains. Les deux relais HTTPS privés Tailscale, site et Prefect sur le port 8443, restent configurés.

Validation : 370 tests API sur PostGIS et 167 tests ingestion réussis pendant le lot ; neuf tests PostGIS de régression réussis après la dernière correction d'idempotence. Les 77 tests web, le contrôle TypeScript, les contrats générés, les trois frontières de dépendances, l'absence de migration manquante et le smoke du web compilé dans les seize langues ont également réussi. Les contrôles de langues et d'identité ne constituent pas une certification cadastrale, une revue juridique des programmes ou une mesure d'exhaustivité du marché.
