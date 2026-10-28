# Catalogue

Possède `Parcel`, `Street`, `Building`, `Place` et `AdministrativeArea`, avec identités UUID, géométries PostGIS, révisions et colonnes typées. Les identités restent séparées par source ; un repère déclaré ne prouve pas une relation commerciale ou un périmètre cadastral. Les logements et projets acceptés restent à définir. Aucun modèle générique JSON ne remplace ces invariants.

`services.py` conserve trous et polygones disjoints et rejette les géométries invalides. Le rapprochement initial est limité aux identifiants d'enregistrement de la source ; un changement d'OBJECTID ne déclenche pas une fusion automatique. La transaction appelante conserve les observations et audits dans le module evidence. Les données importées ne sont pas automatiquement publiées.

N'importe pas les modules evidence/publication ni la couche HTTP. Les autres modules utilisent ses services de mutation et ses fonctions de lecture explicites.

`territories.py` possède la navigation nationale typée et les noms anglais/arabe ; ses rectangles sont approximatifs et ne créent pas de géométries officielles. Les lectures de `queries.py` acceptent des namespaces explicites ou des données bornées de tout fournisseur. Les surfaces et distances sont géodésiques, sans projection UTM unique imposée au pays. Voir [UAE_COVERAGE.md](../../../../../../docs/engineering/UAE_COVERAGE.md).

Le schéma SQL est `real_estate` : `parcel`, `street`, `building`, `place`, `administrative_area`. Le nom de module Django `catalog` reste stable. `map_queries.py` possède les lectures de contexte, les candidats spatiaux et les distances calculées dans PostGIS. `retire_map_record` désactive une attribution invalidée ; la transaction appelante conserve sa preuve et sa raison. Voir [DATABASE_DESIGN.md](../../../../../../docs/engineering/DATABASE_DESIGN.md) et [la couverture Reem](../../../../../../docs/engineering/REEM_MAP.md).

Les lectures de proximité et superposition restent calculées, sans table supplémentaire. Voir [NEIGHBOURHOOD.md](../../../../../../docs/engineering/NEIGHBOURHOOD.md) pour les budgets, les preuves et les responsabilités.
