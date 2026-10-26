# Preuves

Possède sources, acquisitions, assertions et décisions de rapprochement. Peut utiliser les interfaces du catalogue ; ne dépend pas de publication.

Le module se range en sous-paquets (`history`, puis `sources`, `maps`, `projects`, `rebuild`) dont la direction est vérifiée par Import Linter ; voir [REPOSITORY.md](../../../../../../docs/engineering/REPOSITORY.md). `history/` possède les journaux de lignes, les exclusions réversibles, les reprises de champs et la couverture des tables par les pipelines. `sources/` possède les collecteurs et imports hors carte (ADREC, contexte public d’Abu Dhabi, pages de référence, imagerie) ; le registre `project_sources.json` reste à la racine.

Les corrections sont tracées et les rapprochements réversibles. Ce module conserve les propositions ; il ne publie pas directement les données du catalogue.

Le schéma SQL `evidence` contient `source`, `ingestion_run`, `capture`, `parcel_observation`, `audit_event`, `quarantined_observation`, `map_observation`, `research_reference` `imagery_scene`, `property_presentation` et `property_media`. Les services et commandes utilisent les modèles Django configurés pour ces noms.

`map_sources.py` et `map_import.py` collectent les couches Onwani/OSM ; `sources/research_sources.py` et `sources/research_import.py` relisent les références et extraient seulement les formats reconnus. Le retraitement conserve sa capture parent et ses dates originales. Les dérivés satellite sont préparés hors du runtime par le script isolé, puis importés avec reçu validé. Voir [la couverture Reem](../../../../../../docs/engineering/REEM_MAP.md).

Le premier connecteur `onwani.py` collecte directement les parcelles de Reem. `services.py` orchestre les captures et la transaction avec le catalogue ; `management/commands/import_onwani.py` fournit la commande manuelle. Les modèles conservent sources, acquisitions, réponses originales, observations, quarantaine et événements d'audit. Les dates externes sont préservées brutes et les dates de publication inconnues restent nulles. Voir [le contrat de provenance](../../../../../../docs/engineering/DATA_PROVENANCE.md).

`property_protocol.py` valide les reçus et licences sans exécuter leur contenu ; `property_import.py` relie des présentations examinées aux identités fournisseur exactes et conserve des versions immuables de leurs preuves. Les modèles restent typés et les géométries ne sont pas modifiées. Les lectures de contexte chargent seulement les métadonnées, jamais les captures binaires. Voir [les fiches immobilières](../../../../../../docs/engineering/PROPERTY_EXPLORATION.md).

Les ingestions et projections du contexte Abu Dhabi sont décrites dans [ABU_DHABI.md](../../../../../../docs/engineering/ABU_DHABI.md). Le module conserve les responsabilités et directions de dépendance existantes.

`project_locations.py` matérialise les points de projets explicitement déclarés dans les formats de promoteurs reconnus par `sources/research_sources.py`. L’import projet conserve capture, observation et lien révocable dans les tables existantes ; il ne transforme pas une proximité ou un bureau de vente en identité de bâtiment. `project_queries.py` livre les points et contours des liens actifs dans `map_locations`, sans captures brutes ni identité d’opérateur. Voir [PROJECTS.md](../../../../../../docs/engineering/PROJECTS.md) et [MAP_PROVIDERS.md](../../../../../../docs/engineering/MAP_PROVIDERS.md).
