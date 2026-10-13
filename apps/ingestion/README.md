# Property Platform — ingestion

Application Python dédiée à la collecte et à l'orchestration Prefect. Les collecteurs et les flows vivent ici ; les modèles, migrations et règles d'import restent dans le domaine Django `evidence`, partagé comme dépendance locale. L'API web ne dépend pas de Prefect.

Lire le [guide d'ingestion](../../docs/engineering/INGESTION.md) pour démarrer l'interface, exécuter un import et activer ses horaires. Les neuf déploiements couvrent les sources existantes du pilote Al Reem ; ils ne créent pas de prix, de logements disponibles ou de couverture nationale supplémentaire.
