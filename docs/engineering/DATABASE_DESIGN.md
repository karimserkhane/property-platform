# Base de données : décisions, audit et évolution

Revue du 11 octobre 2026, fondée sur les modèles, migrations, services, tests et une inspection en lecture seule de la base locale `property_platform`. Ce document couvre organisation métier, intégrité, géographie, acquisition, sécurité et exploitation. Il ne constitue pas une certification de production et ne prouve pas qu'un mécanisme prévu existe déjà.

## 1. Décision de nommage

Le nom retenu pour le **domaine immobilier et son schéma SQL** est `real_estate`. Il décrit durablement les parcelles, projets, bâtiments et logements, indépendamment de la marque Property Platform et du territoire Reem. `catalog` reste le nom du module Django installé pour préserver les identifiants des modèles et l'historique des migrations. La table est désormais `real_estate.parcel` après application des migrations.

Un schéma regroupe des objets dans une base. Ce n'est ni un dossier du dépôt ni un serveur supplémentaire. PostgreSQL permet des schémas pour organiser les objets et contrôler leurs accès ; le schéma seul n'apporte pas un gain de vitesse. Voir [la documentation PostgreSQL 18](https://www.postgresql.org/docs/18/ddl-schemas.html).

| Domaine cible | Contenu | Tables ou exemples | État |
|---|---|---|---|
| `real_estate` | Biens, projets et relations acceptées | `parcel`, `building`, `unit`, `development_project` | Schéma créé : parcel, street, building, place, administrative_area ; unités/projets acceptés à créer |
| `evidence` | Origine des informations, acquisitions et observations | `source`, `ingestion_run`, `capture`, `parcel_observation` | Schéma créé avec onze tables, dont map_observation, research_reference, imagery_scene, property_presentation et property_media |
| `publication` | Dossiers validés et versions accessibles au public | `project_version`, `publication_decision` | Première fonctionnalité de publication |
| `market` | Transactions, offres, prix et échéanciers | `transaction`, `listing`, `price_observation`, `payment_schedule` | Première fonctionnalité de prix ; responsabilités à documenter |
| `media` | Métadonnées des documents, images, vidéos et dérivés | `asset`, `asset_version`, `processing_result` | Premier traitement documentaire ; fichiers dans un stockage adapté |

`real_estate` et `evidence` sont implémentés ; `publication`, `market` et `media` restent des domaines futurs. Lieux et rues sont désormais possédés par le catalogue géographique ; avis et médias complets demanderont leur propre décision. Aucun schéma par pays, île, langue ou source : les territoires et langues sont des données liées aux objets. Dev, test et production sont des bases/environnements séparés, pas des schémas d'une même base de production.

Conventions : anglais, minuscules, `snake_case`, noms de tables au singulier, noms de colonnes précis, clés étrangères `<objet>_id`. Éviter les noms de marque, `data`, `misc`, `table1` et les suffixes `v2` pour contourner les migrations. Les noms internes des contraintes existantes ne sont pas renommés pour l'apparence.

Noms actuels : `property_platform.real_estate.parcel` et `property_platform.evidence.capture`. Dans une connexion PostgreSQL à `property_platform`, on écrit habituellement `real_estate.parcel` et `evidence.capture`. Le qualificatif de base ne permet pas d'interroger une autre base depuis la même connexion.

## 2. Ce qui existe réellement

La portée du produit est nationale : les géométries WGS84 des tables acceptent déjà des objets hors Reem. Le registre de navigation des sept émirats n'ajoute aucune frontière fictive ni migration aux tables ; voir [UAE_COVERAGE.md](UAE_COVERAGE.md). Les rapprochements administratifs canoniques et leurs dates seront ajoutés avec des sources vérifiées, sans réutiliser les rectangles d'interface comme preuve foncière.

Après application des migrations, les tables métier sont réparties entre `real_estate` et `evidence`. Les anciens noms disparaissent sans créer de seconde copie :

| Ancien nom | Propriétaire Django | Nom actuel |
|---|---|---|
| `public.catalog_parcel` | `catalog` | `real_estate.parcel` |
| `public.evidence_source` | `evidence` | `evidence.source` |
| `public.evidence_ingestionrun` | `evidence` | `evidence.ingestion_run` |
| `public.evidence_capture` | `evidence` | `evidence.capture` |
| `public.evidence_parcelobservation` | `evidence` | `evidence.parcel_observation` |
| `public.evidence_auditevent` | `evidence` | `evidence.audit_event`, audit limité aux parcelles aujourd'hui |
| `public.evidence_quarantinedobservation` | `evidence` | `evidence.quarantined_observation` |

Les tables techniques Django restent gérées par leurs migrations. Les extensions PostGIS et leurs fonctions ne doivent pas être déplacées comme des tables ordinaires. `tiger` et `topology`, présents dans l'image locale, ne sont pas utilisés par notre import. Leur présence ne signifie pas que leurs données alimentent le site.

L'inspection locale a trouvé PostgreSQL 18.6 et PostGIS 3.6.4, 2 431 parcelles valides/non vides en EPSG:4326, une observation en quarantaine et aucun lien contradictoire entre les événements d'audit, observations et acquisitions existants. Ce sont des constats datés, pas des effectifs garantis pour les imports futurs. Les tables métier restent de petite taille ; rien ne justifie aujourd'hui partitionnement, réplication de lecture ou séparation en plusieurs bases.

Les couches supplémentaires et leur provenance sont décrites dans [REEM_MAP.md](REEM_MAP.md). Les migrations catalog 0004 et evidence 0005–0009 ajoutent les tables typées, le reçu d’acquisition, les références, les aperçus et la capture parent. Les parcelles existantes restent dans real_estate.parcel. Capture parent, observations et scènes utilisent des clés étrangères protégées ; une invalidation de repère conserve identité et historique avec active=false. Les petits PNG du pilote ne remplacent pas le futur stockage objet.

## 3. Migration et compatibilité Django

Les migrations [catalog/0003_real_estate_schema.py](../../apps/api/src/property_platform/modules/catalog/migrations/0003_real_estate_schema.py) et [evidence/0004_evidence_schema.py](../../apps/api/src/property_platform/modules/evidence/migrations/0004_evidence_schema.py) déplacent les tables avec des noms SQL qualifiés, puis synchronisent les modèles Django avec `SeparateDatabaseAndState`. Les migrations précédemment appliquées ne sont pas modifiées. Index, contraintes, clés étrangères et séquences associées restent liés aux tables déplacées.

Les modèles utilisent des noms simples dans `db_table` : `parcel`, `capture`, etc. La connexion Django possède un `search_path` fixe `public,real_estate,evidence`, sans schéma dérivé du nom de l'utilisateur. Cette approche conserve le backend Django/PostGIS standard et la concordance des noms entre modèles et introspection, nécessaire notamment à `flush`. Aucun backend personnalisé n'a été ajouté. `public` en tête conserve les tables techniques et objets d'extension au bon endroit lors d'une installation fraîche ; il ne doit pas contenir de table homonyme masquant un domaine.

Les noms de tables doivent être uniques sur ce chemin. Les migrations refusent les collisions avec des tables homonymes dans les schémas prioritaires. Les SQL de maintenance utilisent des noms qualifiés, par exemple `evidence.capture`. Les rôles de production devront disposer de `USAGE` et des droits d'objets appropriés, sans droit de création arbitraire sur les schémas du chemin. Ajouter un domaine impose de revoir ce chemin, les noms et leurs permissions.

Pour un nouveau modèle, `db_table` simple fixe le nom, pas le schéma de création. Une migration générée peut créer sa table dans `public` : sa migration doit donc prévoir explicitement son placement dans le schéma propriétaire. Le test PostGIS d'appartenance des tables contrôle cette règle pour tous les modèles gérés de `catalog` et `evidence`, ainsi que l'unicité de leurs noms. Les nouveaux domaines devront étendre ce contrôle.

Chaque migration est transactionnelle et prend à l'aller le verrou de l'import Onwani ; une maintenance, y compris une annulation, doit malgré tout être faite sans commandes d'import concurrentes. Les deux migrations sont des étapes distinctes : en cas d'échec de la seconde, corriger la cause et relancer `migrate`, qui reprend les étapes non appliquées. Leur annulation remet les tables dans `public` sous leurs anciens noms et conserve les données. Les schémas alors vides sont laissés en place pour éviter de supprimer des objets ajoutés indépendamment. Lors d'une annulation, revenir aussi au code et aux modèles correspondant aux anciennes migrations.

## 4. Audit d'intégrité et corrections immédiates

Un contrôle Python protège le chemin d'import. Une contrainte SQL protège aussi les écritures qui contournent ce chemin. Les deux sont nécessaires.

| Sujet | État vérifié avant cette revue | Correction ou décision |
|---|---|---|
| Identité | UUID interne et unicité `(source_namespace, source_record_id)` | Conserver ; refuser aussi les identifiants vides ou composés seulement d'espaces |
| Géométrie | Type `MultiPolygon`, SRID 4326 et index GiST ; validité contrôlée dans le service | Ajouter une contrainte SQL de validité et de non-vacuité |
| Révision | Entier positif Django autorisant aussi zéro dans sa contrainte SQL | Exiger une révision au moins égale à 1 |
| Acquisition | Statut et dates enregistrés, mais texte de statut libre en base | Exiger les états actuels et leur cohérence avec les dates de fin |
| Capture | Réponse brute, dates, hash et code HTTP | Contraintes SQL sur la plage HTTP, l'ordre des dates de collecte et le format SHA-256 |
| Audit | Création et changement en transaction avec les observations | Contraintes sur actions actuelles, révision, opérateur et motif non blancs |
| Relations | Clés étrangères, protections Django contre la suppression et unicité par capture | Conserver ; elles ne garantissent pas à elles seules toutes les cohérences entre plusieurs liens |

Les corrections sont dans les modèles et migrations suivantes :

- [apps/api/src/property_platform/modules/catalog/models.py](../../apps/api/src/property_platform/modules/catalog/models.py)
- [apps/api/src/property_platform/modules/catalog/migrations/0002_enforce_data_integrity.py](../../apps/api/src/property_platform/modules/catalog/migrations/0002_enforce_data_integrity.py)
- [apps/api/src/property_platform/modules/evidence/models.py](../../apps/api/src/property_platform/modules/evidence/models.py)
- [apps/api/src/property_platform/modules/evidence/migrations/0003_enforce_data_integrity.py](../../apps/api/src/property_platform/modules/evidence/migrations/0003_enforce_data_integrity.py)
- [apps/api/tests/test_onwani_postgis.py](../../apps/api/tests/test_onwani_postgis.py)

Une acquisition `running` n'a pas de date de fin ; `succeeded`, `quarantined` ou `failed` ont une date de fin au moins égale à celle du début. Un processus interrompu peut laisser `running` : une future réconciliation de tâches devra traiter ce cas, plutôt que d'inventer une réussite. Les états d'audit actuels sont `created` et `updated` ; de nouveaux types d'opérations nécessiteront une migration explicite.

Les contraintes ne vérifient pas encore le contenu des compteurs JSON, que la taille déclarée égale celle du binaire, que le hash correspond réellement au contenu, ni toute la cohérence des clés étrangères croisées. Le service reste responsable de ces invariants ; une évolution des écritures demandera une revue des garanties SQL supplémentaires.

## 5. Modèle immobilier et identité multi-source

Une parcelle n'est ni un bâtiment ni un logement. Un projet commercial peut regrouper plusieurs parcelles/bâtiments ; une parcelle peut contenir plusieurs bâtiments. Les relations réelles doivent déterminer les cardinalités et permettre leurs évolutions : ne pas coder arbitrairement « un projet = une parcelle = un bâtiment ».

Avant le deuxième collecteur décrivant les mêmes biens, séparer l'identité interne des identifiants externes dans des correspondances typées. Aujourd'hui, la paire source/enregistrement est directement portée par `Parcel` : adaptée au premier import, insuffisante pour réunir plusieurs sources sans doublons. Les rapprochements conserveront preuve, opérateur/méthode, état et possibilité d'annulation. Une proximité géographique ou un nom similaire ne suffit pas pour fusionner automatiquement deux objets.

Les municipalités, quartiers, rues et promoteurs sont encore des valeurs de source ou des objets à développer. Une normalisation future doit conserver ces libellés originaux et leurs correspondances ; elle ne doit pas déduire une identité certaine d'une simple orthographe. La table de correspondance ne devient pas une table JSON universelle pour tous les domaines.

## 6. Provenance, historique et publication

Conserver séparément capture originale, observation, décision et valeur acceptée. Une date de collecte ne remplace pas une date de publication ; une date inconnue reste inconnue. Les instants utilisent UTC, les dates sans heure restent des dates, et la précision/fuseau de la source est conservée. Voir [DATA_PROVENANCE.md](DATA_PROVENANCE.md).

La révision de `Parcel` suit aujourd'hui l'état accepté courant. Les observations/captures permettent de retrouver ses entrées historiques, mais il n'existe pas encore de table complète de versions métier des parcelles. Une requête « que savions-nous à telle date ? » demandera des versions explicites et, si nécessaire, la distinction entre date de validité dans le monde et date d'enregistrement chez nous.

Prix, transactions, disponibilité et échéanciers nécessiteront des tables typées et datées, avec montant décimal, devise, unités et preuve. Aucun montant monétaire en flottant ; distinguer prix annoncé, transaction observée et estimation. Plans de paiement : dates/événements déclencheurs et montants/pourcentages contrôlés selon le produit, sans imposer une règle universelle arbitraire à toutes les offres.

Un score de fiabilité porte sur une information et ses preuves, avec version des règles, date de calcul et explication. Plusieurs sites recopiant la même annonce ne sont pas des confirmations indépendantes. Une traduction, une OCR ou une génération IA conserve ses entrées, fournisseur/modèle, version et coût ; elle n'est pas présentée comme une observation officielle.

La publication est une décision distincte. Les futurs lecteurs publics doivent accéder aux projections autorisées, sans exposer automatiquement captures brutes, coordonnées personnelles ou documents à accès limité.

## 7. Géographie et performance

Conserver le SRID explicite, les trous et parties disjointes ; ne pas réparer silencieusement une géométrie. `ST_IsValid` contrôle la validité en 2D, pas la vérité d'une limite cadastrale. [Référence PostGIS](https://postgis.net/docs/ST_IsValid.html)

EPSG:4326 convient aux échanges longitude/latitude. Une aire calculée directement sur cette géométrie n'est pas une superficie en m² : utiliser une projection adaptée ou un calcul `geography` selon la mesure voulue. Une altitude, un étage et une emprise 2D sont des informations différentes. [Unités de ST_Area](https://postgis.net/docs/ST_Area.html)

L'index spatial GiST existe déjà. La future API cartographique devra filtrer par emprise, borner le nombre de résultats et proposer un niveau de détail adapté au zoom. Les prédicats doivent utiliser l'index ; ne pas charger toutes les géométries, captures et observations pour chaque déplacement de carte. [Index spatiaux PostGIS](https://postgis.net/documentation/faq/spatial-indexes/)

Les clés étrangères sont indexées et l'identité de source est unique. Les index composites pour historique d'un bien ou imports d'une source seront définis avec les requêtes, vérifiés avec `EXPLAIN (ANALYZE, BUFFERS)` sur un jeu représentatif. Pas d'index sur toutes les colonnes ni de GIN général sur les JSON sans requête justifiée. Partitionnement, caches et vues matérialisées doivent répondre à des mesures ; 2 431 parcelles ne suffisent pas à les justifier.

## 8. Acquisition, stockage et tâches

Le connecteur actuel possède limites de réponse, contrôle de territoire/couverture, verrou PostgreSQL, quarantaine et écriture atomique. Une nouvelle acquisition n'efface pas les captures précédentes ; un échec préserve les captures déjà reçues. L'absence d'une parcelle dans une acquisition ne provoque pas sa suppression automatique.

Le verrou sérialise Onwani seulement : ce n'est pas une protection universelle contre des mises à jour concurrentes par les futures API ou collecteurs. Ces écritures devront partager les services propriétaire, transactions et politique de conflit/version.

Les JSON bornés restent dans PostgreSQL aujourd'hui. Documents, photos et vidéos iront dans un stockage objet avec références, empreintes, formats, droits, versions et politique de rétention. Déduplication physique et réutilisation logique d'une preuve sont deux décisions différentes. Les fichiers originaux autorisés ne doivent pas être remplacés par leurs dérivés.

Automatisation future : identifiants durables de tâches, états, reprises bornées, détection des tâches bloquées, journalisation et alertes sur erreurs significatives. Pour les appels payants : réservation de budget et réconciliation avant retry. L'idempotence des parcelles n'empêche pas une double facturation d'une vidéo générée. Pas de collecte longue ou rendu 3D dans une requête de visiteur.

## 9. Permissions, données personnelles et exploitation

Le rôle local `property_platform` est superutilisateur, comme créé par l'image PostgreSQL avec ses paramètres de développement. Ce rôle ne doit pas devenir le rôle d'exécution en production. L'inspection du schéma `public` n'a pas montré un droit `CREATE` pour tous les rôles : le nom « public » ne signifie pas « accessible sur Internet ».

Avant production : rôle propriétaire/migrations distinct du rôle API ; collecteur et lecteur avec droits adaptés ; accès réseau limité ; secrets propres à l'environnement ; `search_path` maîtrisé. Les schémas ne sont une frontière d'accès que si les droits des schémas **et des objets** le prévoient. Les droits par défaut des nouveaux objets doivent être traités aussi. Aucun rôle d'exécution ne doit pouvoir créer/remplacer arbitrairement les fonctions qu'il utilise. [Schémas et permissions PostgreSQL](https://www.postgresql.org/docs/18/ddl-schemas.html)

L'audit n'est pas encore protégé en écriture par un rôle SQL distinct. Les contrôles de modèle ne rendent pas un journal immuable. Restreindre modifications/suppressions de preuves et événements pour les rôles ordinaires, tout en conservant un traitement autorisé des retraits et durées de conservation. Les opérateurs actuels sont des libellés fournis à une commande de maintenance, pas une authentification des utilisateurs publics.

Avant avis, comptes publics ou sources sociales : règles d'accès, minimisation des données personnelles, retrait, rétention et limites de réutilisation documentées. Une politique d'accès par organisation, si le produit l'introduit, demandera des contrôles et tests dédiés ; aucun mécanisme de multi-tenant ou RLS n'est supposé existant.

Un volume Docker persistant n'est pas une sauvegarde. Prévoir sauvegarde indépendante, chiffrement et accès, puis tester la restauration dans une base distincte. Définir les objectifs de perte de données et de temps de remise en service. La production pourra demander une restauration à un instant donné via WAL/PITR. Ne pas copier les fichiers internes d'une base en fonctionnement comme méthode de sauvegarde improvisée. [Sauvegardes PostgreSQL](https://www.postgresql.org/docs/18/backup.html)

Surveiller échecs/durée/ancienneté des imports, quarantaine, dérive de schéma externe, volume des captures, stockage libre, connexions, requêtes lentes et verrous. Configurer les limites de connexions/timeouts selon les workers et la concurrence réelle. Migrations contrôlées, maintenance PostgreSQL et restauration font partie de l'exploitation ; aucun de ces mécanismes ne découle du simple lancement de Docker.

## 10. Ordre de mise en œuvre et critères de validation

| Priorité | Travail | Condition de fin |
|---|---|---|
| Maintenant | Contraintes d'intégrité de la section 4 | Migrations fraîches et sur données existantes ; rejet SQL des écritures invalides ; import/rollback/quarantaine toujours corrects |
| Implémenté | Migration `real_estate`/`evidence` compatible Django | ORM, introspection, migrations aller/retour, séquences, contraintes, `flush`, tests et restauration validés sur PostGIS |
| Avant plusieurs sources immobilières | Correspondances d'identité et rapprochements réversibles | Deux sources pour un bien sans fusion incontrôlée ; annulation d'un rapprochement testée |
| Avec la carte et les fiches | Modèles bâtiments/logements, versions/publication et requêtes spatiales | Provenance visible, limites de lecture, contrats, tests de publication et plans de requêtes mesurés |
| Avec la collecte automatique | Tâches durables, reprises, observations de qualité | Échec/reprise, concurrence et détection de tâches bloquées testés |
| Avant accès public | Droits d'exécution, protection des preuves, sauvegarde/restauration et supervision | Tests avec les vrais rôles, accès refusés quand attendu et restauration vérifiée |

La migration de noms conserve UUID, observations, audit, captures et relations. Préparer une sauvegarde vérifiée et un relevé des effectifs/identités ; appliquer en période contrôlée, comparer après migration et reconstruire les programmes utilisant les noms. Ne pas éditer les migrations déjà appliquées. [Opérations de migration Django](https://docs.djangoproject.com/en/6.1/ref/migration-operations/)

La structure cible ne crée pas de nouveaux modules Python à elle seule. Les propriétaires actuels et dépendances restent ceux de [REPOSITORY.md](REPOSITORY.md). Toute création/renommage de module devra actualiser ce document, Import Linter, migrations, CI et guide de développement.

## 11. Vérifications de cette revue

- 54 cas distincts vérifiés avec succès sur PostGIS temporaire : suite de 52 tests backend, puis contrôles ciblés de migrations/conflits et d'appartenance des tables. Ils couvrent HTTP, protocole, import, transactions, quarantaine, refus SQL, migrations aller/retour avec données, introspection, sérialisation, `flush`, séquences et reprise après collision de nom.
- Ruff, formatage, frontières Import Linter, absence de migrations manquantes, liens locaux et vérification du diff réussis. Ces contrôles locaux ne constituent pas un résultat de CI distante.
- Sauvegarde locale PostgreSQL au format personnalisé, exclue de Git, restaurée dans une base temporaire distincte. Effectifs et empreintes de contenu identiques pour les sept tables métier ; seule cette base temporaire a été supprimée après le contrôle.
- Image API reconstruite et migrations d'intégrité puis de schémas appliquées à la base locale. Comparaison avant/après du contenu complet, des effectifs et identités PostgreSQL des sept tables : identiques. Aucun ancien nom de table métier ne subsiste dans `public` ; tables techniques et extensions restent en place.
- Import réel après déplacement : `created=0`, `updated=0`, `unchanged=2431`, `observed=2432`, `quarantined=1`. Une nouvelle acquisition conserve ses captures et observations dans `evidence`, sans doublon de parcelle dans `real_estate`. La quarantaine existante n'est pas une erreur de migration.

Ce contrôle ponctuel de restauration n'est pas un service de sauvegarde automatique. Les rôles de production, les reprises de tâches et les versions métier complètes restent à réaliser aux étapes indiquées ci-dessus.

## 12. Identité technique générique — 12 octobre 2026

Le nom de la base et du rôle locaux est devenu `property_platform`. Les références techniques et chemins de ce document ont été actualisés ; le contexte et les résultats de la revue précédente restent historiques. Les labels Django et les schémas métier conservent leur identité.

Le script [migrate-local-identity.mjs](../../scripts/migrate-local-identity.mjs) a sauvegardé la base existante, restauré son contenu dans un volume cible neuf `property-platform-local_postgres18-data`, puis comparé les effectifs et empreintes du contenu de **25 tables**, couvrant `public`, `real_estate` et `evidence` : identiques. La sauvegarde, son SHA-256 et les rapports sont sous `.cache/backups/`, exclus de Git. La source est conservée arrêtée pour récupération ; aucune capture ou observation n'a été réécrite pour changer la marque.

Les paramètres de l'installation active et le parcours de reprise sont dans [BRANDING.md](BRANDING.md). Un changement ultérieur du nom affiché sur le site ne change ni cette base, ni ses tables, ni ses rôles.

## Premières présentations et images documentées

La migration evidence 0010 ajoute `property_platform.evidence.property_presentation` et `property_platform.evidence.property_media`, sans modifier les identités ou déplacer les données existantes. Présentation typée, cible exclusive bâtiment/lieu, captures de source et de licence protégées par FK, version de revue, dates et contrôle de diffusion sont décrits dans [PROPERTY_EXPLORATION.md](PROPERTY_EXPLORATION.md). Ces petites captures photo de pilote ne remplacent pas le futur domaine média, son stockage objet et ses workflows de droits/administration.
