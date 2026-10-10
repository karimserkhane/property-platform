# Lancer et développer Liwa Atlas, étape par étape

Ce guide décrit le **socle actuel du dépôt** : page d'attente multilingue, API de contrôle de santé, base PostGIS et premier import manuel de parcelles Onwani avec provenance. Carte, fiches immobilières, authentification, médias et traitements IA arriveront avec les fonctionnalités suivantes.

Les commandes sont prévues pour **Windows et PowerShell**, depuis la racine du dépôt sauf indication contraire. Exécuter chaque commande séparément ; résoudre une erreur avant de poursuivre.

Les versions courantes et les exceptions de compatibilité sont documentées dans [TOOLCHAIN.md](TOOLCHAIN.md). Les anciennes études de stack restent des documents historiques ; les manifestes et ce guide décrivent les versions exécutées.

**Repère pour retrouver les fichiers :** les chemins du dépôt sont écrits depuis sa racine `C:\Users\Karim\Repositories\property-platform`. Par exemple, `apps/api/src/liwa/config/settings/base.py` désigne sur ton PC `C:\Users\Karim\Repositories\property-platform\apps\api\src\liwa\config\settings\base.py`. Les chemins commençant par `/app/` désignent au contraire des fichiers **dans le conteneur Linux**, pas dans l'explorateur Windows. Les noms courts dans une arborescence se lisent avec tous leurs dossiers parents.

## Mémo rapide : lancer, tester et tout arrêter

**Après avoir installé les outils et dépendances du guide**, ouvrir Docker Desktop, puis deux terminaux PowerShell. Copier les commandes une par une. Pour une première installation, suivre les étapes détaillées plus bas.

**Terminal A — lancer le site :**

```powershell
Set-Location 'C:\Users\Karim\Repositories\property-platform'
pnpm.cmd dev:web
```

Garder ce terminal ouvert. Ouvrir [le site local](http://localhost:3000) dans le navigateur.

**Terminal B — lancer la base et l'API, puis les vérifier :**

```powershell
Set-Location 'C:\Users\Karim\Repositories\property-platform'
docker compose -f infra/local/compose.yaml up -d --build
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
docker compose -f infra/local/compose.yaml ps
Invoke-RestMethod 'http://localhost:8000/api/v1/health/live'
Invoke-RestMethod 'http://localhost:8000/api/v1/health/ready'
```

Résultat attendu : site accessible, `api` en cours d'exécution, `db` en état `healthy`, réponses `ok` et `ready`. Tu peux aussi ouvrir [la documentation de l'API](http://localhost:8000/api/v1/docs). Il s'agit d'une vérification rapide du démarrage ; les contrôles de code et tests automatisés sont détaillés à l'étape 9. Si une commande échoue, résoudre l'erreur avant de continuer.

**Tout arrêter :** appuyer sur **Ctrl+C dans le terminal A**, puis exécuter dans le terminal B :

```powershell
docker compose -f infra/local/compose.yaml down
```

Le serveur web, l'API et la base sont alors arrêtés. **Les données de PostgreSQL sont conservées** : ne pas ajouter `-v` à `down`, car cette option supprime le volume de données. Fermer le navigateur ne suffit pas à arrêter les services. Docker Desktop peut rester ouvert ou être quitté après cet arrêt.

## Avant de commencer : où écrire les commandes ?

Ce document est un mode d'emploi. Les blocs intitulés `powershell` contiennent des commandes à **copier dans un terminal**, puis exécuter avec la touche **Entrée**. Ne pas les écrire dans un fichier du projet, dans la barre d'adresse du navigateur ou sur GitHub.

Pour ouvrir le bon terminal sur Windows :

1. Appuyer sur **Windows + R** : une petite fenêtre « Exécuter » apparaît.
2. Écrire `powershell` dans son champ, puis appuyer sur **Entrée**.
3. Une fenêtre avec une ligne de saisie s'ouvre. C'est le terminal PowerShell ; garder cette fenêtre ouverte.
4. Cliquer dans la fenêtre, coller une commande avec **Ctrl+V**, puis appuyer sur **Entrée**. Si Ctrl+V ne colle pas dans ce terminal, essayer un clic droit.
5. Attendre la fin de la commande avant de coller la suivante. Pour une installation, la fin correspond au retour de la ligne de saisie. Pour un serveur web, le terminal reste occupé : c'est normal.

Il n'est pas nécessaire d'ouvrir PowerShell en administrateur pour les commandes ordinaires du projet. Un terminal intégré à ton éditeur peut aussi convenir s'il utilise PowerShell, mais la procédure ci-dessus fonctionne sans éditeur.

Une ligne telle que `PS C:\Users\Karim>` est une **invite affichée par le terminal**, pas une commande à recopier. Le chemin indique le dossier dans lequel les commandes vont agir. « Depuis la racine du dépôt » signifie depuis le dossier `property-platform`, pas depuis son sous-dossier `docs`.

Les noms `.json`, `.yaml` et `.md` désignent des fichiers texte. Tu n'as pas besoin de les ouvrir ou de les modifier pour lancer le projet : les outils les lisent automatiquement.

## 1. Choisir le parcours

### Comprendre les outils avant les commandes

Une **dépendance**, ou bibliothèque, est du code déjà écrit par d'autres développeurs que le projet utilise. Par exemple, React aide à construire l'interface et Django aide à construire l'API. Installer les dépendances évite de devoir écrire ces outils nous-mêmes.

| Nom | Explication simple | Son rôle ici |
|---|---|---|
| PowerShell / terminal | Fenêtre dans laquelle tu donnes des commandes à Windows | Ouvrir un dossier, installer les bibliothèques et démarrer les programmes |
| Git | Outil qui conserve l'historique des fichiers et de leurs modifications | Récupérer et partager le code du dépôt |
| GitHub | Service qui héberge le dépôt Git | Stocker le code et son historique en ligne ; cela ne publie pas automatiquement le site |
| Node.js | Programme qui exécute du JavaScript sur l'ordinateur, en dehors du navigateur | Faire fonctionner les outils et le serveur web Next.js |
| npm | Gestionnaire de paquets fourni avec Node.js | Installer ou actualiser les outils npm et pnpm dans ce guide |
| pnpm | Autre gestionnaire de paquets JavaScript | Installer les bibliothèques de ce dépôt et lancer ses commandes nommées |
| Next.js | Framework web : ensemble d'outils pour construire et servir le site | Préparer les pages et démarrer le serveur sur le port 3000 |
| React | Bibliothèque utilisée par Next.js pour l'interface | Construire les composants visibles et leurs interactions |
| TypeScript | JavaScript avec des types pour détecter certaines erreurs avant l'exécution | Vérifier le code ; les types ne sont pas une base de données |
| Python / Django | Langage et framework utilisés pour le backend | Faire fonctionner l'API qui gérera les données et les règles métier |
| API | Programme qui reçoit des demandes et renvoie des réponses structurées | Répondre aux contrôles de santé aujourd'hui, puis aux demandes immobilières |
| PostgreSQL | Serveur de base de données | Conserver durablement les données de l'application |
| PostGIS | Extension de PostgreSQL pour les données géographiques | Stocker/interroger les futurs bâtiments, parcelles et coordonnées |
| Docker Desktop | Application qui fait tourner des environnements isolés sur Windows | Exécuter ici l'API et la base dans des conteneurs Linux |
| Docker Compose | Outil Docker qui démarre plusieurs services à partir d'un fichier de configuration | Lire infra/local/compose.yaml et gérer les services api et db ensemble |
| uv | Gestionnaire des outils et dépendances Python | Préparer l'environnement Python pour les tests natifs, à l'étape 9 |

**npm et pnpm servent à des tâches similaires.** Nous utilisons npm pour installer pnpm, puis pnpm pour gérer le projet. Les deux noms dans le guide ne désignent pas deux sites à lancer. Le suffixe `.cmd` est simplement le lanceur Windows de ces outils.

Un **serveur** est un programme qui reste en marche pour répondre aux demandes. Un **port** est le numéro qui distingue ses points d'accès sur une machine : 3000 pour le web, 8000 pour l'API, 5432 pour PostgreSQL. **localhost** signifie « cet ordinateur » : localhost:3000 ouvre le serveur web qui tourne sur ton PC.

Une **image Docker** est un environnement préparé avec les programmes nécessaires. Un **conteneur** est une instance en cours d'exécution de cette image. Un **volume** est un stockage conservé séparément : la base garde ainsi ses données lorsqu'on arrête ou remplace un conteneur.

### Ce que chaque étape change

| Étape | Ce qu'elle fait | Ce qui reste après |
|---|---|---|
| 1 | Choisir le parcours | Rien n'est installé ou démarré par la lecture du guide |
| 2 | Installer les outils sur Windows | Outils utilisables dans plusieurs projets ; leurs commandes de version ne font que vérifier |
| 3 | Ouvrir/récupérer le code puis télécharger les bibliothèques web | Fichiers du dépôt, node_modules et cache de paquets ; aucun site encore démarré |
| 4 | Démarrer Next.js | Serveur web tant que le terminal tourne, fichiers de travail générés sous apps/web/.next |
| 5 | Démarrer l'API et PostGIS, puis appliquer les migrations | Images/conteneurs Docker et volume PostgreSQL avec ses tables |
| 6 | Créer ton compte administrateur Django | Un compte dans la base locale, pas un compte utilisateur du futur site |
| 7 | Redémarrer, reconstruire ou arrêter | Les données du volume sont conservées lors de l'arrêt ordinaire |
| 8 | Préparer et essayer une version compilée du site | Un artefact local sous .next ; cela ne déploie rien sur Internet |
| 9 | Vérifier le code et éventuellement régénérer les contrats | Résultats de tests ; l'export/génération peut modifier les fichiers de contrat à revoir |
| 10 | Diagnostiquer les erreurs | Actions dépendant de l'erreur ; ce n'est pas une étape à exécuter systématiquement |
| 11 | Expliquer ce qui restera à faire avant publication | Aucun déploiement automatique |

À l'étape 4, si l'installation 3.3 et le démarrage ont réussi, **tu as préparé les bibliothèques puis lancé le serveur web**. L'API et PostgreSQL ne sont pas démarrés par pnpm dev:web. La page actuelle fonctionne sans eux ; elle n'appelle pas encore de catalogue immobilier.

| Objectif | Prérequis | Étapes |
|---|---|---|
| Voir et modifier le site | Git, Node.js 26.11.1, pnpm 12.10.1 | 2 à 4 |
| Lancer aussi l'API et PostGIS | Prérequis web + Docker Desktop avec Compose | 2 à 6 |
| Exécuter les outils Python et tests isolés sur Windows | uv 0.13.0 et Python 3.14.8 géré par uv | 9 |

Python et uv ne sont pas nécessaires sur Windows pour lancer l'API Docker : l'image contient leur environnement et les bibliothèques GIS. Le web actuel fonctionne seul, sans API ni compte Supabase, cartographique ou IA. Aucun service payant n'est requis pour ce lancement local.

## 2. Installer et vérifier les prérequis

### 2.1. Git et Node.js

**Ce que cette étape fait :** elle installe les programmes Git et Node.js sur Windows. Node.js apporte aussi npm. Cela ne télécharge pas encore les bibliothèques du site et ne crée aucune base. Les commandes --version ci-dessous affichent seulement la version de chaque programme.

Installer Git si nécessaire depuis [Git pour Windows](https://git-scm.com/download/win) et **Node.js 26.11.1** depuis [Node.js](https://nodejs.org/en/download). Le dépôt accepte Node.js `>=26.11.1 <27` ; la CI et les images web utilisent précisément 26.11.1.

Fermer puis rouvrir PowerShell après installation pour actualiser le PATH. Vérifier :

```powershell
git --version
node --version
npm.cmd --version
```

Git et npm doivent afficher leur version ; Node doit afficher **v26.11.1** (ou un correctif 26 plus récent autorisé). Une version 24/25 ou 26 antérieure à 26.11.1 ne satisfait pas les contraintes.

### 2.2. pnpm

**Ce que ces commandes font :** la première actualise l'outil npm ; la deuxième installe pnpm. `--global` signifie que l'outil est installé à un emplacement accessible depuis plusieurs projets, généralement dans ton profil Windows. Il ne s'agit pas de l'installation des dépendances immobilières de l'application. La troisième commande vérifie la version sans démarrer de serveur.

Installer la version fixée dans le dépôt :

```powershell
npm.cmd install --global npm@12.2.0
npm.cmd install --global pnpm@12.10.1 --allow-scripts=pnpm
pnpm.cmd --version
```

Résultat attendu : **12.10.1**. Les exemples utilisent `pnpm.cmd` pour éviter les blocages du wrapper PowerShell .ps1, sans changer la politique d'exécution Windows. Il s'agit du même outil que pnpm. Voir [son installation officielle](https://pnpm.io/installation).

npm 12 bloque par défaut les scripts d'installation non autorisés. pnpm 12 en a besoin pour préparer son exécutable Windows. L'option `--allow-scripts=pnpm` autorise uniquement les scripts de pnpm pour cette commande ; elle ne modifie pas la configuration globale de npm.

Si tu as déjà installé pnpm sans cette option et que `pnpm.cmd --version` répond qu'un chemin finissant par `node_modules\pnpm\pnpm` n'est pas reconnu, réparer l'installation **dans la même fenêtre PowerShell** :

```powershell
npm.cmd rebuild --global pnpm --allow-scripts=pnpm
pnpm.cmd --version
```

La première commande exécute les scripts manquants du paquet déjà installé et recrée ses lanceurs. Attendre sa réussite, puis vérifier que la seconde affiche **12.10.1**. Reprendre ensuite l'étape 3.3. Ne pas activer tous les scripts de tous les paquets pour résoudre ce problème. Voir [npm rebuild](https://docs.npmjs.com/cli/v12/commands/npm-rebuild).

### 2.3. Docker, pour l'API et PostGIS seulement

**Ce que cette étape fait :** elle installe et démarre le moteur Docker, qui pourra ensuite exécuter les conteneurs. Ouvrir Docker Desktop ne démarre pas automatiquement les services de ce dépôt : c'est la commande Compose de l'étape 5 qui le fait. Les commandes ci-dessous vérifient les outils et l'état du moteur.

Installer [Docker Desktop pour Windows](https://docs.docker.com/desktop/setup/install/windows-install/) et suivre ses prérequis Windows/WSL 2. Ouvrir Docker Desktop, utiliser les **conteneurs Linux** et attendre le démarrage du moteur.

```powershell
docker --version
docker compose version
docker info
```

Les deux premières commandes doivent afficher une version et docker info les informations du serveur sans erreur de connexion. Docker Desktop doit rester démarré pendant l'utilisation de l'API et de la base.

## 3. Ouvrir le dépôt et installer les dépendances

### 3.1. Sur la machine actuelle

**Ce que ces commandes font :** Set-Location choisit le dossier dans lequel travailler ; git status affiche l'état des fichiers par rapport à Git. Elles ne téléchargent rien et ne démarrent rien.

Le dépôt existe déjà :

```powershell
Set-Location 'C:\Users\Karim\Repositories\property-platform'
git status
```

Ne pas le cloner à nouveau dans ce dossier. Les commandes suivantes partent de cette racine, où se trouvent package.json, pnpm-workspace.yaml, apps et docs.

### 3.2. Sur une nouvelle machine seulement

**Ce que git clone fait :** il télécharge une copie des fichiers du dépôt et de son historique dans un nouveau dossier property-platform. Ce dossier contient du code et des configurations, pas toutes les bibliothèques nécessaires pour l'exécuter. L'installation de l'étape 3.3 reste nécessaire.

Depuis le dossier où tu souhaites ranger tes projets :

```powershell
git clone https://github.com/karimserkhane/property-platform.git
Set-Location property-platform
```

Le dépôt privé nécessite les droits du compte GitHub. Utiliser le parcours d'authentification Git proposé, sans mettre de jeton dans l'URL ou un fichier du dépôt.

### 3.3. Installer les paquets web

Si tu es bloqué ici, suivre exactement les sous-étapes ci-dessous. **Tout se fait dans la fenêtre PowerShell**, pas dans un fichier YAML.

#### 3.3.1. Ouvrir PowerShell

Utiliser **Windows + R**, écrire `powershell`, puis appuyer sur **Entrée**. Si tu as déjà une fenêtre PowerShell libre, réutilise-la. Ne pas coller les commandes dans un terminal où un serveur est déjà en cours d'exécution.

#### 3.3.2. Se placer dans le dossier du projet

Copier cette ligne dans PowerShell et appuyer sur **Entrée** :

```powershell
Set-Location 'C:\Users\Karim\Repositories\property-platform'
```

Cette commande sélectionne le dossier de travail. Elle ne lance pas encore le site. Tu devrais ensuite voir une invite ressemblant à `PS C:\Users\Karim\Repositories\property-platform>`.

Pour confirmer, exécuter :

```powershell
Get-Location
```

Le chemin affiché doit être **C:\Users\Karim\Repositories\property-platform**. Si Set-Location indique que le chemin n'existe pas, ouvrir l'Explorateur Windows avec **Windows + E**, retrouver le dossier réellement cloné et utiliser son chemin à la place. Sur la machine actuelle, le chemin ci-dessus est celui du dépôt.

#### 3.3.3. Vérifier les fichiers et les outils

Exécuter les quatre commandes suivantes **une par une**, en appuyant sur Entrée après chacune :

```powershell
Test-Path -LiteralPath '.\package.json'
Test-Path -LiteralPath '.\pnpm-workspace.yaml'
node --version
pnpm.cmd --version
```

Résultats attendus : **True**, **True**, **v26.11.1** (ou correctif 26 ultérieur autorisé), puis **12.10.1**. Si un Test-Path répond False, vérifier le dossier sélectionné. Si node ou pnpm.cmd n'est pas reconnu, reprendre l'installation de l'étape 2, puis fermer et rouvrir PowerShell ; revenir ensuite au dossier du projet avec Set-Location.

#### 3.3.4. Lancer l'installation

Copier **cette commande seulement** dans PowerShell, puis appuyer sur **Entrée** :

```powershell
pnpm.cmd install --frozen-lockfile
```

Laisser PowerShell ouvert et attendre : la première installation télécharge les bibliothèques nécessaires au site. Tu peux voir des lignes de progression, des nombres de paquets ou un message indiquant qu'ils sont déjà à jour. Si les dépendances sont déjà installées, la commande peut finir rapidement.

L'installation est terminée quand le terminal rend la main et affiche de nouveau son invite, généralement après un message « Done ». Il ne faut pas poursuivre si un message indique une erreur. Cette étape **n'ouvre pas de page web** ; c'est attendu. Le site sera lancé à l'étape 4.

Cette commande lit les fichiers du dépôt et installe les dépendances JavaScript à partir de pnpm-lock.yaml, sans modifier ce verrouillage. Elle crée ou actualise des dossiers locaux tels que node_modules et .pnpm-store, ignorés par Git.

**Ce qui se passe concrètement :** pnpm identifie les applications du dépôt, lit leurs package.json et le verrouillage, télécharge les paquets manquants puis les rend accessibles au code. Next.js et React font partie de ces bibliothèques. Le cache permet de réutiliser les téléchargements, et node_modules contient les paquets et liens nécessaires à leur utilisation. Ces fichiers ne sont pas des biens immobiliers et il n'est pas nécessaire de les éditer. Cette commande n'installe pas PostgreSQL et ne lance pas Docker Compose.

#### 3.3.5. Quel fichier YAML est concerné ?

Voici les fichiers à distinguer ; **aucun n'est à modifier pour cette installation** :

| Fichier | Où il se trouve | À quoi il sert |
|---|---|---|
| [package.json](../../package.json) | Directement dans property-platform | Déclare les outils/dépendances de racine et les commandes comme dev:web |
| [pnpm-workspace.yaml](../../pnpm-workspace.yaml) | Directement dans property-platform | Indique à pnpm les applications/packages appartenant au même dépôt et sa configuration |
| [pnpm-lock.yaml](../../pnpm-lock.yaml) | Directement dans property-platform | Fixe les versions précises des dépendances à installer |
| [compose.yaml](../../infra/local/compose.yaml) | Dans property-platform/infra/local | Configure Docker pour l'API et PostGIS ; il intervient à l'étape 5, pas pour lancer le site seul |

Tu peux voir ces fichiers dans l'Explorateur Windows : **Windows + E**, cliquer sur la barre d'adresse en haut, coller `C:\Users\Karim\Repositories\property-platform`, puis appuyer sur Entrée. Cette manipulation affiche les fichiers ; elle ne remplace pas l'exécution des commandes dans PowerShell.

#### 3.3.6. Si l'installation échoue

- **pnpm.cmd non reconnu** : reprendre l'étape 2.2, rouvrir PowerShell et refaire Set-Location.
- **Erreur de version/engine** : vérifier node --version et pnpm.cmd --version avec les valeurs ci-dessus.
- **package.json introuvable / aucun projet trouvé** : refaire Set-Location et les deux Test-Path ; ne pas lancer l'installation depuis docs ou Downloads.
- **Erreur de certificat** : consulter l'étape 10 ; ne pas désactiver la vérification TLS.
- **Autre erreur** : conserver le texte complet affiché et le partager pour diagnostiquer le problème avant de passer à l'étape suivante.

Les scripts d'installation de Parcel/SWC sont désactivés explicitement dans pnpm-workspace.yaml ; leurs binaires de plateforme sont fournis par les dépendances optionnelles. **Ne pas ajouter --no-optional.** node_modules et .pnpm-store sont locaux et ignorés par Git.

## 4. Démarrer le site — terminal A

**Ce que cette étape fait :** elle lance un programme qui reste en marche pour servir le site depuis ton ordinateur. « Terminal A » est seulement le nom donné dans ce guide à ta première fenêtre PowerShell ; ce n'est ni un fichier ni un outil à installer.

Après la réussite de l'installation, rester dans **la même fenêtre PowerShell**, au dossier property-platform. Copier cette commande et appuyer sur **Entrée** :

```powershell
pnpm.cmd dev:web
```

### Ce qui se passe derrière cette commande

1. pnpm lit la commande nommée dev:web dans le package.json de racine.
2. Cette commande sélectionne l'application web, située dans apps/web, puis lance sa commande dev.
3. La commande dev lance **Next.js**, exécuté grâce à Node.js. Next prépare les pages à partir du code ; JavaScript et CSS nécessaires à l'interface sont ensuite envoyés au navigateur.
4. Next démarre son serveur de développement, généralement sur le port 3000, et crée des fichiers de travail sous apps/web/.next.
5. Il surveille le code : lorsque tu enregistres un changement, il met à jour les pages concernées. C'est pourquoi le terminal reste occupé.

Tu n'as donc pas « lancé npm, pnpm et Docker en même temps » : **pnpm a simplement lancé le serveur Next.js**. Les bibliothèques installées à l'étape 3.3 sont utilisées par ce serveur. Cette commande ne crée pas la base, ne collecte pas d'annonces et ne génère aucun média IA.

Garder le terminal ouvert : il fait tourner le site. Attendre que Next.js indique qu'il est prêt (« Ready »), puis ouvrir ton navigateur habituel, par exemple Edge ou Chrome. Cliquer dans sa barre d'adresse en haut, écrire **http://localhost:3000**, puis appuyer sur **Entrée**. Tu peux aussi cliquer sur [le site local](http://localhost:3000).

L'adresse se saisit dans le **navigateur**, contrairement aux commandes précédentes qui se saisissent dans **PowerShell**. Il n'y a pas de fichier HTML à double-cliquer pour démarrer cette application.

Résultat attendu :

- La racine redirige vers /en, même si le navigateur préfère une autre langue.
- La page affiche Liwa Atlas, Al Reem Island et le texte d'attente en anglais.
- Le sélecteur propose les quinze langues configurées.
- [L'arabe](http://localhost:3000/ar), l'ourdou et le persan utilisent le sens de lecture de droite à gauche.

Si le port 3000 est occupé, Next peut en choisir un autre : utiliser l'adresse affichée dans le terminal.

Modifier par exemple apps/web/messages/en.json ou apps/web/src/app/[locale]/page.tsx puis enregistrer : le serveur de développement recharge les changements. Les textes visibles doivent rester dans les dictionnaires. Voir [la politique multilingue](INTERNATIONALIZATION.md).

**Ctrl+C** dans ce terminal arrête le site. Tant que le serveur tourne, utiliser un autre terminal pour les commandes suivantes.

**Ce qui est conservé après Ctrl+C :** le code, les bibliothèques installées et les fichiers générés sur disque. **Ce qui s'arrête :** le serveur web lancé dans cette fenêtre. Tu peux le relancer avec la même commande sans tout réinstaller. Fermer seulement l'onglet du navigateur n'arrête pas le serveur.

Ce lancement est du développement local, pas une publication publique du site. Si Next affiche aussi une adresse « Network », elle correspond à un accès possible depuis ton réseau local selon la configuration ; elle ne signifie pas que le site a été déployé sur Internet.

## 5. Démarrer PostGIS et l'API — terminal B

**Ce que cette étape fait :** elle lance les deux autres services, indépendamment du serveur web : l'API Django et la base PostgreSQL/PostGIS. « Terminal B » est simplement une deuxième fenêtre PowerShell, utile parce que le terminal A reste occupé par Next.js.

Ouvrir un deuxième PowerShell pendant que le site tourne :

```powershell
Set-Location 'C:\Users\Karim\Repositories\property-platform'
docker compose -f infra/local/compose.yaml config --quiet
docker compose -f infra/local/compose.yaml up -d --build
docker compose -f infra/local/compose.yaml ps
```

La première commande valide le Compose. La deuxième télécharge PostgreSQL 18/PostGIS 3.6, construit l'image Python et démarre db et api en arrière-plan. Le premier lancement est plus long que les suivants.

### Lire cette commande sans jargon

Dans `docker compose -f infra/local/compose.yaml up -d --build` :

| Élément | Signification |
|---|---|
| docker compose | Utiliser Docker pour gérer ensemble les services du projet |
| -f infra/local/compose.yaml | Lire ce fichier précis, qui décrit les services db et api, leurs ports et leur stockage |
| up | Créer si nécessaire, puis démarrer les services |
| -d | Les laisser tourner en arrière-plan ; PowerShell rend la main |
| --build | Construire/reconstruire l'image de l'API à partir de son Dockerfile et du code du dépôt |

Le service **db** utilise une image PostGIS déjà préparée et initialise une base lors de la première utilisation du volume vide. Le service **api** construit son image à partir de apps/api/Dockerfile : Python, Django et les bibliothèques GIS sont installés **dans l'environnement Docker**, puis le code API y est copié. Cela n'installe pas Python directement dans Windows.

Compose crée aussi un réseau pour que l'API joigne la base par le nom db. Les ports publiés permettent de joindre l'API sur localhost:8000 et PostgreSQL sur localhost:5432. La commande ps affiche les services ; logs affiche leurs messages. Ces deux commandes ne créent pas de nouvelles données.

Le web de l'étape 4 reste exécuté directement par Node.js sur Windows : **le Compose actuel ne démarre pas le web**. La future interface appellera l'API pour les fonctionnalités métier ; la page d'attente actuelle fonctionne encore indépendamment.

Dans ps, attendre que **db soit healthy** et que **api soit en cours d'exécution**. En cas d'arrêt de l'API ou de base non saine, lire les journaux :

```powershell
docker compose -f infra/local/compose.yaml logs --tail 100 db api
```

### Changement depuis l'ancien socle PostgreSQL 17

Le Compose utilise désormais le volume `liwa-local_postgres18-data`, monté sous `/var/lib/postgresql`, conformément à l'image PostgreSQL 18. L'ancien volume `liwa-local_postgres-data` est conservé mais **n'est pas migré automatiquement**. Le premier lancement en PostgreSQL 18 initialise une nouvelle base : recréer les migrations et le superutilisateur ci-dessous. Si l'ancien volume contient des données à conserver, préparer un export/restauration ou une migration validée avant de basculer les usages. Ne pas monter directement son répertoire PostgreSQL 17 dans PostgreSQL 18 et ne pas le supprimer. Aucun transfert ou effacement de base n'est exécuté par la mise à jour du dépôt.

### D'où viennent les noms des services, images et conteneurs ?

Compose lit [infra/local/compose.yaml](../../infra/local/compose.yaml) et démarre deux **conteneurs** à partir de deux **images**. Une image est le modèle préparé ; un conteneur est une instance exécutée à partir de ce modèle ; un service est la définition de ce que Compose doit lancer.

Voici un **extrait simplifié à lire**, pas une commande à exécuter ni un remplacement du fichier complet :

```yaml
name: liwa-local

services:
  db:
    image: postgis/postgis:18-3.6

  api:
    build:
      context: ../..
      dockerfile: apps/api/Dockerfile
```

| Élément | Base de données | Backend Django |
|---|---|---|
| Service défini sous `services:` | `db` | `api` |
| Image utilisée | `postgis/postgis:18-3.6`, téléchargée si nécessaire | `liwa-local-api`, construite localement depuis notre Dockerfile |
| Conteneur créé | `liwa-local-db-1` | `liwa-local-api-1` |

`name: liwa-local` fixe le nom du projet Compose. Par défaut, le nom du conteneur suit **projet + service + numéro** : `liwa-local` + `api` + `1` donne `liwa-local-api-1`. Le numéro distingue les instances d'un service. Pour `api`, nous n'avons pas déclaré de champ `image:` : Compose attribue à l'image construite le nom `liwa-local-api`. Ces noms correspondent aux commandes de ce guide, sans option ni variable qui remplace le nom du projet.

Dans les commandes Compose, on utilise le **service** : `exec api`, `logs api` ou `logs db`. Il n'est donc pas nécessaire d'écrire le nom complet du conteneur.

### Pourquoi `docker compose … ps` et `docker ps` affichent-ils des tableaux différents ?

Ces deux commandes consultent l'état des conteneurs ; elles ne les démarrent pas et ne modifient pas la base.

| Commande | Ce qu'elle affiche |
|---|---|
| `docker compose -f infra/local/compose.yaml ps` | Les conteneurs du projet décrit par ce YAML, avec leur service `api` ou `db` |
| `docker ps` | Tous les conteneurs actuellement démarrés sur le Docker auquel ton terminal est connecté, avec notamment leur identifiant |

Si seuls nos deux conteneurs tournent, les deux tableaux montrent les mêmes instances, avec des colonnes différentes. `IMAGE` indique le modèle utilisé ; `NAME` ou `NAMES` indique le conteneur ; `SERVICE` indique le service Compose ; `CONTAINER ID` est l'identifiant technique du conteneur. `Up` indique qu'il tourne, et `healthy` que son contrôle de santé réussit. Les durées changent entre deux commandes exécutées à des moments différents.

**Voir `api` en cours d'exécution et `db` en état `healthy` ne prouve pas que les tables Django existent déjà.** C'est le rôle de l'étape 5.1.

### 5.1. Créer les tables Django

Une **migration** décrit une évolution de la structure de la base : créer une table, ajouter une colonne ou une contrainte. Le premier migrate crée les tables Django de comptes, permissions et sessions, ainsi que nos premières tables de parcelles, acquisitions et audit. Cette commande crée leur structure ; elle ne collecte aucune donnée immobilière.

**Pourquoi cette étape après le démarrage Docker ?** PostgreSQL a initialisé une base disponible, mais il ne connaît pas les tables dont Django a besoin. Démarrer l'API et créer ces tables sont deux opérations distinctes : Django doit envoyer les instructions de création à PostgreSQL.

Lorsque les services tournent :

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
docker compose -f infra/local/compose.yaml exec api python manage.py check
```

Résultat attendu : migrations appliquées ou aucune migration restante, puis contrôle Django sans erreur. Le démarrage de l'API **n'applique pas automatiquement les migrations**.

Ici, `exec api` signifie « exécuter la suite de la commande dans le conteneur api déjà démarré ». `python manage.py` lance un outil Django du projet. `migrate --noinput` applique les migrations sans questions interactives ; `check` examine la configuration et ne crée pas de tables. Appliquer des migrations déjà appliquées ne les rejoue pas.

Le chemin de cette opération est : **PowerShell → Django dans le conteneur `api` → création des tables dans PostgreSQL, dans le conteneur `db`**. La commande ne crée pas de nouveau conteneur. Django enregistre aussi les migrations appliquées dans la base afin de savoir lesquelles restent à exécuter. Les tables et ce suivi sont conservés dans le volume persistant de PostgreSQL après un arrêt ordinaire de Docker.

#### Où sont les modèles et les fichiers de migration ?

Un **modèle** est une classe Python décrivant les données de l'application, par exemple un bâtiment et ses champs. Une **migration** est un fichier Python décrivant une évolution de la base correspondant à ces modèles. Les fichiers Python ne contiennent pas les lignes de données : celles-ci sont enregistrées dans PostgreSQL.

**Une partie des modèles et migrations est fournie par Django lui-même.** Ces fichiers sont installés dans les dépendances Python du conteneur API, pas dans nos dossiers de code métier. Nos modèles de parcelles et de provenance, décrits ensuite, sont dans le dépôt. Les applications concernées sont déclarées dans `INSTALLED_APPS`, dans [apps/api/src/liwa/config/settings/base.py](../../apps/api/src/liwa/config/settings/base.py).

| Fonction Django | Modèles fournis avec Django | Migrations fournies avec Django |
|---|---|---|
| Comptes et permissions | `/app/.venv/lib/python3.14/site-packages/django/contrib/auth/models.py` | `/app/.venv/lib/python3.14/site-packages/django/contrib/auth/migrations/` |
| Types de contenus utilisés notamment par les permissions | `/app/.venv/lib/python3.14/site-packages/django/contrib/contenttypes/models.py` | `/app/.venv/lib/python3.14/site-packages/django/contrib/contenttypes/migrations/` |
| Sessions stockées en base | `/app/.venv/lib/python3.14/site-packages/django/contrib/sessions/models.py` | `/app/.venv/lib/python3.14/site-packages/django/contrib/sessions/migrations/` |
| Journal de l'administration | `/app/.venv/lib/python3.14/site-packages/django/contrib/admin/models.py` | `/app/.venv/lib/python3.14/site-packages/django/contrib/admin/migrations/` |

Le tableau donne les chemins complets **dans le conteneur API actuel**. Si tu utilises le parcours Python natif sur Windows, le préfixe `/app/.venv/lib/python3.14/site-packages/` est remplacé par `apps/api/.venv/Lib/site-packages/` depuis la racine du dépôt. Ce sont les fichiers de la bibliothèque : **on ne les modifie pas pour développer notre produit**.

Pour afficher le chemin réel d'un fichier de migration Django dans ton conteneur, depuis PowerShell à la racine du dépôt :

```powershell
docker compose -f infra/local/compose.yaml exec api python -c "import importlib; print(importlib.import_module('django.contrib.auth.migrations.0001_initial').__file__)"
```

Pour voir les migrations connues et savoir lesquelles ont été appliquées :

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py showmigrations
```

`[X]` signifie « déjà appliquée » et `[ ]` « pas encore appliquée ». Ces deux commandes consultent des informations ; elles ne créent pas de tables. Django conserve le suivi des applications dans la table PostgreSQL `django_migrations`.

**Nos modèles et migrations sont dans le module propriétaire.** Le premier sous-ensemble de parcelles existe maintenant dans le catalogue :

```text
apps/api/src/liwa/modules/catalog/
├── apps.py                     Existe : déclaration du module Django
├── README.md                   Existe : responsabilités du catalogue
├── models.py                   Existe : modèle Parcel, géométrie et champs typés
├── services.py                 Existe : mutations du catalogue et conversion des géométries
└── migrations/                 Existe : historique de leur structure en base
    ├── __init__.py
    └── 0001_initial.py         Existe : première création de la table des parcelles
```

Pour retrouver ces fichiers sans lire l'arborescence : [apps/api/src/liwa/modules/catalog/models.py](../../apps/api/src/liwa/modules/catalog/models.py), dossier `apps/api/src/liwa/modules/catalog/migrations/`, première migration `apps/api/src/liwa/modules/catalog/migrations/0001_initial.py`. Les modèles de provenance sont dans [apps/api/src/liwa/modules/evidence/models.py](../../apps/api/src/liwa/modules/evidence/models.py), avec leurs migrations dans `apps/api/src/liwa/modules/evidence/migrations/`.

On pourra répartir les modèles dans un paquet `apps/api/src/liwa/modules/catalog/models/` si leur taille le justifie. Les modules `apps/api/src/liwa/modules/evidence/` et `apps/api/src/liwa/modules/publication/` auront leurs propres modèles et migrations pour les données qu'ils possèdent ; tout ne sera pas regroupé dans le catalogue.

Le cycle de développement est **modifier les modèles → générer les migrations avec `makemigrations` → relire et conserver ces fichiers dans Git → appliquer avec `migrate`**. `makemigrations` prépare des fichiers ; `migrate` modifie la base. **À cette étape du démarrage, utilise seulement `migrate` : les migrations du dépôt sont déjà générées.** Les bâtiments et logements restent à développer.

Le Compose actuel copie le code dans l'image sans monter les fichiers Windows. Une migration générée uniquement dans le conteneur n'apparaît donc pas automatiquement dans ton dépôt et peut être perdue lors de sa recréation. Lors du développement des premiers modèles, il faudra générer les fichiers dans l'environnement local configuré ou les récupérer explicitement dans le dépôt avant de reconstruire l'image. Voir aussi [la structure des modules](REPOSITORY.md).

### 5.2. Vérifier les endpoints

Un **endpoint** est une adresse précise de l'API à laquelle envoyer une demande. Invoke-RestMethod envoie ici une requête HTTP depuis PowerShell et affiche la réponse. Ces requêtes de santé ne créent pas d'utilisateur ou de bien immobilier.

```powershell
Invoke-RestMethod 'http://localhost:8000/api/v1/health/live'
Invoke-RestMethod 'http://localhost:8000/api/v1/health/ready'
```

Le champ status doit valoir **ok** pour live et **ready** pour ready. live vérifie que l'API répond ; ready vérifie une connexion fonctionnelle avec PostGIS. ready ne remplace pas les migrations ni les futurs tests métier.

Ouvrir [la documentation interactive locale](http://localhost:8000/api/v1/docs) pour voir les endpoints. Les endpoints immobiliers ne sont pas encore implémentés.

Les ports sont limités à la machine locale : web 3000, API 8000, base 5432. Compose fournit déjà ses variables et identifiants de développement : **aucun .env n'est requis pour ce parcours**. apps/api/.env.example illustre une exécution Python native ; Django ne charge pas automatiquement une copie .env dans la configuration actuelle.

### Premier import manuel des parcelles Onwani

**Facultatif pour lancer le site, nécessaire pour alimenter le catalogue de parcelles.** Cette commande interroge directement DMT/Onwani ; elle n'utilise pas le HTML fourni. Elle reste manuelle, sans tâche planifiée.

Après avoir récupéré la branche contenant cet import, depuis la racine du dépôt dans le terminal B :

```powershell
docker compose -f infra/local/compose.yaml up -d --build api
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
docker compose -f infra/local/compose.yaml exec api python manage.py import_onwani --actor Karim
```

`--actor Karim` identifie l'opérateur dans l'audit ; ce texte ne constitue pas une authentification. La commande de maintenance est réservée aux personnes ayant accès à l'environnement serveur. La collecte peut prendre quelques minutes. Le résultat affiche un identifiant d'acquisition et les compteurs `created`, `updated`, `unchanged`, `observed` et `quarantined`.

- `created` : nouvelles parcelles du catalogue ; `updated` : versions typées ou géométries changées ; `unchanged` : parcelles déjà présentes et identiques.
- `observed` : nombre d'enregistrements collectés ; `quarantined` : géométries invalides conservées pour examen, sans correction automatique ni remplacement d'une ancienne géométrie valide.
- Un statut `quarantined` signale un lot à examiner, pas une carte entièrement validée. Une erreur de réseau, de territoire, de schéma ou de couverture laisse le catalogue précédent intact ; les captures déjà reçues et le statut de l'acquisition restent enregistrés.

Tu peux relancer l'import : il crée une nouvelle acquisition, sans dupliquer les parcelles qui gardent le même identifiant de source. Les observations et captures successives sont conservées. Aucun enregistrement absent n'est supprimé automatiquement. Cela ne publie pas encore les parcelles sur le site, qui reste une page d'attente.

Dans l'outil de base de données, les tables sont sous le schéma `public` :

| Table | Ce qu'elle contient |
|---|---|
| `catalog_parcel` | Parcelles, géométries PostGIS, identité interne et révision |
| `evidence_source` | Source officielle utilisée |
| `evidence_ingestionrun` | Historique des imports, opérateur, statut et compteurs |
| `evidence_capture` | Réponses JSON exactes, URL, horaires, empreinte SHA-256 et en-têtes disponibles |
| `evidence_parcelobservation` | Attributs originaux, version de mapping et référence de capture par parcelle |
| `evidence_auditevent` | Créations et changements du catalogue, auteur et justification |
| `evidence_quarantinedobservation` | Enregistrements dont la géométrie doit être examinée |

Pour vérifier les effectifs depuis le terminal, sans modifier les données :

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py shell -c "from liwa.modules.catalog.models import Parcel; from liwa.modules.evidence.models import IngestionRun; print('Parcelles:', Parcel.objects.count()); print('Acquisitions:', IngestionRun.objects.count())"
```

Les dates de publication inconnues restent nulles ; les dates de réception, permis et mise à jour fournies par Onwani restent préservées dans leurs attributs originaux. Voir [DATA_PROVENANCE.md](DATA_PROVENANCE.md) pour les limites, la portée des identifiants et les responsabilités de chaque module. Utiliser les services métier et cette commande pour modifier le catalogue, pas des modifications manuelles de tables dans l'outil SQL.

## 6. Créer un compte d'administration — facultatif

**Ce que cette étape fait :** elle ajoute dans PostgreSQL un compte autorisé à utiliser l'administration Django. Ce compte reste dans le volume de base après un arrêt ordinaire. Il ne crée pas un compte GitHub, un compte Windows ou le système de connexion du futur site public.

Après les migrations :

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py createsuperuser
```

Répondre aux questions. Le mot de passe peut ne pas apparaître pendant la saisie : c'est normal. Il n'est pas enregistré dans Git.

Ouvrir [l'administration Django](http://localhost:8000/admin/) et se connecter. Elle propose actuellement les écrans Django de base ; les modules immobiliers n'ont pas encore leurs modèles et écrans métier. Admin et docs interactives sont disponibles en configuration locale DEBUG ; ce parcours n'est pas prêt à publier.

## 7. Routine quotidienne et arrêt

### Au prochain lancement

**Ce qui se passe :** Compose redémarre ou réutilise les conteneurs et retrouve le même volume de base. pnpm dev:web relance le serveur web à partir du code déjà présent. Installer, démarrer et arrêter sont trois opérations différentes ; une installation n'est pas à refaire chaque matin.

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

**Pourquoi reconstruire :** l'image API est une copie préparée du code à un instant donné. Changer le fichier Python sur Windows ne change pas cette copie. Le build crée une image actualisée et Compose peut remplacer le conteneur API en utilisant toujours le même volume de base.

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

**Ce que cette étape fait :** elle transforme le code du web en fichiers préparés pour une exécution sans rechargement de développement. Ce travail s'appelle un build, ou compilation. Ce n'est pas encore un déploiement : les fichiers restent sur ton ordinateur.

Arrêter le serveur de développement pour libérer le port 3000. Depuis la racine :

```powershell
pnpm.cmd build
pnpm.cmd --filter @liwa/web start
```

Le build utilise **Webpack** : la copie standalone avec Turbopack a échoué dans l'environnement Windows vérifié. Le développement conserve le compilateur par défaut de Next.js. Le script de pré-démarrage prépare les fichiers CSS/JS et les éventuels fichiers public du standalone.

Ouvrir [le site compilé](http://localhost:3000/en). Ce serveur ne recharge pas les modifications : arrêter, reconstruire et redémarrer pour les prendre en compte.

`build` prépare les fichiers ; `start` démarre le serveur qui les utilise. À l'étape 4, `dev:web` prépare les pages au fil du développement et surveille les modifications. Ne pas lancer dev:web et start simultanément sur le même port.

Pour vérifier automatiquement l'artefact, arrêter ce serveur puis exécuter :

```powershell
node scripts/prepare-web-runtime.mjs
pnpm.cmd smoke:web
```

Le contrôle attend un build existant. Il démarre un serveur temporaire sur **3101**, vérifie les quinze routes, lang/dir, traductions, sélecteur, CSS, défaut anglais et route inexistante, puis arrête son serveur. Libérer le port 3101 avant de le lancer.

## 9. Vérifier le code avant de le partager

**Ce que cette étape fait :** elle cherche des erreurs avant de partager ou publier le code. Les vérifications ne remplacent pas un lancement du site et ne téléchargent pas de données immobilières. Les tests isolés utilisent un environnement de test, pas le volume PostgreSQL de développement.

### 9.1. Web et documentation

Avec les dépendances installées, depuis la racine :

```powershell
pnpm.cmd lint
pnpm.cmd typecheck
pnpm.cmd test:web
pnpm.cmd docs:check
pnpm.cmd contracts:check
```

Les commandes doivent terminer sans erreur. Le typage utilise le compilateur natif TypeScript 7.0.2 via un alias explicite. Next.js utilise le paquet de compatibilité TypeScript 6.0.2 (API embarquée 6.0.3) ; le générateur OpenAPI conserve l'API TypeScript 5.9.3 requise par ses peers. Voir [les versions et exceptions](TOOLCHAIN.md).

Elles contrôlent respectivement qualité/style, types, traductions, liens Markdown locaux et cohérence des types générés avec OpenAPI. Pour vérifier aussi le serveur compilé, suivre l'étape 8.

### 9.2. Python sur Windows — installation facultative

Cette option sert à travailler sur les outils Python directement depuis Windows. Elle est distincte du parcours Docker : uv télécharge ici l'interpréteur Python et prépare un environnement local au projet. Une **.venv** contient les bibliothèques Python isolées pour ce projet ; elle évite de les mélanger avec celles d'autres applications.

Pour les outils de qualité, l'export OpenAPI et les tests HTTP isolés, installer [uv 0.13.0 avec son installateur officiel](https://docs.astral.sh/uv/getting-started/installation/) :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/0.13.0/install.ps1 | iex"
```

Cette commande exécute l'installateur officiel dans un processus distinct. Fermer puis rouvrir PowerShell, revenir à la racine et lancer :

```powershell
uv --version
uv python install 3.14.8
uv sync --project apps/api --frozen --python 3.14.8
```

Résultat attendu : uv **0.13.0** et un environnement Python **3.14.8** sous apps/api/.venv avec les dépendances de apps/api/uv.lock. uv run --project apps/api sélectionne cet environnement ; aucune activation manuelle n'est requise.

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

Un **contrat API** décrit les adresses disponibles et les formes des demandes/réponses. L'export OpenAPI produit cette description depuis le code Python ; contracts:generate en déduit les types TypeScript pour le web. Cela permet aux deux applications de s'accorder sur les données échangées, sans partager directement leurs tables de base.

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
| pnpm.cmd cite un chemin node_modules\pnpm\pnpm non reconnu après installation npm | Réparer les scripts bloqués avec npm.cmd rebuild --global pnpm --allow-scripts=pnpm, puis pnpm.cmd --version ; voir l'étape 2.2 |
| Erreur de version/engine | Vérifier Node 26 et pnpm 12.10.1 ; ne pas contourner engineStrict |
| ERR_PNPM_UNEXPECTED_STORE | Vérifier storeDir dans le dépôt ; réinstaller avec pnpm.cmd install --force --frozen-lockfile si les paquets locaux provenaient d'un autre store |
| Docker ne joint pas son moteur | Ouvrir Docker Desktop, attendre son démarrage et vérifier les conteneurs Linux avec docker info |
| Port 8000 ou 5432 occupé | Identifier le programme avec Get-NetTCPConnection -LocalPort 8000,5432 -ErrorAction SilentlyContinue ; arrêter seulement un service reconnu ou adapter les ports locaux dans Compose |
| ready répond 503 | Lire les logs db/api, vérifier db healthy et la connexion PostGIS ; ne pas supprimer le volume pour tenter une réparation |
| API inchangée après édition Python | Reconstruire l'image API comme à l'étape 7 |
| Admin refuse la connexion | Vérifier migrations, création du superutilisateur et configuration locale |
| CSS/JS absent en standalone | Reconstruire puis lancer node scripts/prepare-web-runtime.mjs, ou utiliser start qui fait cette préparation |
| Erreur certificat TLS à l'installation | Vérifier les certificats du système/réseau ; Node 26 permet $env:NODE_OPTIONS='--use-system-ca', uv accepte --system-certs sur sa commande réseau ; ne pas désactiver la vérification TLS |

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
