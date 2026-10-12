# Preuves

Possède sources, acquisitions, assertions et décisions de rapprochement. Peut utiliser les interfaces du catalogue ; ne dépend pas de publication.

Les corrections sont tracées et les rapprochements réversibles. Ce module conserve les propositions ; il ne publie pas directement les données du catalogue.

Le schéma SQL `evidence` contient `source`, `ingestion_run`, `capture`, `parcel_observation`, `audit_event`, `quarantined_observation`, `map_observation`, `research_reference` et `imagery_scene`. Les services et commandes utilisent les modèles Django configurés pour ces noms.

`map_sources.py` et `map_import.py` collectent les couches Onwani/OSM ; `research_sources.py` et `research_import.py` relisent les références et extraient seulement les formats reconnus. Le retraitement conserve sa capture parent et ses dates originales. Les dérivés satellite sont préparés hors du runtime par le script isolé, puis importés avec reçu validé. Voir [la couverture Reem](../../../../../../docs/engineering/REEM_MAP.md).

Le premier connecteur `onwani.py` collecte directement les parcelles de Reem. `services.py` orchestre les captures et la transaction avec le catalogue ; `management/commands/import_onwani.py` fournit la commande manuelle. Les modèles conservent sources, acquisitions, réponses originales, observations, quarantaine et événements d'audit. Les dates externes sont préservées brutes et les dates de publication inconnues restent nulles. Voir [le contrat de provenance](../../../../../../docs/engineering/DATA_PROVENANCE.md).
