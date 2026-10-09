# Structure et règles de dépendance

Le dépôt conserve les choix de la revue V2 et du contre-audit. Un monorepo contient plusieurs applications, sans en faire des microservices. Les études sont dans `docs/product`, les décisions actuelles dans `docs/architecture` et les propositions remplacées dans `docs/archive`. Seuls README et AGENTS restent des documents Markdown de racine.

```text
apps/
  web/                     Next.js ; présentation et orchestration de l'interface
    messages/              traductions de l'interface par langue
    src/i18n/              langues, routage et configuration de traduction
    src/app/[locale]/      pages et layout localisés
    tests/                 contrats de traduction et routage
  api/
    src/liwa/
      config/              configuration Django, URL et démarrage
      api/                 transport HTTP, validation des entrées/sorties
      modules/
        catalog/           identité et relations immobilières
        evidence/          sources, assertions et décisions de rapprochement
        publication/       validation et versions publiées
    tests/                 contrôles HTTP et intégration PostGIS
packages/
  contracts/               OpenAPI exporté par Python et types TypeScript générés
infra/local/               PostgreSQL/PostGIS et API locaux via Compose
docs/                     produit, architecture, ingénierie et archives
scripts/                  contrôles du dépôt et préparation de l'artefact web
.github/workflows/         vérifications reproductibles
```

## Ce qui rend cette organisation modulaire

- Chaque module possède ses mutations et invariants. Les appels externes passent par des services explicites ; aucun module ne modifie les tables d'un autre directement.
- Dépendances autorisées : publication → evidence → catalog, et publication → catalog. Les modules n'importent ni configuration ni HTTP. Import Linter vérifie ces directions en CI ; il ne peut pas détecter tous les accès ORM indirects, qui restent à examiner en revue.
- API, administration et futurs workers appellent les mêmes commandes métier. Les dépendances lourdes OCR/Blender ne sont pas installées dans le serveur web.
- Le backend possède schémas et migrations métier. OpenAPI est exporté, les types TypeScript sont générés et la CI détecte leur divergence.
- Le web ne connaît pas les tables ni les modèles Django. Chaque fonctionnalité future sera regroupée sous `src/features/<fonction>` ; seuls les composants réellement partagés rejoignent une bibliothèque commune.
- Les adaptations de stockage, authentification et fournisseurs seront introduites avec leur première utilisation. Aucun framework abstrait de plugins n'est créé d'avance.

Les workers légers utiliseront le même paquet Python que l'API, avec un processus distinct. Une image spécialisée sera ajoutée pour le calcul lourd. Mobile, market, reviews et scenes arrivent lorsqu'une fonctionnalité les justifie ; aucun dossier vide ne simule une application prête.

## Invariants de travail

1. Aucun secret ni original documentaire privé dans Git. Utiliser `.env.example` pour les noms et paramètres locaux ; les environnements réels utilisent leurs secrets propres.
2. Les tables métier publiées restent typées ; propositions et preuves ne remplacent pas les contraintes du catalogue.
3. Une opération sensible conserve auteur, raison et version ; les permissions couvrent HTTP, administration, fichiers et futurs traitements.
4. Toute évolution d'API conserve sa compatibilité ou documente une rupture. Les types générés ne sont jamais édités manuellement.
5. Les migrations sont revues et exécutées explicitement, pas au démarrage concurrent de chaque processus. Les comptes base de migration/exécution seront séparés au déploiement.
6. Les durées, montants et identifiants sont validés côté serveur. UTC en stockage ; fuseau et format d'affichage côté client.
7. L'anglais est la langue par défaut. Les traductions d'interface restent séparées des traductions documentaires ; les preuves originales et identifiants restent stables. Les layouts utilisent des propriétés CSS logiques pour le RTL.

## Ce que le socle ne prétend pas fournir

Les trois modules Django sont des limites de responsabilité, sans modèle métier inventé avant le dossier pilote. La page web est une page d'attente. Auth Supabase, stockage, carte, collecteurs, queue et génération ne sont pas encore intégrés. Les seuls endpoints sont liveness et readiness PostGIS. L'administration Django est locale à ce stade ; elle ne doit pas être ouverte en production avant le parcours d'accès du personnel et ses règles métier.
