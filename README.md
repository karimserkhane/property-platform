# property-platform

Liwa Atlas : plateforme immobilière cartographique évolutive, avec dossiers sourcés, plans, comparaison et suivi des changements. Première zone envisagée : Al Reem Island.

## Documents de cadrage

- [Étude produit](ETUDE_PRODUIT_LIWA_ATLAS.md)
- [Approfondissement stratégique](STRATEGIE_PRODUIT_LIWA_ATLAS.md)
- [Architecture actuelle — revue critique V2](REVUE_ARCHITECTURE_LIWA_ATLAS_V2.md)
- [Contre-audit : décision maintenue et conditions de validation](AUDIT_DECISION_STACK_LIWA_ATLAS.md)
- [Proposition de stack précédente — historique](ARCHITECTURE_STACK_LIWA_ATLAS.md)

Le dépôt contient actuellement le cadrage. La stack recommandée après revue est Next.js/TypeScript, Django/Django Ninja/GeoDjango, PostgreSQL/PostGIS et MapLibre, avec des workers Python séparés. Le web adaptatif précède l'application React Native/Expo. Les choix, le budget de pilote inférieur à 500 AED/mois et les essais nécessaires sont détaillés dans la revue V2 ; l'application n'est pas encore implémentée.
