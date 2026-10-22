# Property Platform — ingestion

Application Python dédiée à la collecte et à l'orchestration Prefect. Les collecteurs et les flows vivent ici ; les modèles, migrations et règles d'import restent dans le domaine Django `evidence`, partagé comme dépendance locale. L'API web ne dépend pas de Prefect.

Lire le [guide d'ingestion](../../docs/engineering/INGESTION.md) pour démarrer l'interface, exécuter un import et activer ses horaires. Les déploiements du registre couvrent les sources examinées d'Al Reem, Saadiyat et Al Maryah, ainsi que le contexte officiel d'Abu Dhabi. Ils ne créent pas de prix, de logements disponibles ou de couverture nationale supplémentaire.

Les tâches `maryah-…` possèdent leurs portées de collecte distinctes : parcelles, couches cartographiques, lieux Overture, références, fiches et catalogues. `maryah-osm-bootstrap` reste une reprise manuelle. Les horaires d'une nouvelle installation commencent désactivés ; un redémarrage conserve ceux modifiés dans Prefect. Les captures et versions antérieures restent conservées. Aucun import de présentation ou de média vide n'est annoncé pour Maryah.

Les pipelines communs d'archive des fonds cartographiques et de reconstruction d'un catalogue vide parcourent le même registre des trois îles. La vérification de préparation contrôle leurs registres sans acquisition et sans écriture métier ; elle ne remplace pas l'exécution des collectes dans Prefect.
