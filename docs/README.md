# Documentation Property Platform

- [Étude produit](product/ETUDE_PRODUIT_PROPERTY_PLATFORM.md)
- [Stratégie produit](product/STRATEGIE_PRODUIT_PROPERTY_PLATFORM.md)
- [Benchmark concurrentiel actualisé](product/BENCHMARK_CONCURRENTIEL.md)
- [Inventaire des sources publiques et ouvertes UAE : accès, couverture et priorités](product/SOURCES_DONNEES_UAE.md)
- [Design de l'accueil et première expérience](product/DESIGN_ACCUEIL.md)
- [Identité visuelle et crédits photos](engineering/VISUAL_DESIGN.md)
- [Nom générique, marque configurable et reprise locale](engineering/BRANDING.md)
- [Couverture des sept émirats et activation d'une nouvelle zone](engineering/UAE_COVERAGE.md)
- [Architecture de référence](architecture/REVUE_ARCHITECTURE_PROPERTY_PLATFORM_V2.md)
- [Contre-audit de la stack](architecture/AUDIT_DECISION_STACK_PROPERTY_PLATFORM.md)
- [Structure et responsabilités](engineering/REPOSITORY.md)
- [Démarrage et vérifications](engineering/DEVELOPMENT.md)
- [Première exploration locale : livraison et validation](engineering/ATLAS_PREVIEW.md)
- [Atlas Al Reem : couches réelles, sources et correspondance avec le HTML](engineering/REEM_MAP.md)
- [Versions des outils et compatibilités](engineering/TOOLCHAIN.md)
- [Multilingue et RTL](engineering/INTERNATIONALIZATION.md)
- [Collecte directe, provenance des données et audit](engineering/DATA_PROVENANCE.md)
- [Ingestion et orchestration Prefect : installation, interface, calendriers et exploitation](engineering/INGESTION.md)
- [Pipelines pour les fiches de projets : sources, modèles et ordre de réalisation](engineering/PROPERTY_DATA_PIPELINES.md)
- [Base de données : noms, intégrité et évolution](engineering/DATABASE_DESIGN.md)
- [Fichiers et médias : stockage local persistant, R2/S3, licences et CDN](engineering/MEDIA_STORAGE.md)
- [Revue critique de structure](engineering/STRUCTURE_REVIEW.md)
- [Feuille de route technique : performance, fiabilité et modularité](engineering/ENGINEERING_ROADMAP.md)
- [Architecture précédente, archivée](archive/ARCHITECTURE_STACK_PROPERTY_PLATFORM.md)

Les décisions actuelles et les archives sont séparées. Les documents historiques conservent leurs dates et leur contexte ; ils ne constituent pas une preuve que toutes les fonctionnalités sont implémentées.

## Enchaînement des décisions d'architecture

1. **Proposition initiale (V1 du dépôt)** : [architecture archivée](archive/ARCHITECTURE_STACK_PROPERTY_PLATFORM.md). Elle proposait Next.js et un backend NestJS/Fastify, avec PostgreSQL/PostGIS.
2. **Revue critique et architecture V2** : [revue V2](architecture/REVUE_ARCHITECTURE_PROPERTY_PLATFORM_V2.md). La réanalyse du produit et des besoins de données, de géographie et d'administration a conduit à retenir Django/GeoDjango et les workers Python. Elle a aussi examiné le document externe `Architecture_Proptech_Stack_V1.md` ; malgré son nom, ce document portait déjà un titre « révision 2 ». Ce fichier externe et la V1 archivée du dépôt sont deux propositions distinctes.
3. **Contre-audit de la décision V2** : [audit de décision](architecture/AUDIT_DECISION_STACK_PROPERTY_PLATFORM.md). Réalisé après V2, il met ses choix à l'épreuve, conserve la stack et précise les conditions de sécurité, de cohérence des données et d'exploitation. **Cet audit n'a donc pas créé V2 et ne constitue pas une V3.**
4. **Mise en œuvre du socle** : [structure du dépôt](engineering/REPOSITORY.md), puis [versions exécutables et compatibilités](engineering/TOOLCHAIN.md). Ces documents décrivent l'organisation effectivement créée et les versions retenues ; les versions évoquées dans les études historiques ne doivent pas servir de consignes d'installation.

Pour comprendre les choix actuels, lire **V2 → contre-audit → structure → versions → guide de développement**. La V1 archivée sert à comprendre les choix précédents et leur évolution.

Les [premières fiches immobilières](engineering/PROPERTY_EXPLORATION.md) décrivent l’exploration centrée sur les biens, les présentations documentées et les photos sous licence du pilote.

Depuis le 13 octobre 2026, [l'orchestration Prefect](engineering/INGESTION.md) est implémentée dans `apps/ingestion`, à côté du site et de l'API dans le même dépôt. Dix-sept déploiements couvrent Al Reem et [Saadiyat](engineering/SAADIYAT.md) ; les calendriers commencent désactivés sur une installation neuve et trois procédures restent manuelles. Les calendriers récurrents locaux sont activés le dimanche. L'interface de supervision locale sur le port 4200 utilise sa propre base de métadonnées ; les données immobilières restent dans PostGIS. Les modèles commerciaux supplémentaires décrits dans [le cadrage des pipelines](engineering/PROPERTY_DATA_PIPELINES.md) restent une extension distincte.

- [Ingestions publiques Abu Dhabi : données réelles, Prefect et accès restreints](engineering/ABU_DHABI.md).
