# Liwa Atlas — contre-audit de la décision de stack

10 octobre 2026. Complément à `REVUE_ARCHITECTURE_LIWA_ATLAS_V2.md`. **Le socle est conservé.** Cette analyse ne constitue pas une nouvelle version de stack ; elle examine les objections et précise les conditions d'implémentation.

Méthode : lectures du cadrage produit et de V2, trois contre-revues indépendantes d'agents IA (backend, données/GIS, exploitation), confrontation aux documentations officielles et à un code source de connecteur. Aucun benchmark ni avis humain externe n'est revendiqué. La demande de réanalyse ne constitue pas, à elle seule, une raison de changer un composant.

## 1. Verdict

**Next.js/TypeScript + Django/GeoDjango + PostgreSQL/PostGIS + MapLibre + stockage objet + workers Python est une base cohérente pour Liwa Atlas.** Aucun obstacle identifié ne justifie de la remplacer avant le prototype technique. Monolithe modulaire et traitements séparés constituent le bon niveau de complexité au lancement.

Le choix des moteurs centraux est défendable. Django Ninja, Procrastinate, le dimensionnement Render/Supabase et le chemin Expo/MapLibre restent des choix secondaires à valider sur une tranche réelle. Le verdict autorise à initier cette tranche ; il ne certifie pas une capacité, une disponibilité ou une qualité de données non mesurée.

L'exigence technique se traduit par des responsabilités explicites, des invariants, des mesures et une reprise testée. Employer le même cloud qu'une grande entreprise ne fournit pas ces garanties. Le budget actuel finance un pilote ; le périmètre complet et sa croissance nécessiteront de réévaluer la capacité et les coûts.

## 2. Les contre-arguments réellement examinés

| Proposition alternative | Meilleur argument en sa faveur | Décision pour notre contexte |
|---|---|---|
| NestJS/Fastify plutôt que Django | Une équipe TypeScript confirmée peut réduire maintenance, recrutement et changements de langage | Valable, mais cette équipe n'est pas établie ; le travail éditorial/GIS/documentaire favorise ici Django. Aucune supériorité de débit Django n'est prétendue |
| FastAPI comme cœur unique | API typée, intégration naturelle de calculs Python et I/O asynchrones | Possible, mais il faudrait assembler administration, migrations et workflows dont Django fournit déjà une partie. Python seul ne départage pas les deux |
| DRF plutôt que Django Ninja | Cadre explicite pour sérialisation, politiques et opérations orientées ressources | Alternative sérieuse, pas un changement nécessaire. Ninja convient si nos politiques métier sont centralisées, testées et accessibles à tous les chemins d'accès |
| Backend Go/Rust | Intérêt possible pour un service calculatoire ou un débit identifié | Aucun profil de charge ne démontre ce besoin ; ne résout pas rapprochement des biens, provenance ni qualité documentaire |
| MongoDB ou base graphe | Souplesse de captures externes et traversées de relations | Les invariants, données financières et relations spatiales favorisent PostgreSQL ; JSONB et tables de liens couvrent le pilote |
| Redis/Celery, SQS ou microservices dès le départ | Isolation de la file, écosystème et croissance indépendante | Alternatives futures ; ajouter une infrastructure sans charge démontrée augmente aujourd'hui les coûts et les modes de panne |
| AWS complet immédiatement | Gouvernance et services spécialisés, dont workflows distribués | Option cible valable ; pas de nécessité technique ni de budget comparable démontrés pour le pilote |

Ce tableau exprime un jugement contextualisé, pas un classement absolu de frameworks. L'expérience réelle des futurs mainteneurs peut modifier le coût du choix sans invalider son architecture logique.

## 3. Corrections de conception nécessaires, sans changer le socle

### A. Les preuves ne doivent pas devenir une base métier générique

Conserver les assertions et captures variables, mais utiliser des tables et contraintes typées pour les valeurs acceptées : montant décimal, devise, offre/version, disponibilité datée, surface et convention de mesure, permis/autorité, géométrie/SRID et relations immobilières. Le filtre « deux chambres sous X AED » interroge une projection structurée et indexée ; il ne reconstitue pas tout depuis des centaines de champs JSON ou de jointures d'assertions.

Le rapprochement projet/parcelle/bâtiment/unité est une décision versionnée et réversible. Conserver candidats, observation d'origine, auteur/méthode et preuve ; pouvoir annuler une mauvaise fusion sans perdre les sources. Une proximité géographique ou un nom similaire ne prouve pas une identité. Implémenter l'historique utile progressivement ; aucun framework bitemporel universel n'est requis.

### B. Django Admin doit respecter les mêmes règles que l'API

Une administration qui écrit directement un prix publié ou change un rattachement peut contourner la validation du produit. Les champs publiés sont protégés ; les opérations sensibles appellent les services métier avec auteur, motif et version attendue. Les éditions concurrentes doivent détecter une révision obsolète. API, administration, commandes d'import et workers partagent les mêmes invariants.

Django Ninja reste acceptable. Ne pas confondre endpoints `async` et transactions asynchrones : Django 5.2 demande encore d'exécuter les blocs transactionnels dans une fonction synchrone. Commencer avec des opérations métier transactionnelles simples, puis ajouter l'asynchrone là où il apporte un bénéfice mesuré. [Transactions et async Django](https://docs.djangoproject.com/en/5.2/topics/async/).

Les quotas payants sont réservés atomiquement dans la base ; un throttle applicatif approximatif n'est pas un verrou de budget. [Limites du throttling Ninja](https://django-ninja.dev/guide/throttling/).

### C. Supabase ne doit pas exposer un second chemin métier

La phrase « le navigateur n'accède pas aux tables » doit devenir une propriété vérifiée. Les tables créées hors Dashboard ne reçoivent pas automatiquement sa configuration RLS. Isoler le domaine dans un schéma non exposé, contrôler grants et privilèges par défaut du rôle de migration, et séparer rôle de migration et rôle d'exécution. Désactiver la Data API REST/GraphQL si elle n'est pas utilisée ; vérifier séparément Auth et Storage.

Tester directement les endpoints Supabase en anonyme et en utilisateur authentifié. Tester uniquement les refus Django laisserait un éventuel contournement inaperçu. Aucun secret privilégié n'est distribué au client. [Durcissement de la Data API](https://supabase.com/docs/guides/api/securing-your-api).

Une session révoquée peut laisser un JWT déjà émis valide jusqu'à expiration. Les actions sensibles de publication et d'administration vérifient aussi l'état du compte et, lorsque requis, de la session ; le traitement de révocation est testé. [Sessions Supabase](https://supabase.com/docs/guides/auth/sessions).

### D. La queue peut être plus simple que l'outbox systématique

Le source officiel du connecteur Django Procrastinate consulté utilise la connexion Django de l'alias choisi et ses curseurs. Cela rend plausible l'enregistrement synchrone du job dans le même `transaction.atomic()` que la mutation métier. **C'est une lecture de source, pas un test de la version que nous installerons.** Si rollback et atomicité sont démontrés sur cette version, ne pas ajouter une outbox redondante. Elle reste nécessaire si la destination ou la transaction est distincte.

Le worker utilise un connecteur adapté à l'écoute PostgreSQL. Choisir connexion directe ou pooler de session pour ce chemin ; le pooler de transaction ne conserve pas l'état de session nécessaire à `LISTEN`. Vérifier réseau IPv4/IPv6 et plafond de connexions sur le véritable hébergement. Lier concurrence worker et capacité SQL ; une queue dans la base partage son domaine de panne.

[Source du connecteur Django, branche main consultée](https://github.com/procrastinate-org/procrastinate/blob/main/procrastinate/contrib/django/django_connector.py), [modes de connexion Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres).

### E. Publication et caches demandent un contrat de fraîcheur

Un manifeste compatible protège une nouvelle session ; il ne renouvelle pas magiquement une carte déjà ouverte. Lors d'une sélection, transmettre identifiant et révision : l'API retourne le dossier compatible ou signale la nouvelle publication. Les prix de l'overlay indiquent leur propre date de référence.

Définir fraîcheur et invalidation pour pages Next.js, données client, tuiles et CDN. Les données privées et réponses personnalisées ne vont pas dans un cache public partagé. Une correction ordinaire peut tolérer un délai explicite ; une révocation d'accès nécessite un chemin adapté. Un fichier déjà rendu public et téléchargé ne peut pas être récupéré chez tous les destinataires.

Next.js auto-hébergé conserve des caches locaux ; plusieurs instances nécessitent une coordination supplémentaire. Une instance au pilote est acceptable, mais sa mise à l'échelle doit tenir compte de cette réalité. [Cache et auto-hébergement Next.js](https://nextjs.org/docs/app/guides/self-hosting).

### F. Web, native et 3D sont trois chemins à valider

PMTiles fonctionne avec Supabase Storage selon la documentation Protomaps ; aucun motif établi pour remplacer ce stockage maintenant. Tester Range/`206`, CORS, ETag et cache sur le chemin réel. Les lectures contribuent aux coûts. [Stockage PMTiles](https://docs.protomaps.com/pmtiles/cloud-storage).

Le protocole JavaScript du navigateur ne garantit pas la même intégration React Native. Verrouiller Expo/RN/MapLibre compatibles ; un endpoint ZXY MVT constitue un repli possible conservant les mêmes archives. [CLI Protomaps](https://docs.protomaps.com/pmtiles/cli).

MapLibre convient à la carte urbaine ; Three.js/GLB à une scène contrôlée. Une extrusion de bâtiment ne fournit pas un logement fidèle, des ombres exactes ou une vue vérifiée. Ces fonctions se jugent sur les données et une scène étalon, pas sur le nom du moteur.

## 4. Le budget est une hypothèse d'exploitation, pas une certification

Le socle V2 à environ 345 AED/mois reste un scénario plausible, pas une capacité mesurée. La réserve de 70–120 AED doit notamment couvrir, selon les besoins, domaine, email transactionnel, copie de sauvegarde indépendante, surveillance et dépassements. Il faut chiffrer ces postes avant ouverture ; ils ne sont pas tous gratuits ni absorbés sans limite.

Supabase Auth nécessite un SMTP adapté pour les inscriptions publiques par email : son service par défaut est limité aux adresses de l'équipe et destiné aux essais. [Configuration SMTP](https://supabase.com/docs/guides/auth/auth-smtp).

Le PITR Supabase sur sept jours est affiché à environ **100 USD/mois**, avant d'éventuels autres prérequis : l'ajouter au socle ferait dépasser 500 AED. Sans mécanisme plus fréquent, une sauvegarde quotidienne peut laisser perdre les changements depuis la dernière sauvegarde, potentiellement près de 24 heures. Fixer explicitement perte acceptable et temps de reprise ; les fichiers ont leur propre protection. [Tarification PITR](https://supabase.com/docs/guides/platform/manage-your-usage/point-in-time-recovery).

Un pilote peut accepter des arbitrages documentés. Une exigence de disponibilité élevée ou de perte quasi nulle impose de revoir le budget. Les workers lourds à la demande sont un futur chemin à sélectionner et chiffrer, pas une infrastructure déjà incluse. On ne doit ni les faire tourner sur le dispatcher de 512 Mo, ni promettre toute leur automatisation avant cet essai.

Après restauration d'un état ancien, réconcilier les demandes avec les opérations déjà soumises aux fournisseurs avant de remettre la queue en route ; restaurer une base ne doit pas déclencher une seconde génération facturée.

## 5. Ce qui permettra réellement de signer la décision

La stack peut être retenue pour le prototype technique. Avant d'étendre l'implémentation produit, réaliser une tranche de bout en bout avec les données de Reem et enregistrer les résultats :

| Validation | Preuve attendue | Décision en cas d'échec |
|---|---|---|
| Identité et données | Mauvaise fusion annulée, preuves préservées ; offres/transactions séparées ; recherche de catalogue sur tables typées | Corriger le modèle avant les migrations centrales |
| Transactions et jobs | Rollback sans job fantôme, reprise après interruption, déduplication de publication et réconciliation d'une soumission payante incertaine | Corriger intégration ou ajouter outbox ; reconsidérer la queue si le défaut persiste |
| Accès | Refus API, administration, REST Supabase, fichiers et contexte IA entre utilisateurs/organisations | Corriger rôles, schémas et politiques avant publication |
| Carte et recherche | Téléphone représentatif aux Émirats, cache froid, sélection après republication, recherche annotée anglais/arabe/alias | Optimiser données et rendu ; changer moteur uniquement si cette voie ne satisfait pas le besoin |
| Exploitation | Mémoire sous charge définie, email réel, restauration base+objets, facture projetée incluant les postes annexes | Ajuster capacité ou périmètre, puis budget si nécessaire |

Le prototype historique décrit environ 2 432 géométries et 73 projets dans l'étude produit, avec beaucoup d'attributions incertaines. Cela oriente la priorité vers le contrôle des données et le chargement limité ; cela ne démontre pas un besoin actuel de systèmes distribués massifs. Les volumes futurs de documents, unités, visites et travaux doivent être estimés séparément.

**Décision maintenue : conserver le socle V2, intégrer les précisions ci-dessus dans sa conception, puis valider la tranche représentative.** Aucun remplacement de framework n'est justifié par cette contre-revue. Les hypothèses restantes sont nommées et réfutables ; si une mesure les invalide, on change le composant concerné avec un motif documenté.
