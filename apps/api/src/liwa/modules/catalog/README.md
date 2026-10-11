# Catalogue

Possède l'identité des territoires, parcelles, bâtiments et logements, ainsi que leurs relations acceptées. Le premier modèle `Parcel` possède une identité UUID, une géométrie PostGIS et des attributs typés ; bâtiments et logements restent à définir. Aucun modèle générique JSON ne remplace ces invariants.

`services.py` conserve trous et polygones disjoints et rejette les géométries invalides. Le rapprochement initial est limité aux identifiants d'enregistrement de la source ; un changement d'OBJECTID ne déclenche pas une fusion automatique. La transaction appelante conserve les observations et audits dans le module evidence. Les données importées ne sont pas automatiquement publiées.

N'importe pas les modules evidence/publication ni la couche HTTP. Les autres modules utilisent ses services de mutation et ses fonctions de lecture explicites.

Le schéma SQL est `real_estate` et la table actuelle `real_estate.parcel`. Le nom de module Django `catalog` reste stable pour les migrations et références de modèles. Les nouveaux noms passent par les migrations, sans copie des données ; voir [DATABASE_DESIGN.md](../../../../../../docs/engineering/DATABASE_DESIGN.md).
