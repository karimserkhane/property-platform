# Lancer et développer Liwa Atlas, étape par étape

Ce guide décrit le **socle actuel du dépôt** : page d'attente multilingue, API de contrôle de santé et base PostGIS. Carte, fiches immobilières, authentification, médias et traitements IA arriveront avec les fonctionnalités métier.

Les commandes sont prévues pour **Windows et PowerShell**, depuis la racine du dépôt sauf indication contraire. Exécuter chaque commande séparément ; résoudre une erreur avant de poursuivre.

## 1. Choisir le parcours

| Objectif | Prérequis | Étapes |
|---|---|---|
| Voir et modifier le site | Git, Node.js 24, pnpm 11.25.0 | 2 à 4 |
| Lancer aussi l'API et PostGIS | Prérequis web + Docker Desktop avec Compose | 2 à 6 |
| Exécuter les outils Python et tests isolés sur Windows | uv 0.13.0 et Python 3.12 géré par uv | 9 |

Python et uv ne sont pas nécessaires sur Windows pour lancer l'API Docker : l'image contient leur environnement et les bibliothèques GIS. Le web actuel fonctionne seul, sans API ni compte Supabase, cartographique ou IA. Aucun service payant n'est requis pour ce lancement local.

## 2. Installer et vérifier les prérequis

### 2.1. Git et Node.js

Installer Git si nécessaire depuis [Git pour Windows](https://git-scm.com/download/win) et **Node.js de la branche 24** depuis [Node.js](https://nodejs.org/en/download). Le dépôt accepte Node.js `>=24 <25` : sélectionner 24 même si une version plus récente est proposée.

Fermer puis rouvrir PowerShell après installation pour actualiser le PATH. Vérifier :

```powershell
git --version
node --version
npm.cmd --version
```

Git et npm doivent afficher leur version ; Node doit afficher **v24.x.x**. Corriger la version utilisée si elle vaut 22, 25 ou 26 avant d'installer les paquets.

### 2.2. pnpm

Installer la version fixée dans le dépôt :

```powershell
npm.cmd install --global pnpm@11.25.0
pnpm.cmd --version
```

Résultat attendu : **11.25.0**. Les exemples utilisent `pnpm.cmd` pour éviter les blocages du wrapper PowerShell .ps1, sans changer la politique d'exécution Windows. Il s'agit du même outil que pnpm. Voir [son installation officielle](https://pnpm.io/installation).

### 2.3. Docker, pour l'API et PostGIS seulement

Installer [Docker Desktop pour Windows](https://docs.docker.com/desktop/setup/install/windows-install/) et suivre ses prérequis Windows/WSL 2. Ouvrir Docker Desktop, utiliser les **conteneurs Linux** et attendre le démarrage du moteur.

```powershell
docker --version
docker compose version
docker info
```

Les deux premières commandes doivent afficher une version et docker info les informations du serveur sans erreur de connexion. Docker Desktop doit rester démarré pendant l'utilisation de l'API et de la base.

## 3. Ouvrir le dépôt et installer les dépendances

### 3.1. Sur la machine actuelle

Le dépôt existe déjà :

```powershell
Set-Location 'C:\Users\Karim\Repositories\property-platform'
git status
```

Ne pas le cloner à nouveau dans ce dossier. Les commandes suivantes partent de cette racine, où se trouvent package.json, pnpm-workspace.yaml, apps et docs.

### 3.2. Sur une nouvelle machine seulement

Depuis le dossier où tu souhaites ranger tes projets :

```powershell
git clone https://github.com/karimserkhane/property-platform.git
Set-Location property-platform
```

Le dépôt privé nécessite les droits du compte GitHub. Utiliser le parcours d'authentification Git proposé, sans mettre de jeton dans l'URL ou un fichier du dépôt.

### 3.3. Installer les paquets web

```powershell
pnpm.cmd install --frozen-lockfile
```

Cette commande installe les dépendances JavaScript des applications/packages à partir de pnpm-lock.yaml, sans modifier ce verrouillage. Attendre sa fin sans erreur avant de démarrer.

Les scripts d'installation de Parcel/SWC sont désactivés explicitement dans pnpm-workspace.yaml ; leurs binaires de plateforme sont fournis par les dépendances optionnelles. **Ne pas ajouter --no-optional.** node_modules et .pnpm-store sont locaux et ignorés par Git.

## 4. Démarrer le site — terminal A

Depuis la racine :

```powershell
pnpm.cmd dev:web
```

Garder le terminal ouvert. Attendre que Next.js indique qu'il est prêt, puis ouvrir [le site local](http://localhost:3000).

Résultat attendu :

- La racine redirige vers /en, même si le navigateur préfère une autre langue.
- La page affiche Liwa Atlas, Al Reem Island et le texte d'attente en anglais.
- Le sélecteur propose les quinze langues configurées.
- [L'arabe](http://localhost:3000/ar), l'ourdou et le persan utilisent le sens de lecture de droite à gauche.

Si le port 3000 est occupé, Next peut en choisir un autre : utiliser l'adresse affichée dans le terminal.

Modifier par exemple apps/web/messages/en.json ou apps/web/src/app/[locale]/page.tsx puis enregistrer : le serveur de développement recharge les changements. Les textes visibles doivent rester dans les dictionnaires. Voir [la politique multilingue](INTERNATIONALIZATION.md).

**Ctrl+C** dans ce terminal arrête le site. Tant que le serveur tourne, utiliser un autre terminal pour les commandes suivantes.

## 5. Démarrer PostGIS et l'API — terminal B

Ouvrir un deuxième PowerShell pendant que le site tourne :

```powershell
Set-Location 'C:\Users\Karim\Repositories\property-platform'
docker compose -f infra/local/compose.yaml config --quiet
docker compose -f infra/local/compose.yaml up -d --build
docker compose -f infra/local/compose.yaml ps
```

La première commande valide le Compose. La deuxième télécharge PostGIS, construit l'image Python et démarre db et api en arrière-plan. Le premier lancement est plus long que les suivants.

Dans ps, attendre que **db soit healthy** et que **api soit en cours d'exécution**. En cas d'arrêt de l'API ou de base non saine, lire les journaux :

```powershell
docker compose -f infra/local/compose.yaml logs --tail 100 db api
```

### 5.1. Créer les tables Django

Lorsque les services tournent :

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
docker compose -f infra/local/compose.yaml exec api python manage.py check
```

Résultat attendu : migrations appliquées ou aucune migration restante, puis contrôle Django sans erreur. Le démarrage de l'API **n'applique pas automatiquement les migrations**.

### 5.2. Vérifier les endpoints

```powershell
Invoke-RestMethod 'http://localhost:8000/api/v1/health/live'
Invoke-RestMethod 'http://localhost:8000/api/v1/health/ready'
```

Le champ status doit valoir **ok** pour live et **ready** pour ready. live vérifie que l'API répond ; ready vérifie une connexion fonctionnelle avec PostGIS. ready ne remplace pas les migrations ni les futurs tests métier.

Ouvrir [la documentation interactive locale](http://localhost:8000/api/v1/docs) pour voir les endpoints. Les endpoints immobiliers ne sont pas encore implémentés.

Les ports sont limités à la machine locale : web 3000, API 8000, base 5432. Compose fournit déjà ses variables et identifiants de développement : **aucun .env n'est requis pour ce parcours**. apps/api/.env.example illustre une exécution Python native ; Django ne charge pas automatiquement une copie .env dans la configuration actuelle.

## 6. Créer un compte d'administration — facultatif

Après les migrations :

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py createsuperuser
```

Répondre aux questions. Le mot de passe peut ne pas apparaître pendant la saisie : c'est normal. Il n'est pas enregistré dans Git.

Ouvrir [l'administration Django](http://localhost:8000/admin/) et se connecter. Elle propose actuellement les écrans Django de base ; les modules immobiliers n'ont pas encore leurs modèles et écrans métier. Admin et docs interactives sont disponibles en configuration locale DEBUG ; ce parcours n'est pas prêt à publier.

## 7. Routine quotidienne et arrêt

### Au prochain lancement

Ouvrir Docker Desktop si l'API est nécessaire, puis depuis la racine :

```powershell
docker compose -f infra/local/compose.yaml up -d
docker compose -f infra/local/compose.yaml ps
```

Dans un autre terminal, également à la racine :

```powershell
pnpm.cmd dev:web
```

Ne pas réinstaller les paquets ni recréer le compte à chaque lancement. Après une mise à jour du dépôt, réinstaller les paquets verrouillés si les dépendances JavaScript ont changé, reconstruire l'API si son code/dépendances ont changé et appliquer les nouvelles migrations.

### Après une modification du backend

Le Compose actuel **ne monte pas le code Windows dans le conteneur** et utilise --noreload. Enregistrer un fichier Python ne change donc pas l'API qui tourne. Pour prendre en compte une modification :

```powershell
docker compose -f infra/local/compose.yaml up -d --build api
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
docker compose -f infra/local/compose.yaml exec api python manage.py check
```

Un simple restart conserve le code de l'image existante. Lorsqu'un modèle change, il faut créer et revoir ses migrations **dans le dépôt** avant de les appliquer. Une migration générée uniquement dans ce conteneur sans montage n'est pas récupérée automatiquement sur Windows.

### Lire les journaux en continu

```powershell
docker compose -f infra/local/compose.yaml logs -f --tail 100 api
```

Ctrl+C arrête le suivi des journaux, sans arrêter les conteneurs.

### Tout arrêter en conservant les données

Arrêter Next.js avec Ctrl+C dans le terminal A, puis :

```powershell
docker compose -f infra/local/compose.yaml down
```

down retire les conteneurs/réseaux locaux mais conserve le volume de base. **Ne pas ajouter -v pour un arrêt ordinaire** : cela supprimerait les données PostgreSQL, notamment les comptes et futurs dossiers pilotes.

## 8. Vérifier le site compilé

Arrêter le serveur de développement pour libérer le port 3000. Depuis la racine :

```powershell
pnpm.cmd build
pnpm.cmd --filter @liwa/web start
```

Le build utilise **Webpack** : la copie standalone avec Turbopack a échoué dans l'environnement Windows vérifié. Le développement conserve le compilateur par défaut de Next.js. Le script de pré-démarrage prépare les fichiers CSS/JS et les éventuels fichiers public du standalone.

Ouvrir [le site compilé](http://localhost:3000/en). Ce serveur ne recharge pas les modifications : arrêter, reconstruire et redémarrer pour les prendre en compte.

Pour vérifier automatiquement l'artefact, arrêter ce serveur puis exécuter :

```powershell
node scripts/prepare-web-runtime.mjs
pnpm.cmd smoke:web
```

Le contrôle attend un build existant. Il démarre un serveur temporaire sur **3101**, vérifie les quinze routes, lang/dir, traductions, sélecteur, CSS, défaut anglais et route inexistante, puis arrête son serveur. Libérer le port 3101 avant de le lancer.

## 9. Vérifier le code avant de le partager

### 9.1. Web et documentation

Avec les dépendances installées, depuis la racine :

```powershell
pnpm.cmd lint
pnpm.cmd typecheck
pnpm.cmd test:web
pnpm.cmd docs:check
pnpm.cmd contracts:check
```

Les commandes doivent terminer sans erreur. Elles contrôlent respectivement qualité/style, types, traductions, liens Markdown locaux et cohérence des types générés avec OpenAPI. Pour vérifier aussi le serveur compilé, suivre l'étape 8.

### 9.2. Python sur Windows — installation facultative

Pour les outils de qualité, l'export OpenAPI et les tests HTTP isolés, installer [uv 0.13.0 avec son installateur officiel](https://docs.astral.sh/uv/getting-started/installation/) :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/0.13.0/install.ps1 | iex"
```

Cette commande exécute l'installateur officiel dans un processus distinct. Fermer puis rouvrir PowerShell, revenir à la racine et lancer :

```powershell
uv --version
uv python install 3.12
uv sync --project apps/api --frozen --python 3.12
```

Résultat attendu : uv **0.13.0** et un environnement Python **3.12** sous apps/api/.venv avec les dépendances de apps/api/uv.lock. uv run --project apps/api sélectionne cet environnement ; aucune activation manuelle n'est requise.

Dans un terminal dédié aux tests isolés, retirer les éventuelles variables de configuration héritées :

```powershell
Remove-Item Env:DJANGO_SETTINGS_MODULE -ErrorAction SilentlyContinue
Remove-Item Env:LIWA_TEST_POSTGIS -ErrorAction SilentlyContinue
uv run --project apps/api ruff check apps/api
uv run --project apps/api ruff format --check apps/api
uv run --project apps/api lint-imports --config apps/api/pyproject.toml
uv run --project apps/api pytest apps/api/tests -c apps/api/pyproject.toml
```

Ces retraits concernent seulement ce terminal. Les tests utilisent liwa.config.settings.testing et SQLite en mémoire. Le test PostGIS est **ignoré volontairement** ; au stade actuel, attendre trois tests réussis et un ignoré. Cela valide HTTP, sans valider le SIG.

Le serveur GeoDjango et les tests PostGIS exécutés nativement nécessitent aussi GDAL/GEOS/PROJ sur l'hôte : Python seul ne suffit pas. Le parcours Docker évite leur installation sur Windows pour lancer l'API. La CI utilise ces bibliothèques et une vraie base PostGIS avec LIWA_TEST_POSTGIS=1. L'image API locale est une image runtime sans pytest/Ruff ; ne pas tenter d'y exécuter les outils de développement.

### 9.3. Après une modification du contrat API

Avec uv installé, dans le terminal des tests isolés et depuis la racine :

```powershell
uv run --project apps/api python -m liwa.export_openapi --output packages/contracts/openapi.json
pnpm.cmd contracts:generate
pnpm.cmd contracts:check
git diff -- packages/contracts
```

Revoir puis enregistrer **OpenAPI et les types TypeScript ensemble**. Ne pas modifier les types générés à la main. Le web connaît ce contrat, pas les tables Django.

## 10. Résoudre les problèmes courants

| Symptôme | Vérification et action |
|---|---|
| node, pnpm ou uv introuvable | Rouvrir PowerShell après installation ; vérifier Get-Command node, Get-Command pnpm.cmd ou Get-Command uv |
| pnpm.ps1 bloqué | Utiliser pnpm.cmd comme dans ce guide |
| Erreur de version/engine | Vérifier Node 24 et pnpm 11.25.0 ; ne pas contourner engineStrict |
| ERR_PNPM_UNEXPECTED_STORE | Vérifier storeDir dans le dépôt ; réinstaller avec pnpm.cmd install --force --frozen-lockfile si les paquets locaux provenaient d'un autre store |
| Docker ne joint pas son moteur | Ouvrir Docker Desktop, attendre son démarrage et vérifier les conteneurs Linux avec docker info |
| Port 8000 ou 5432 occupé | Identifier le programme avec Get-NetTCPConnection -LocalPort 8000,5432 -ErrorAction SilentlyContinue ; arrêter seulement un service reconnu ou adapter les ports locaux dans Compose |
| ready répond 503 | Lire les logs db/api, vérifier db healthy et la connexion PostGIS ; ne pas supprimer le volume pour tenter une réparation |
| API inchangée après édition Python | Reconstruire l'image API comme à l'étape 7 |
| Admin refuse la connexion | Vérifier migrations, création du superutilisateur et configuration locale |
| CSS/JS absent en standalone | Reconstruire puis lancer node scripts/prepare-web-runtime.mjs, ou utiliser start qui fait cette préparation |
| Erreur certificat TLS à l'installation | Vérifier les certificats du système/réseau ; Node 24 permet $env:NODE_OPTIONS='--use-system-ca', uv accepte --system-certs sur sa commande réseau ; ne pas désactiver la vérification TLS |

### Cas particulier : cache natif SWC sous Windows

Si l'erreur cite ERR_SWC_NATIVE_CACHE, un propriétaire non fiable ou des permissions de remplacement, le chargeur refuse le cache Windows. Ce n'est pas une erreur de traduction.

Un cache privé a été créé et vérifié sur la machine Karim pendant la mise en place. Depuis **le PowerShell du compte Karim**, si ce dossier existe encore, le sélectionner avant les commandes web :

```powershell
$env:SWC_NATIVE_BINDING_CACHE = Join-Path $env:USERPROFILE '.cache\liwa-swc-private'
Test-Path -LiteralPath $env:SWC_NATIVE_BINDING_CACHE
pnpm.cmd dev:web
```

Test-Path doit répondre **True**. La variable est propre au terminal ; la définir aussi dans celui qui exécute typecheck/build si nécessaire. Ce cache extérieur au dépôt ne doit pas être committé ; il est accessible au compte Karim, pas nécessairement au compte sandbox d'un outil.

Sur une autre machine, le cache par défaut peut fonctionner sans configuration. En cas de problème, utiliser un répertoire privé dont les permissions et celles des parents sont compatibles avec SWC. Conserver les contrôles de sécurité et ne pas modifier les permissions de tout le profil. Voir [le fonctionnement officiel du cache SWC](https://github.com/swc-project/swc/blob/main/docs/native-addon-carriers.md).

## 11. Du lancement local à la production

Ce guide démarre les services sur ta machine ; il ne publie rien sur Internet. Les clés et identifiants Compose sont exclusivement pour le développement.

Un déploiement public nécessitera HTTPS/reverse proxy, secrets réels (DJANGO_SECRET_KEY, DATABASE_URL, DJANGO_ALLOWED_HOSTS), accès du personnel, statiques d'administration, sauvegardes et rôles SQL. Les migrations restent une étape explicite du déploiement. La CI vérifie sources, contrats, PostGIS et images : observer son résultat GitHub avant de considérer les contrôles distants comme réussis.

Pour poursuivre, lire [les frontières des modules](REPOSITORY.md) et [la revue de structure](STRUCTURE_REVIEW.md). Prochaine étape métier : définir le dossier pilote, puis développer le parcours carte → fiche → preuve → correction → publication.
