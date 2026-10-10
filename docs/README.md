# Documentation Liwa Atlas

- [Étude produit](product/ETUDE_PRODUIT_LIWA_ATLAS.md)
- [Stratégie produit](product/STRATEGIE_PRODUIT_LIWA_ATLAS.md)
- [Architecture de référence](architecture/REVUE_ARCHITECTURE_LIWA_ATLAS_V2.md)
- [Contre-audit de la stack](architecture/AUDIT_DECISION_STACK_LIWA_ATLAS.md)
- [Structure et responsabilités](engineering/REPOSITORY.md)
- [Démarrage et vérifications](engineering/DEVELOPMENT.md)
- [Versions des outils et compatibilités](engineering/TOOLCHAIN.md)
- [Multilingue et RTL](engineering/INTERNATIONALIZATION.md)
- [Collecte directe, provenance des données et audit](engineering/DATA_PROVENANCE.md)
- [Revue critique de structure](engineering/STRUCTURE_REVIEW.md)
- [Architecture précédente, archivée](archive/ARCHITECTURE_STACK_LIWA_ATLAS.md)

Les décisions actuelles et les archives sont séparées. Les documents historiques conservent leurs dates et leur contexte ; ils ne constituent pas une preuve que toutes les fonctionnalités sont implémentées.

## Enchaînement des décisions d'architecture

1. **Proposition initiale (V1 du dépôt)** : [architecture archivée](archive/ARCHITECTURE_STACK_LIWA_ATLAS.md). Elle proposait Next.js et un backend NestJS/Fastify, avec PostgreSQL/PostGIS.
2. **Revue critique et architecture V2** : [revue V2](architecture/REVUE_ARCHITECTURE_LIWA_ATLAS_V2.md). La réanalyse du produit et des besoins de données, de géographie et d'administration a conduit à retenir Django/GeoDjango et les workers Python. Elle a aussi examiné le document externe `Architecture_Proptech_Stack_V1.md` ; malgré son nom, ce document portait déjà un titre « révision 2 ». Ce fichier externe et la V1 archivée du dépôt sont deux propositions distinctes.
3. **Contre-audit de la décision V2** : [audit de décision](architecture/AUDIT_DECISION_STACK_LIWA_ATLAS.md). Réalisé après V2, il met ses choix à l'épreuve, conserve la stack et précise les conditions de sécurité, de cohérence des données et d'exploitation. **Cet audit n'a donc pas créé V2 et ne constitue pas une V3.**
4. **Mise en œuvre du socle** : [structure du dépôt](engineering/REPOSITORY.md), puis [versions exécutables et compatibilités](engineering/TOOLCHAIN.md). Ces documents décrivent l'organisation effectivement créée et les versions retenues ; les versions évoquées dans les études historiques ne doivent pas servir de consignes d'installation.

Pour comprendre les choix actuels, lire **V2 → contre-audit → structure → versions → guide de développement**. La V1 archivée sert à comprendre les choix précédents et leur évolution.
