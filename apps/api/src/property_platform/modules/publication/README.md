# Publication

Orchestre validation, projections et versions publiées en utilisant les interfaces du catalogue et des preuves. Ne modifie pas leurs tables par un accès ORM transversal.

API, administration et futurs workers appelleront ces mêmes commandes pour les décisions sensibles. Aucun worker ou adaptateur externe ne publie une valeur extraite sans validation.

`coverage.py` possède les profils de sources activés et compose la navigation et ses comptes via les interfaces du catalogue. Le registre d'émirats seul n'active aucune collecte. Il exporte un snapshot sans comptes pour les clients statiques ; les références et scènes sont filtrées par le profil sélectionné. Voir [UAE_COVERAGE.md](../../../../../../docs/engineering/UAE_COVERAGE.md).

`preview.py` assemble actuellement les lectures explicites de `catalog.queries` et `evidence.queries` pour l'atlas de recherche local. Il ne crée pas une version approuvée, ne modifie aucune table et ne transmet ni originaux ni identité d'opérateur. L'API de livraison refuse ces lectures hors DEBUG, indépendamment d'un flag activé. La validation des droits et une projection de publication durable seront nécessaires avant ouverture publique.

Les ingestions et projections du contexte Abu Dhabi sont décrites dans [ABU_DHABI.md](../../../../../../docs/engineering/ABU_DHABI.md). Le module conserve les responsabilités et directions de dépendance existantes.
