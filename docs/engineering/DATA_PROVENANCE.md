# Données de Reem : collecte directe, provenance et audit

Décision du 10 octobre 2026 : la carte pilote couvre Al Reem Island. Les données sont acquises directement auprès de leurs sources ; le HTML fourni sert de référence visuelle, pas de jeu de données à importer. Ce document décrit la cible et son premier sous-ensemble implémenté : parcelles, acquisitions Onwani, captures, observations et événements d'audit. Les décisions éditoriales, les autres collecteurs et la publication restent à développer.

## Import manuel implémenté

Le connecteur `apps/api/src/property_platform/modules/evidence/maps/onwani.py` interroge la source officielle à chaque exécution, filtre `AL REEM ISLAND` **et** `ADM`, vérifie son schéma et collecte les identifiants puis les géométries par lots. Une seconde liste d'identifiants contrôle la couverture en fin de collecte ; elle ne garantit pas que tous les attributs sont restés figés pendant l'acquisition.

`apps/api/src/property_platform/modules/evidence/maps/services.py` conserve les réponses exactes et leur empreinte, puis applique un lot complet dans une transaction qui conserve aussi observations et audit. Un verrou PostgreSQL de session empêche deux instances de ce connecteur de modifier le catalogue simultanément. Connexion directe requise ; ne pas utiliser de pooler de transaction pour cette commande.

Une répétition crée une nouvelle acquisition et de nouvelles observations, mais pas de nouvelles parcelles pour les mêmes identifiants de source. Les changements typés ou géométriques augmentent la révision et produisent un audit. Les dates externes restent dans leurs champs bruts ; aucune date de publication n'est inventée. Les captures référencent exactement le champ `features[n]`, qui permet de retrouver chaque attribut et la géométrie d'origine.

Limites explicites de ce premier sous-ensemble : les réponses JSON bornées sont stockées dans PostgreSQL, sans stockage objet ni déduplication physique des captures ; aucun document/photo/vidéo n'est acquis. L'OBJECTID reste un identifiant d'observation rattaché à la source, pas une garantie d'identité cadastrale permanente : un changement d'identifiant nécessite une réconciliation ultérieure. Une géométrie topologiquement invalide est conservée dans `evidence.quarantined_observation`, sans réparation silencieuse ni remplacement d'une ancienne valeur valide ; les autres enregistrements complets sont appliqués et le statut du lot devient `quarantined`. Un mauvais territoire, un schéma inattendu ou un lot manquant font en revanche échouer toute l'acquisition. Aucune disparition n'efface une parcelle. Les erreurs réseau sont enregistrées sur l'acquisition, les réponses HTTP d'erreur bornées sont capturées. Il n'y a ni reprise à mi-lot, ni planification, ni publication automatique. Le journal n'est pas encore durci par des rôles SQL dédiés ; les opérations de cette commande restent transactionnelles et attribuées à son opérateur.

Les captures exploratoires de la section suivante ne sont pas utilisées par cette commande. Voir [les commandes de développement](DEVELOPMENT.md#premier-import-manuel-des-parcelles-onwani).

### Vérifications de ce premier import

Les tests d'intégration ont été exécutés avec PostgreSQL 18.6/PostGIS 3.6 réel dans une base de test séparée : répétition sans doublon, changement de valeur avec historique, échec de collecte sans mutation du catalogue, rollback en cas d'échec d'audit, lot incomplet, trous et polygones disjoints, et quarantaine sans remplacement d'une valeur valide. Les tests de protocole vérifient aussi territoires, identifiants, coordonnées, schéma, troncature et conservation d'une réponse HTTP d'erreur.

Deux acquisitions réelles successives ont ensuite été exécutées dans une autre base temporaire : première acquisition **2 432 observations, 2 431 créations et une quarantaine** ; seconde acquisition **0 création, 0 modification, 2 431 inchangées et une quarantaine**. La géométrie invalide observée correspond à l'OBJECTID `26032713`. Les 56 captures des deux acquisitions ont été conservées dans cette base pendant le test. La base temporaire a été supprimée après vérification ; la base locale de développement `property_platform` n'a pas été alimentée par ces tests. Ces effectifs décrivent les acquisitions testées, pas une constante à imposer aux futures collectes.

## 1. Sources et état de la recherche

| Source | Rôle | État réellement vérifié |
|---|---|---|
| [DMT/Onwani, couche PLOT](https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/0?f=pjson) | Géométries et attributs de parcelles, champs de construction et de dernier permis | Métadonnées et enregistrements interrogés directement le 10 octobre 2026 |
| [Onwani, présentation officielle](https://pages.dmt.gov.ae/en/onwani) | Adresses, rues et numéros de bâtiments | Page officielle retrouvée ; connecteur de rues/adresses à qualifier |
| [ADREC, annuaire](https://adrec.gov.ae/en/directory) | Projets et professionnels | Annuaire public retrouvé ; disponibilité et extraction des fiches à tester |
| [DMT, présentation de Binaa](https://www.dmt.gov.ae/en/Media-Centre/News/Binaa-Construction-Permits-Platform-Launched) | Point de départ pour les services de permis | Existence de la plateforme documentée ; un registre public complet ou une API ouverte n'est pas établi par cette annonce |
| Promoteurs et documents de projets | Plans, offres, annonces, échéanciers, livraison annoncée | Sources à inventorier projet par projet, avec date/version du document |
| Forums, avis et réseaux sociaux | Témoignages et signaux de changement | Sources publiques à inventorier ; accès, couverture et droits de réutilisation à qualifier par plateforme |

Une page consultable n'établit pas à elle seule un droit de redistribution, une API utilisable ou une couverture complète. Distinguer lecture publique, collecte, conservation et publication des textes/médias. Un accès bloqué est enregistré comme tel ; aucune couverture « de tous les sites et commentaires » n'est promise. Les données identifiant des personnes ne sont pas collectées par défaut.

### Droits de chaque source (A19)

Toutes les données et tous les pipelines sont conservés ; chaque source porte ses droits. Les droits appartiennent à l'éditeur d'un site (ou à l'un de ses hôtes), pas à chaque ligne : une capture, une observation ou un fait hérite des droits de l'hôte de l'URL d'où il a été lu. Une revue modifiée s'applique donc d'un coup aux données passées et futures, sans réécrire de ligne.

**Application des droits (A22).** Les droits sont toujours enregistrés, en base comme dans l'API. Les appliquer est une décision distincte du propriétaire : un interrupteur par droit dans `evidence/source_rights_enforcement.json`, avec `enforced`, la date, l'auteur et le motif. Décision de Karim au 27 octobre 2026, aucun des deux droits n'est appliqué :
- **collecte** : tous les pipelines collectent, y compris les sites `forbidden` ;
- **publication** : l'aperçu privé montre toutes les données collectées, y compris celles des sources `link` ou `none`.

Chaque donnée garde ses droits. Mettre `enforced` à `true` arrête d'un coup les collectes ou masque ce que les conditions ne permettent pas (voir « Ce que le code en fait »), sans toucher aux données. Le remettre à `false` les rétablit.

**Registre revu** : `evidence/source_rights.json`, une entrée par hôte (sous-domaines compris). Il couvre toutes les sources des registres et tous les connecteurs ; un test refuse une source sans entrée et une entrée qui ne sert plus.

| Champ | Contenu |
| --- | --- |
| `licence`, `licence_url` | Licence de réutilisation : `ODbL-1.0`, `CC-BY-4.0`, `CDLA-Permissive-2.0`, `Copernicus`, `per-item` (licence propre à chaque fichier), `proprietary`, ou `unknown` (conditions jamais relues) |
| `terms_url`, `reviewed_on`, `reviewed_by` | Conditions lues, date et auteur de la revue (`Karim` pour une décision du propriétaire) |
| `collection` | `allowed`, ou `forbidden` quand les conditions interdisent l'accès automatisé |
| `publication` | `open` (redistribution permise, avec `attribution`), `facts` (faits datés, courte citation d'origine et lien), `link` (simple lien) ou `none` |
| `basis` | Ce qui justifie la décision, en une phrase |

État au 27 octobre 2026, sur 83 hôtes :
- **Données ouvertes** (`open`) : OpenStreetMap (et Overpass, Geofabrik, OpenFreeMap), Overture, Copernicus Sentinel-2, ESA WorldCover, Wikimedia Commons.
- **Collecte interdite par leurs conditions** (`forbidden`, collectés tant que la collecte n'est pas appliquée) : Property Finder, PSI, Bayut, LinkedIn et Reddit (`none`), Aldar (`link` : les liens vers ses pages officielles restent, par décision de Karim).
- **Relues sans interdiction** : Reportage et Bloom (médias non republiables, faits et liens) ; ADREC (aucune licence ni interdiction publiée, abonnement API officiel possible).
- **Non qualifiées** (`unknown`, `facts`) : les autres promoteurs, la presse, les forums, Onwani, AD-SDI et les autres services publics ; à qualifier en [A21](../tasks/A21.md).

**Ce que le code en fait.** `evidence/source_rights.py`, sans réseau ni Django, est lu partout :
- **Collecte**, quand elle est appliquée : les flows de fiches, catalogues, références et présentations sautent les sources `forbidden`. `SourceHTTP.fetch` les refuse aussi pour tout connecteur, même lancé à la main. Les pipelines et les registres restent en place : une autorisation écrite se traduit par une ligne modifiée.
- **Publication**, quand elle est appliquée : rien de ce que porte une capture d'une source `link` ou `none` n'est publié :
  - faits, typologies et médias ;
  - positions et repères de carte ;
  - liens de hiérarchie, présentations et références ;
  - signal satellite.

  Une fiche sans autre source n'est plus publiée. Le lien « site du projet » ne pointe vers une telle source que si elle est `link`. Non appliquée, chaque lecture retrouve son comportement d'avant A19.
- **API** : chaque source d'une fiche porte `rights` (licence, conditions, niveau de publication, attribution, date de revue) et `shown_beyond_terms`, vrai quand la publication n'est pas appliquée et que les conditions ne permettent qu'un lien ou rien. Le site les affiche sous chaque citation, avec une ligne qui signale ces données ([A20](../tasks/A20.md)). `GET /api/v1/preview/source-rights` publie le registre (sans auteur ni motif de revue) pour la page `/[locale]/sources` « Sources et licences », liée depuis la liste des sources de chaque fiche. Les crédits des cartes (OpenFreeMap, OpenStreetMap, ESA WorldCover, Copernicus Sentinel, Overture) viennent du même registre, par l'export `packages/contracts/map-credits.json` (`source_rights.map_credits`), lié aux conditions de chaque site ; une couche ne peut venir que d'un site relu en publication `open`. Esri World Imagery n'est pas encore relu : son crédit reste dans `imagery-sources.ts`.
- **Histoire** : les captures privées restent conservées et un rejeu les relit à l'identique ; une présentation dont la collecte est interdite et sans reçu est sautée.

**En base.** La table `evidence.source_rights` (migration `0038`, journalisée) reflète le registre : une ligne active par hôte. Une revue modifiée ou retirée révoque la ligne en vigueur (`revoked_at`, `revoked_by`, motif) sans l'effacer, ce qui date chaque décision. Elle se joint aux captures par l'hôte de leur URL. Synchronisation idempotente : déploiement Prefect `source-rights` (chaque jour à 00:45, sans contacter de source), commande `python manage.py apply_source_rights --actor <nom>`, et étape finale de `rebuild-check` (politique `registry`, non bloquante). Après un déploiement qui modifie le registre, lancer la commande ou le déploiement.

**Modifier un droit.** Une ligne du registre, relue avec ses conditions citées, dans une PR ; puis la synchronisation ci-dessus.

**Activer ou couper l'application d'un droit.** Changer `enforced` dans `source_rights_enforcement.json`, avec la date, l'auteur et le motif, dans une PR. Ensuite, redéployer l'API pour la publication et l'ingestion pour la collecte. Le cache des lectures se vide au redémarrage de l'API.

### Première collecte directe de parcelles

- Couche : `MyLand/SMARTHUB/MapServer/0`, nom `PLOT`, géométrie polygonale, WGS84/EPSG:4326.
- Filtre : `DISTRICTENG = 'AL REEM ISLAND'` ; tous les enregistrements récupérés portent ce nom et `MUNICIPALITYENG = 'ADM'`.
- Résultat : **2 432 identifiants demandés et 2 432 enregistrements récupérés**, sans doublon d'OBJECTID dans cette acquisition, tous avec des anneaux géométriques. Cela ne valide pas encore leur topologie ni tous leurs attributs.
- **104 enregistrements ont `Permit_LastDate` non nul**. Cela ne signifie ni 104 permis actifs ni un historique complet des permis. L'absence de valeur n'établit pas l'absence de permis.
- Acquisition par lots de 100, avec contrôle des identifiants et de la troncature. Le service annonce un plafond de 2 000 enregistrements par réponse ; une réponse unique ne suffit pas pour cette collecte.
- Fin du lot : **2026-10-10T19:03:10.672Z**, soit 23:03:10.672 à Dubai. Chaque réponse possède ses propres heures et empreinte ; cette heure de fin n'est pas la date de publication des données.
- Captures acceptées : `.cache/source-research/onwani-reem-2026-10-10/validated-query/`. Chaque réponse `.json` possède un fichier `.receipt.json` avec URL exacte, statut HTTP, horaires et SHA-256 ; `summary.json` décrit les contrôles. Ces fichiers sont locaux et exclus de Git par `.gitignore`.
- Les premières requêtes de diagnostic, dans le dossier parent, ne constituent pas une acquisition validée. Le code `DISTRICTID = '57'` seul renvoyait aussi des enregistrements de SWEIHAN. La portée des identifiants doit donc être vérifiée avec la municipalité, le territoire et la source.
- **Aucun enregistrement n'a été importé dans PostgreSQL ni publié.** Ces captures exploratoires ne remplacent pas un connecteur reproductible. Le service ne garantit pas une photographie transactionnelle pendant les différents lots ; rapprocher les identifiants et refaire un contrôle de couverture avant publication.

## 2. Une provenance par information, pas seulement par bâtiment

Une fiche peut réunir une géométrie municipale, un nom de promoteur, une date annoncée dans une brochure et un avis d'utilisateur. Un unique champ `source_url` sur le bâtiment ne permet pas de savoir qui soutient quelle valeur.

Le modèle distingue : **source → acquisition → assertion → décision de validation → valeur métier publiée**. Une assertion est une information rapportée par une source, pas automatiquement une vérité acceptée. Les tables métier restent typées : prix décimal avec devise, dates, géométries, permis et relations explicites. Les captures brutes et extensions de collecteurs peuvent utiliser JSON ; le catalogue immobilier ne devient pas une table universelle clé/valeur.

### Répartition entre les modules

| Module cible | Objets et responsabilités |
|---|---|
| `apps/api/src/property_platform/modules/evidence/` | Sources, acquisitions, versions de captures, assertions, preuves et décisions de rapprochement réversibles |
| `apps/api/src/property_platform/modules/catalog/` | Identifiants immobiliers internes stables, parcelles, bâtiments, logements et relations acceptées |
| `apps/api/src/property_platform/modules/publication/` | Décisions de validation/publication, version affichée et références vers les preuves utilisées |

Les prix, avis et documents rejoindront leurs modules propriétaires lorsqu'ils seront introduits. Une référence de provenance doit viser un champ défini et sa version, ou un enregistrement typé identifié : pas une chaîne libre impossible à vérifier. Plusieurs preuves peuvent soutenir une valeur ; plusieurs valeurs contradictoires restent visibles dans les assertions sans écraser l'historique.

## 3. Dates et colonnes à prévoir

Les instants connus sont stockés en UTC avec fuseau. Si une source ne donne qu'un jour, conserver cette précision ; ne pas inventer une heure à minuit. Si son fuseau est inconnu, conserver la valeur brute et cette incertitude avant toute conversion. Les champs optionnels restent nuls lorsqu'ils ne sont pas connus.

| Champ ou groupe de champs cible | Signification et règle |
|---|---|
| `id`, `created_at`, `updated_at`, `revision` | Identité interne, création/modification chez nous et version pour détecter les écritures concurrentes ; ne prouvent pas la date de la source |
| `source_id`, `source_record_id`, `source_url` | Source, identifiant externe dans sa portée et URL exacte de l'information ; conserver aussi l'URL canonique si distincte |
| `source_published_at`, `source_published_raw`, `source_published_precision`, `source_timezone` | Date de publication fournie par la source, valeur originale, précision et fuseau ; inconnue si non publiée |
| `source_updated_at` et sa valeur brute/précision | Dernière modification déclarée par la source, distincte de notre collecte |
| `valid_from`, `valid_to` ou date métier dédiée | Période à laquelle la valeur concerne le monde réel : validité d'une offre, émission d'un permis, etc. ; ne pas confondre avec sa publication |
| `fetched_started_at`, `fetched_at` | Début et fin de récupération de la réponse chez nous |
| `ingested_at` | Moment où une assertion normalisée est enregistrée dans notre base ; nul pour une simple capture locale |
| `first_seen_at`, `last_seen_at` | Première et dernière observations de l'information lors de nos collectes ; ne permettent pas de connaître sa première publication |
| `reviewed_at`, `reviewed_by`, `review_reason` | Validation humaine ou automatisée, acteur identifié et justification |
| `published_at`, `publication_revision` | Moment et version de publication sur notre plateforme |
| `supersedes_id`, `retracted_at`, `retraction_reason` | Remplacement ou retrait d'une assertion/version sans perte de son historique |

Les dates appartiennent à l'objet approprié : horaires sur l'acquisition, dates externes sur la version de source/assertion, validation et publication sur leurs décisions. Ne pas recopier toutes ces colonnes dans chaque table sans relation claire.

**Attention à Onwani :** `DataReceivedDate`, `MODIFIEDDATE`, `APPROVALDATE`, `Permit_LastDate` et `MEPS_CONS_UPDATEON` portent des significations différentes. Ne pas transformer une date de réception ou de permis en date de publication. Le sens exact, la précision, le fuseau et les valeurs nulles sont documentés dans le mapping du connecteur avant usage métier.

## 4. Captures et extraction reproductibles

Pour chaque acquisition, prévoir `ingestion_run_id`, `request_id`, URL/paramètres non secrets, début/fin, statut HTTP, erreur éventuelle, empreinte SHA-256 des octets reçus, taille, type de contenu, ETag/Last-Modified lorsqu'ils sont présents, référence de stockage et version de connecteur. L'heure d'une réponse `304` est une nouvelle observation de la capture précédente, pas une nouvelle publication.

Pour chaque assertion, conserver la capture d'origine, le champ JSON ou la page du document, l'extrait utile autorisé, la langue originale, la valeur brute, la valeur normalisée, la version de mapping/extracteur et la méthode d'extraction. Une OCR, une traduction ou un calcul de proximité reste une transformation avec ses entrées et sa version. Une estimation ne devient pas une observation officielle.

Préserver les acquisitions successives sans dupliquer inutilement les fichiers identiques : capture identifiée par son empreinte, événements de collecte distincts. Une reprise du même job utilise une clé d'idempotence et des contraintes d'unicité explicites. Les échecs et lots partiels restent enregistrés ; une collecte incomplète ne remplace pas une publication complète précédente. Une disappearance dans un lot partiel ne vaut pas suppression de l'objet.

Les identifiants externes sont rattachés à l'autorité, au jeu de données et à leur portée vérifiée. `OBJECTID`, le nom commercial ou la proximité spatiale ne deviennent pas seuls notre identité métier stable. Une fusion de biens conserve les candidats, la décision, l'auteur et les preuves ; elle doit être annulable.

## 5. Audit des modifications et fiabilité

`updated_at` seul ne constitue pas un journal d'audit. Les opérations sensibles ont un événement conservant acteur (humain, service ou collecteur), heure, objet/version concerné, action, motif, référence de requête/job et changements de valeurs appropriés. Les services métier enregistrent mutation et audit dans la même transaction. API, administration et imports suivent ces mêmes règles.

Le journal est protégé contre les modifications par les rôles ordinaires ; ce choix ne le rend pas inviolable par un administrateur de base. Éviter d'y recopier secrets et contenus personnels ; définir accès et rétention des captures et journaux avant ouverture publique. Les preuves et transformations sont conservées par versions, avec une politique de retrait documentée lorsqu'un contenu ne peut plus être conservé.

La fiabilité s'évalue **pour une assertion donnée** : autorité sur ce sujet, preuve directe, précision géographique, fraîcheur, corroboration indépendante et conflits. Une source officielle sur une parcelle n'est pas automatiquement une preuve d'une date de livraison. Plusieurs sites recopiant la même annonce ne constituent pas plusieurs confirmations indépendantes.

L'IA peut proposer une extraction ou une appréciation motivée. Conserver fournisseur/modèle, version de consigne, entrées référencées et sortie ; séparer confiance de l'extraction, qualité du rapprochement et crédibilité de l'information. Pas de note universelle opaque qui publie automatiquement les prix, permis ou faits sensibles. Les avis restent des témoignages, avec date et source, distincts des faits validés.

## 6. Ordre d'implémentation et contrôles

1. Créer les modèles minimaux `catalog` et `evidence`, leurs contraintes, migrations et services ; traiter dès le début provenance et audit des décisions.
2. Construire le connecteur Onwani avec territoire explicite, mapping documenté et acquisition durable. Refaire une collecte fraîche ; les captures exploratoires permettent d'étudier le schéma mais ne sont pas le chemin de production.
3. Valider unités, SRID, géométries, portée des identifiants et dates ; conserver l'original et enregistrer toute réparation/transformation.
4. Ajouter progressivement rues/adresses, registre de projets et promoteurs, puis forums/avis/réseaux publics avec adaptateurs séparés et accès qualifiés.
5. Publier les couches et fiches avec sources par information, date de référence, dernière observation et état de validation. Une fiche peut rester incomplète sans afficher de fausses certitudes.

Tests essentiels : répétition d'un import sans doublon métier, échec puis reprise d'un lot, rejet d'un mauvais territoire, détection d'une réponse tronquée, date sans heure/fuseau, changement de valeur sans perte de la preuve précédente, contradictions entre sources, rollback simultané de mutation et audit, édition concurrente et annulation d'un rapprochement erroné. Les géométries et contraintes spatiales sont validées avec PostgreSQL/PostGIS réel.

Le prototype vise une couverture cartographique de Reem ; les informations disponibles varient selon les parcelles et sources. Il ne promet pas un dossier complet pour chaque bien ni une actualisation instantanée de tous les sites.

La [revue de base de données](DATABASE_DESIGN.md) précise les noms de domaines retenus, les contraintes SQL d'intégrité, les limites du premier modèle d'identité et les validations restantes pour permissions, versions, sauvegardes et migration des schémas. Les contraintes d'intégrité ne protègent pas à elles seules les preuves contre une modification autorisée par les droits SQL.
