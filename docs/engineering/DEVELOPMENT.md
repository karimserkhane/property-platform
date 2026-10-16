# Lancer et développer Property Platform, étape par étape

**Accès téléphone à distance :** le [guide de prévisualisation privée](REMOTE_PREVIEW.md) explique le connecteur Tailscale Docker facultatif, la connexion sur téléphone, le lien HTTPS de la carte et l'arrêt de cet accès. Le PC et Docker doivent rester allumés. Ce parcours ne publie pas le site sur Internet et ne remplace pas un déploiement de production.

**Stockage retenu pour le moment : local, sans R2/S3.** Les photos, PDF, vidéos et modèles acquis utilisent le volume persistant dédié `property-platform-local_media-data`, partagé entre Django et Prefect sous `/media`. Aucune clé cloud n'est nécessaire. Voir [où trouver cet espace et préparer un transfert ultérieur](MEDIA_STORAGE.md#mode-actuel--stockage-local-dédié). Les commandes locales ordinaires suffisent ; ne pas ajouter le fichier `compose.storage.s3.yaml` tant que le cloud n'est pas souhaité.

**Option ultérieure — Cloudflare R2 :** le [guide de raccordement](MEDIA_STORAGE.md#51-ce-que-tu-dois-faire-dans-cloudflare) reste disponible. Le fichier local `C:\Users\Karim\Repositories\property-platform\infra\local\.env` est un emplacement préparé pour les futurs paramètres, ignoré par Git ; sa présence n'active pas le cloud. Aucun domaine CDN ni compte Cloudflare n'est requis pour continuer le développement local.

**Fiches projets et vidéos — 16 octobre 2026 :** le [guide PROJECTS.md](PROJECTS.md) explique les nouvelles tables, les imports Prefect de 57 projets/programmes examinés chez 10 promoteurs, l’annuaire Reem/Saadiyat, la découverte de nouveaux liens, les PDF et vidéos, et l’ajout de fichiers autorisés. Les candidats non examinés ne créent pas de bien automatiquement. Reconstruire API et ingestion, appliquer les migrations, lancer les deux imports de projets, puis reconstruire le web ; aucune suppression de volume. Les anciennes sections de lancement et de collecte cartographique restent applicables.

**Carte d’ensemble — 14 octobre 2026 :** [ouvrir l’exploration](http://localhost:3102/fr/explore) affiche par défaut **Toute la zone : Reem et Saadiyat réunies**, avec leurs biens, parcelles, bâtiments, lieux et rues sur une seule carte. Le sélecteur permet aussi d’afficher chaque île séparément. Les limites des autres districts d’Abu Dhabi restent en base pour plus tard, mais ne sont plus affichées sur cette carte. Le [guide Abu Dhabi](ABU_DHABI.md#carte-densemble-et-districts-officiels) explique cette composition. Aucun nouvel import ou migration n’est nécessaire sur ce poste ; les images API/web doivent utiliser le code actualisé.

**Clic et usages — 14 octobre 2026 :** les grands périmètres comme RT4 sont sélectionnables en dernier recours, derrière les biens, lieux, rues et petites parcelles. Les usages déjà ingérés sont visibles en tête de fiche : école, mosquée, commerce, transport, infrastructure, etc., avec le libellé original. Le [guide des fiches](PROPERTY_EXPLORATION.md) explique les champs SQL et la classification. Cette évolution nécessite les nouvelles images API/web, mais aucune migration ni réimportation des données sur ce poste.

Ce guide décrit le **socle actuel du dépôt** : accueil multilingue, carte locale des parcelles, rues, secteurs, empreintes de bâtiments et lieux, premières fiches immobilières, sources consultables, deux aperçus satellite, API, base PostGIS et imports avec provenance. Les imports manuels restent disponibles ; leur orchestration Prefect est désormais implémentée dans une application dédiée. Unités, offres commerciales, dossiers publics approuvés, authentification, bibliothèque complète de médias et traitements IA arriveront avec les fonctionnalités suivantes.

**Ingestion et calendrier — ajout du 13 octobre 2026 :** [INGESTION.md](INGESTION.md) explique comment lancer Prefect, consulter les exécutions et configurer les horaires dans [son interface locale](http://localhost:4200). Trente-deux déploiements sont définis ; les quatre jobs de fiches et catalogues proposent un calendrier le samedi, désactivé sur une nouvelle installation. Le job de fichiers reste manuel. Les calendriers locaux déjà configurés restent conservés. Sur une nouvelle installation, les calendriers commencent désactivés. Le code se trouve dans `C:\Users\Karim\Repositories\property-platform\apps\ingestion\`, séparé du serveur web. Cette application réutilise les services métier Django ; sa base de métadonnées Prefect est distincte de la base immobilière. L'orchestrateur est facultatif pour consulter le site.

**Marché ADREC :** [ADREC.md](ADREC.md) explique les ventes récentes de Reem et Saadiyat, les indices, leurs trois pipelines Prefect et les nouvelles tables PostgreSQL. Ces prix décrivent des ventes passées, pas des unités actuellement disponibles.

**Sources à ajouter :** [SOURCES_DONNEES_UAE.md](../product/SOURCES_DONNEES_UAE.md) répertorie les autorités et jeux de données pertinents dans les sept émirats, les cinq API d’Ajman vérifiées, les accès à qualifier et l’ordre conseillé des prochains pipelines. Cet inventaire n’active pas de nouvelle collecte.

**Prochaine extension des données immobilières :** [PROPERTY_DATA_PIPELINES.md](PROPERTY_DATA_PIPELINES.md) décrit les modèles et extracteurs supplémentaires pour livraison annoncée, typologies, offres et plans de paiement. Programmer une collecte est maintenant possible avec Prefect ; les typologies et livraisons documentées sont désormais extraites par les [pipelines projets](PROJECTS.md), tandis que les offres et plans de paiement restent à développer.

**Identité technique actualisée le 12 octobre 2026 :** le paquet Python est `property_platform`, les paquets JavaScript utilisent `@property-platform/*`, et la base locale s'appelle `property_platform`. Si ton ancienne installation utilise encore d'autres noms, suivre d'abord [la reprise contrôlée de la base](BRANDING.md#reprendre-une-ancienne-base-locale-sous-le-nouveau-nom). Modifier seulement les variables PostgreSQL ne renomme pas une base déjà stockée. Sur le poste où la reprise a déjà été vérifiée, suivre les commandes ordinaires ci-dessous sans la refaire.

**Pour changer le nom affiché :** ouvrir `C:\Users\Karim\Repositories\property-platform\packages\branding\src\brand.ts` et modifier `displayName`. Le [guide de marque](BRANDING.md) explique le nom, le symbole, la reconstruction et les identités métier à conserver.

### Essayer le nouvel accueil et la carte locale

**Fiches et titres :** sélectionner une parcelle met maintenant en avant le projet ou bâtiment disponible, même lorsque son association reste incertaine. Un promoteur documenté peut remplacer un nom absent. La référence cadastrale apparaît en second, par exemple `RT3 · C53–C56` sous **The District** ; son code original reste dans les détails. Sans identité disponible, un libellé de terrain remplace le code en titre. Voir [les règles de présentation](PROPERTY_EXPLORATION.md#titres-des-fiches-et-des-listes--13-octobre-2026). Cette modification d'affichage ne demande ni `migrate`, ni import : seul le web doit utiliser le nouveau code.

L'accueil présente les sept émirats et trois photographies locales de Dubai et Abu Dhabi : une vue nocturne au premier écran, le littoral dans la section suivante et les palmiers au coucher du soleil à la fin. Chaque section garde sa photo ; il n'y a plus de diaporama, de boutons pour changer la photo ni de lecture/pause. Ces photographies sont utilisées sous la licence Unsplash ; leurs auteurs, pages et droits restent dans `C:\Users\Karim\Repositories\property-platform\apps\web\public\images\uae\credits.json`, sans crédit affiché sur l'accueil. Les sources immobilières restent consultables dans la carte et les fiches ; le bandeau « Data & sources » de l'accueil a été retiré.

En faisant défiler la page, le paysage se déplace plus lentement que le texte : c'est la **parallaxe**. Sur ordinateur, la photo du littoral reste un instant en place pendant que le contenu passe à côté. Le réglage système « réduire les animations » désactive ces mouvements ; sur téléphone ils sont plus courts et la photo du littoral défile normalement. La plateforme vise tous les Émirats ; Al Reem reste le premier jeu de données. [Le guide de couverture nationale](UAE_COVERAGE.md) indique où configurer les territoires et comment en activer un nouveau. [Le guide du thème](VISUAL_DESIGN.md) détaille les droits des images, le cadrage, les textes, les nouvelles polices locales, les boutons, les couleurs et les effets.

**Pour voir une modification du thème ou du code web**, la base et l'API peuvent rester démarrées. Depuis `C:\Users\Karim\Repositories\property-platform`, lancer :

```powershell
pnpm.cmd dev:web
```

Garder ce terminal ouvert. Next.js lit le code du dossier Windows et actualise les pages lors des modifications. La commande de racine est bien **`dev:web`**, pas `dev`. Si ce serveur tourne déjà, enregistrer le fichier suffit généralement ; après modification de `.env.local`, le redémarrer avec Ctrl+C puis cette commande. `pnpm.cmd install --frozen-lockfile` sert à la première installation ou après modification des dépendances/verrouillage, pas à chaque modification d'un titre ou d'une couleur.

Ouvrir [l'accueil anglais](http://localhost:3000/en), puis **Explore the Emirates**. Les sélecteurs permettent de choisir l'émirat et la zone ; Abu Dhabi ouvre Al Reem par défaut ; sélectionner **Saadiyat Island** dans **Area** pour la deuxième île. [La carte](http://localhost:3000/en/explore) charge les parcelles déjà importées, pas une nouvelle collecte. Les autres émirats montrent une couverture en préparation. Cliquer sur un contour ou une référence de la liste affiche sa source et ses dates. La recherche trouve codes, usages et noms localisés ; l'onglet rues cherche les noms de rues. Les offres d’appartements ne sont pas encore recherchables. L’onglet Market permet de chercher les ventes ADREC par nom de projet, avec leurs prix enregistrés.

**L’exploration met maintenant les biens au premier plan.** L’onglet Properties affiche les bâtiments et repères de projets existants. Un clic ouvre la fiche et souligne l’objet sans déplacer la carte ; le bouton **Locate on map** permet de cadrer volontairement. Les secteurs et périmètres ProjectLimits ne sont plus cliquables. La priorité est bâtiment, repère explicite de projet, vraie parcelle, autre lieu, rue. Les données cadastrales sont conservées dans les sections secondaires.

**Cette évolution ajoute aussi deux tables de preuves immobilières**, contrairement aux changements de thème seuls : `property_platform.evidence.property_presentation` et `property_platform.evidence.property_media`. Sur ce poste, migration, import des premières fiches Sun Tower / Sky Tower / Leaf Tower / The District / Vista 3 / Radisson Residences et mise à jour de l’API sont déjà faits. Les autres bâtiments ne reçoivent pas de promoteur ou de photo inventés. Le [guide des fiches immobilières](PROPERTY_EXPLORATION.md) explique les données réellement disponibles, leurs droits, les fichiers et les commandes pour une autre installation. Refaire Onwani n’est pas nécessaire.

<a id="apres-maj"></a>

### Que relancer après une modification ?

Toutes les commandes de cette partie s'écrivent dans PowerShell depuis `C:\Users\Karim\Repositories\property-platform`.

| Ce qui a changé | Action utile | Ce que cela change |
|---|---|---|
| Code, thème, images ou traductions web ; site sur **3000** | `pnpm.cmd dev:web`, si le serveur est arrêté | Lit les fichiers Windows actuels ; rechargement de développement |
| Dépendances JavaScript ou `pnpm-lock.yaml` | `pnpm.cmd install --frozen-lockfile`, puis redémarrer le web | Installe les versions décidées dans le verrouillage ; n'importe aucune donnée |
| Code Python sous `C:\Users\Karim\Repositories\property-platform\apps\api\` | Reconstruire **api**, comme ci-dessous | Copie le code actuel dans une nouvelle image et remplace son conteneur après un build réussi |
| Code ou dépendances sous `C:\Users\Karim\Repositories\property-platform\apps\ingestion\` ; services Django qu'il réutilise | Reconstruire l'image d'ingestion et reprendre les services, voir [INGESTION.md](INGESTION.md) | Actualise les collecteurs et le runner ; conserver les calendriers édités dans l'UI et les volumes |
| Nouvelles migrations Django | Après reconstruction réussie de l'API, lancer `migrate --noinput` | Applique les évolutions SQL non encore enregistrées ; ne collecte aucune donnée |
| Code web ; site Docker sur **3102** | Reconstruire **web**, voir la variante Docker ci-dessous | Prépare un nouveau site compilé ; ce conteneur ne surveille pas les fichiers Windows |
| Nouvelles données à collecter | Lancer la commande d'import adaptée, section 6 | Contacte la source et enregistre preuves et objets ; une compilation ne lance aucun import |

**Seulement après modification du backend**, exécuter cette commande et attendre son succès :

```powershell
docker compose -f infra/local/compose.yaml up -d --build api
```

Elle lit `C:\Users\Karim\Repositories\property-platform\infra\local\compose.yaml`, construit l'image depuis `C:\Users\Karim\Repositories\property-platform\apps\api\Dockerfile`, assure le démarrage de la base dont l'API dépend, puis démarre ou recrée **api** si nécessaire. `-d` signifie que les services restent en arrière-plan. Le site **web** n'est pas la cible de cette commande. Compose réutilise les étapes inchangées du build ; arrêter tous les conteneurs avant n'est pas nécessaire. Les données PostgreSQL restent dans leur volume.

Si la structure SQL a aussi changé, ou pour vérifier les migrations en attente, lancer ensuite :

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
```

`exec` exécute la commande **dans le conteneur API existant**. `migrate` applique les migrations Django ; `No migrations to apply` est un résultat normal. Si le build précédent a échoué, ce conteneur peut encore utiliser l'ancien code : une migration réussie ne signifie donc pas que l'image a été mise à jour. Arrêter cette séquence à la première erreur de build et suivre le dépannage ci-dessous. Les imports restent séparés (section 6).

Si Prefect est utilisé, reconstruire aussi l'image d'ingestion après une modification des services Django qu'elle embarque. Les images API et ingestion contiennent chacune une copie du code ; reconstruire l'une n'actualise pas l'autre. Le [guide d'ingestion](INGESTION.md) décrit la séquence et la migration préalable au démarrage du runner.

La modification de couverture nationale du 12 octobre ne change pas les tables. Pour installer cette évolution backend sur une autre installation, reconstruire l'API et le site suffit, sans réimporter Reem. Sur le poste où elle a déjà été appliquée, choisir le parcours correspondant aux fichiers modifiés dans le tableau ci-dessus. `migrate` reste la commande ordinaire pour appliquer d'autres évolutions de structure. Ajouter un émirat à la navigation ne collecte aucune donnée. Les commandes `import_onwani` et `import_reem_*` restent propres au pilote, avec les mêmes preuves et UUID.

Si la base est vide, appliquer les migrations et l'import de la section 6 avant d'explorer. Un message d'indisponibilité indique de vérifier l'API ; une carte vide et une recherche sans résultat sont des états différents. Les couches rues, secteurs, empreintes 2D, lieux et satellite sont disponibles après les imports de la section 6.8. La 3D n'est pas encore livrée. Les coordonnées ne sont pas une certification de limites foncières.

Pour changer l'adresse de l'API, copier `C:\Users\Karim\Repositories\property-platform\apps\web\.env.example` vers `C:\Users\Karim\Repositories\property-platform\apps\web\.env.local`, régler PROPERTY_PLATFORM_API_ORIGIN, puis redémarrer Next.js. Ce réglage reste côté serveur. Le site en développement autorise le relais local ; pour essayer le **site compilé localement**, définir aussi PROPERTY_PLATFORM_ENABLE_LOCAL_PREVIEW=1 dans ce fichier ou dans le terminal de lancement. Sans cet opt-in, le web compilé refuse l'aperçu. Django hors DEBUG le refuse dans tous les cas. Ce mécanisme n'est pas une procédure de mise en production.

Les commandes sont prévues pour **Windows et PowerShell**, depuis la racine du dépôt sauf indication contraire. Exécuter chaque commande séparément ; résoudre une erreur avant de poursuivre.

Les versions courantes et les exceptions de compatibilité sont documentées dans [TOOLCHAIN.md](TOOLCHAIN.md). Les anciennes études de stack restent des documents historiques ; les manifestes et ce guide décrivent les versions exécutées.

**Repère pour retrouver les fichiers :** les chemins du dépôt sont écrits depuis sa racine `C:\Users\Karim\Repositories\property-platform`. Par exemple, `apps/api/src/property_platform/config/settings/base.py` désigne sur ton PC `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\config\settings\base.py`. Les chemins commençant par `/app/` désignent au contraire des fichiers **dans le conteneur Linux**, pas dans l'explorateur Windows. Les noms courts dans une arborescence se lisent avec tous leurs dossiers parents.

### Variante : prévisualisation entièrement dans Docker

**État du poste après la validation nationale du 12 octobre :** la prévisualisation compilée actuelle est disponible sur 3102 et peut se redémarrer avec `docker compose -f infra/local/compose.yaml --profile web-preview up -d --no-build`. Les reconstructions nécessitant PyPI/npm rencontrent actuellement `UnknownIssuer` sur ce poste ; voir [le compte rendu et les limites](UAE_COVERAGE.md#validation-de-cette-modification). `--no-build` réutilise les images présentes et ne compile pas un nouveau changement.

Si tu préfères essayer le site compilé sans lancer Node sur Windows, depuis `C:\Users\Karim\Repositories\property-platform` :

```powershell
docker compose -f infra/local/compose.yaml --profile web-preview up -d --build web
```

Compose construit le site, assure le démarrage de ses dépendances API/PostGIS, puis expose [l'accueil](http://localhost:3102/en) et [l'exploration](http://localhost:3102/en/explore) sur **3102**, sans occuper le port 3000. Le démarrage des dépendances peut aussi nécessiter leur construction si leurs images/configurations ne sont pas à jour. C'est une prévisualisation locale compilée, sans rechargement automatique. Le profil est facultatif : un lancement Compose habituel n'ajoute pas ce site Docker.

Si **api et db tournent déjà** et que **seul le web a changé**, reconstruire uniquement le web :

```powershell
docker compose -f infra/local/compose.yaml --profile web-preview up -d --build --no-deps web
```

`--no-deps` laisse les autres services en place ; ne pas utiliser cette variante si l'API ou la base sont arrêtées ou doivent être mises à jour. La reconstruction peut encore rencontrer le problème de certificat du poste. `restart web` ou `up --no-build` réutilisent l'image existante : ils ne copient pas les nouveaux fichiers web dans une image. Le site Docker sur 3102 et le site de développement sur 3000 peuvent fonctionner ensemble, mais lire deux versions différentes après une modification. Pour travailler au quotidien sur le web, privilégier **3000**.

Pour tout arrêter après avoir utilisé ce profil :

```powershell
docker compose -f infra/local/compose.yaml --profile web-preview down
```

Cette commande conserve le volume PostgreSQL. Ne pas ajouter `-v`. Le contrôle local du 11 octobre a validé cette variante ; le build natif Windows de l'agent a été bloqué par les permissions du cache SWC, sans désactiver ses protections. Cela ne prouve pas que le même problème existe dans ton terminal personnel.

Pour les données et imports de la deuxième île, consulter aussi [Saadiyat : données, commandes et limites](SAADIYAT.md).

## Sommaire

- [Contexte Abu Dhabi : nouvelles ingestions et tables](#contexte-abu-dhabi)

- [Mémo rapide : lancer, vérifier et arrêter](#memo-rapide)
- [Que relancer après une modification ?](#apres-maj)
- [1. Comprendre les outils et savoir où écrire les commandes](#choisir-le-parcours)
- [2. Installer les outils Windows](#prerequis)
- [3. Ouvrir le dépôt, choisir la branche et installer les dépendances](#installer-les-dependances)
- [4. Démarrer le site — terminal A](#demarrer-le-site)
- [5. Démarrer l'API et la base, puis créer les tables — terminal B](#demarrer-api-postgis)
- [6. Importer les données et comprendre le pipeline de data engineering](#data-engineering)
- [6.9. Programmer et suivre les ingestions avec Prefect](#orchestration-prefect)
- [Fichiers, photos et futur stockage R2/CDN](#stockage-medias)
- [7. Créer un compte d'administration — facultatif](#compte-administration)
- [8. Routine quotidienne, modifications et arrêt](#routine-quotidienne)
- [9. Construire et essayer le site compilé](#site-compile)
- [10. Vérifier le code et les contrats](#verifier-le-code)
- [11. Dépanner les erreurs](#depannage)
- [12. Comprendre le passage en production](#production)
- [Saadiyat : données et imports de la deuxième île](#saadiyat)

**Accès directs :**

- [Ouvrir PowerShell et retrouver les fichiers](#ecrire-les-commandes)
- [Installer les paquets web, étape par étape](#installer-paquets-web)
- [Comprendre les noms Docker](#noms-docker)
- [Créer les tables Django](#migrations-django)
- [Retrouver modèles et migrations](#fichiers-modeles-migrations)
- [Vérifier que l'API répond](#verifier-api)
- [Lancer l'import Onwani](#premier-import-manuel-des-parcelles-onwani)
- [Ajouter rues, bâtiments, lieux, références et satellite](#couches-reem)
- [Lire le code de collecte, contrôle et stockage](#code-import)
- [Ouvrir l'orchestrateur et comprendre ses neuf procédures](#orchestration-prefect)
- [Consulter les tables avec une interface graphique](#consulter-la-base)
- [Reconstruire le backend après une modification](#modification-backend)
- [Arrêter en conservant les données](#arreter-les-services)

**Quel parcours suivre ?** Première installation : sections 1 à 5. Reprendre le travail sur un poste déjà prêt : mémo rapide ou section 8. Alimenter et examiner les parcelles : section 6, après la section 5. Modifier et vérifier le code : sections 8 à 10. Une erreur : section 11. Tu n'as pas besoin d'exécuter tous les blocs du document à chaque lancement.

<a id="memo-rapide"></a>

## Mémo rapide : lancer, tester et tout arrêter

<a id="stockage-medias"></a>

**Photos et fichiers — ajout du 15 octobre 2026 :** le [guide MEDIA_STORAGE.md](MEDIA_STORAGE.md) détaille le volume local partagé, les trois nouvelles tables `evidence`, la commande `archive_property_media`, la tâche Prefect et la préparation de R2/S3 avec CDN facultatif. Pour installer cette évolution : sauvegarder la base, reconstruire API et ingestion, appliquer `migrate`, puis lancer l’archivage ; le guide donne chaque commande et son effet. Le cloud reste désactivé tant que ses accès ne sont pas configurés. Les captures SQL existantes sont conservées. Le site compilé doit aussi être reconstruit pour utiliser le futur champ `delivery_url`.

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
docker compose -f infra/local/compose.yaml up -d --no-build db api
docker compose -f infra/local/compose.yaml ps
Invoke-RestMethod 'http://localhost:8000/api/v1/health/live'
Invoke-RestMethod 'http://localhost:8000/api/v1/health/ready'
```

Ce mémo suppose que les images et la base ont **déjà été préparées avec ce guide**. `--no-build` démarre les images existantes ; il ne prend pas en compte une modification Python et ne construit pas une image absente. Pour une première installation, suivre l'étape 5 ; pour un changement backend ou de schéma, suivre [Que relancer après une modification ?](#apres-maj).

Résultat attendu : site accessible, `api` en cours d'exécution, `db` en état `healthy`, réponses `ok` et `ready`. Tu peux aussi ouvrir [la documentation de l'API](http://localhost:8000/api/v1/docs). Il s'agit d'une vérification rapide du démarrage ; les contrôles de code et tests automatisés sont détaillés à l'étape 10. Si une commande échoue, résoudre l'erreur avant de continuer.

**Tout arrêter :** appuyer sur **Ctrl+C dans le terminal A**. Si Prefect est aussi lancé, suivre [l'arrêt complet dans INGESTION.md](INGESTION.md). Sinon, exécuter dans le terminal B :

```powershell
docker compose -f infra/local/compose.yaml down
```

Le serveur web, l'API et la base de ce parcours sont alors arrêtés. **Si tu as aussi lancé Prefect**, suivre [l'arrêt complet dans INGESTION.md](INGESTION.md) : l'overlay facultatif ajoute des services que cette commande ne prend pas en charge. **Les données de PostgreSQL sont conservées** : ne pas ajouter `-v` à `down`, car cette option supprime le volume de données. Fermer le navigateur ne suffit pas à arrêter les services. Docker Desktop peut rester ouvert ou être quitté après cet arrêt.

<a id="choisir-le-parcours"></a>

## 1. Comprendre les outils et le fonctionnement local

<a id="ecrire-les-commandes"></a>

### 1.1. Où écrire les commandes et retrouver les fichiers ?

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

### 1.2. Comprendre les outils avant les commandes

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
| Python / Django | Langage et framework utilisés pour le backend | Faire fonctionner l'API et les services métier qui contrôlent et enregistrent les données |
| API | Programme qui reçoit des demandes et renvoie des réponses structurées | Répondre aux contrôles de santé et aux lectures de l'atlas local |
| PostgreSQL | Serveur de base de données | Conserver durablement les données de l'application |
| PostGIS | Extension de PostgreSQL pour les données géographiques | Stocker parcelles, rues, empreintes de bâtiments et périmètres ; calculer distances et intersections |
| Docker Desktop | Application qui fait tourner des environnements isolés sur Windows | Exécuter ici l'API et la base dans des conteneurs Linux |
| Docker Compose | Outil Docker qui démarre plusieurs services à partir d'un fichier de configuration | Lire infra/local/compose.yaml et gérer les services api et db ensemble |
| uv | Gestionnaire des outils et dépendances Python | Préparer l'environnement Python pour les tests natifs, à l'étape 10 |
| Prefect | Orchestrateur avec interface web : décide quand exécuter les ingestions et suit leur résultat | Neuf procédures du pilote ; exécutions, logs et calendriers sur le port 4200 |
| Runner d'ingestion | Processus Python qui attend les travaux demandés à Prefect | Exécuter une ingestion à la fois, dans un processus séparé du site et de l'API |

**npm et pnpm servent à des tâches similaires.** Nous utilisons npm pour installer pnpm, puis pnpm pour gérer le projet. Les deux noms dans le guide ne désignent pas deux sites à lancer. Le suffixe `.cmd` est simplement le lanceur Windows de ces outils.

Un **serveur** est un programme qui reste en marche pour répondre aux demandes. Un **port** est le numéro qui distingue ses points d'accès sur une machine : 3000 pour le web, 8000 pour l'API, 5432 pour PostgreSQL et 4200 pour Prefect. **localhost** signifie « cet ordinateur » : localhost:3000 ouvre le serveur web qui tourne sur ton PC.

Une **image Docker** est un environnement préparé avec les programmes nécessaires. Un **conteneur** est une instance en cours d'exécution de cette image. Un **volume** est un stockage conservé séparément : la base garde ainsi ses données lorsqu'on arrête ou remplace un conteneur.

### 1.3. Ce que chaque étape change

| Section | Ce qu'elle fait | Ce qui reste après |
|---|---|---|
| 1 | Comprendre les outils et le terminal | Rien n'est lancé par la lecture |
| 2 | Installer les outils Windows | Git, Node/pnpm et Docker disponibles |
| 3 | Récupérer le code et installer ses bibliothèques | Dépôt, dépendances et caches locaux |
| 4 | Démarrer Next.js | Site disponible pendant que son serveur tourne |
| 5 | Démarrer Django/PostGIS et appliquer les migrations | Services locaux et tables dans le volume persistant |
| 6 | Collecter, contrôler et importer les parcelles | Données, captures, observations, audit et quarantaine dans PostgreSQL |
| 7 | Créer un administrateur facultatif | Compte Django conservé dans la base |
| 8 | Relancer, reconstruire ou arrêter | Données conservées à l'arrêt ordinaire |
| 9 | Construire et essayer une version compilée du site | Artefact web local ; aucun déploiement |
| 10 | Contrôler le code et les contrats | Résultats de tests et contrats éventuellement régénérés |
| 11 | Diagnostiquer une erreur précise | Actions adaptées au problème |
| 12 | Préparer les décisions de production | Aucun hébergement souscrit ni déploiement automatique |

À l'étape 4, si l'installation 3.3 et le démarrage ont réussi, **tu as préparé les bibliothèques puis lancé le serveur web**. L'API et PostgreSQL ne sont pas démarrés par pnpm dev:web. Les pages du site peuvent s'ouvrir, mais l'exploration des données enregistrées exige aussi les services de l'étape 5.

| Objectif | Prérequis | Étapes |
|---|---|---|
| Voir et modifier le site | Git, Node.js 26.11.1, pnpm 12.10.1 | 2 à 4 |
| Lancer aussi l'API et PostGIS | Prérequis web + Docker Desktop avec Compose | 2 à 5 ; compte facultatif en section 7 |
| Exécuter les outils Python et tests isolés sur Windows | uv 0.13.0 et Python 3.14.8 géré par uv | 10 |
| Programmer et superviser les ingestions avec une UI | Docker Desktop, base préparée et image d'ingestion | 6.9 et [INGESTION.md](INGESTION.md) |

Python et uv ne sont pas nécessaires sur Windows pour lancer l'API Docker : l'image contient leur environnement et les bibliothèques GIS. Le web actuel fonctionne seul, sans API ni compte Supabase, cartographique ou IA. Aucun service payant n'est requis pour ce lancement local.

Le fichier `C:\Users\Karim\Repositories\property-platform\.python-version` de racine indique maintenant **3.14.8**, comme les applications API et ingestion. Cette indication guide les outils Python ; elle n'installe rien à la lecture du fichier et ne remplace pas automatiquement un environnement `.venv` existant.

<a id="prerequis"></a>

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

<a id="installer-les-dependances"></a>

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

### 3.2.1. Choisir la version du code avant de lancer les commandes

Une **branche Git** est une version de travail du code dans le même dépôt. Elle ne crée pas une base de données séparée. La branche actuelle du premier import est `codex/onwani-import` ; `main` conserve le socle précédent tant que cette fonctionnalité n'y est pas intégrée.

Depuis la racine, dans PowerShell :

```powershell
git branch --show-current
git status --short
```

La première commande donne le nom de la branche ; la seconde indique tes modifications locales. La section 6.1 explique comment récupérer la branche d'import. Ne pas effacer des modifications pour changer de branche. Après un changement de code backend, reconstruire son image : Git change les fichiers Windows, pas automatiquement le programme déjà copié dans Docker.

<a id="installer-paquets-web"></a>

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
- **Erreur de certificat** : consulter l'étape 11 ; ne pas désactiver la vérification TLS.
- **Autre erreur** : conserver le texte complet affiché et le partager pour diagnostiquer le problème avant de passer à l'étape suivante.

Les scripts d'installation de Parcel/SWC sont désactivés explicitement dans pnpm-workspace.yaml ; leurs binaires de plateforme sont fournis par les dépendances optionnelles. **Ne pas ajouter --no-optional.** node_modules et .pnpm-store sont locaux et ignorés par Git.

<a id="demarrer-le-site"></a>

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
- La page affiche Property Platform, United Arab Emirates et les sept émirats ; le premier jeu de données annoncé est Al Reem.
- Le sélecteur propose les quinze langues configurées.
- [L'arabe](http://localhost:3000/ar), l'ourdou et le persan utilisent le sens de lecture de droite à gauche.

Si le port 3000 est occupé, Next peut en choisir un autre : utiliser l'adresse affichée dans le terminal.

**Le petit « N » que tu pouvais voir** était le bouton des outils de développement Next.js, ajouté par le framework pendant le développement. Il est maintenant masqué avec `devIndicators: false` dans `C:\Users\Karim\Repositories\property-platform\apps\web\next.config.ts`, conformément à [la documentation Next.js](https://nextjs.org/docs/app/api-reference/config/next-config-js/devIndicators). Les erreurs et les journaux restent accessibles dans le terminal. Après un changement de cette configuration, arrêter le serveur avec Ctrl+C puis relancer `pnpm.cmd dev:web` ; pour le site Docker compilé sur 3102, reconstruire le web comme indiqué au début du guide.

Modifier par exemple apps/web/messages/en.json ou apps/web/src/app/[locale]/page.tsx puis enregistrer : le serveur de développement recharge les changements. Les textes visibles doivent rester dans les dictionnaires. Voir [la politique multilingue](INTERNATIONALIZATION.md).

**Ctrl+C** dans ce terminal arrête le site. Tant que le serveur tourne, utiliser un autre terminal pour les commandes suivantes.

**Ce qui est conservé après Ctrl+C :** le code, les bibliothèques installées et les fichiers générés sur disque. **Ce qui s'arrête :** le serveur web lancé dans cette fenêtre. Tu peux le relancer avec la même commande sans tout réinstaller. Fermer seulement l'onglet du navigateur n'arrête pas le serveur.

Ce lancement est du développement local, pas une publication publique du site. Si Next affiche aussi une adresse « Network », elle correspond à un accès possible depuis ton réseau local selon la configuration ; elle ne signifie pas que le site a été déployé sur Internet.

<a id="demarrer-api-postgis"></a>

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

Le Compose utilise désormais le volume `property-platform-local_postgres18-data`, monté sous `/var/lib/postgresql`, conformément à l'image PostgreSQL 18. L'ancien volume `property-platform-local_postgres-data` est conservé mais **n'est pas migré automatiquement**. Le premier lancement en PostgreSQL 18 initialise une nouvelle base : recréer les migrations et le superutilisateur ci-dessous. Si l'ancien volume contient des données à conserver, préparer un export/restauration ou une migration validée avant de basculer les usages. Ne pas monter directement son répertoire PostgreSQL 17 dans PostgreSQL 18 et ne pas le supprimer. Aucun transfert ou effacement de base n'est exécuté par la mise à jour du dépôt.

<a id="noms-docker"></a>

### D'où viennent les noms des services, images et conteneurs ?

Compose lit [infra/local/compose.yaml](../../infra/local/compose.yaml) et démarre deux **conteneurs** à partir de deux **images**. Une image est le modèle préparé ; un conteneur est une instance exécutée à partir de ce modèle ; un service est la définition de ce que Compose doit lancer.

Voici un **extrait simplifié à lire**, pas une commande à exécuter ni un remplacement du fichier complet :

```yaml
name: property-platform-local

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
| Image utilisée | `postgis/postgis:18-3.6`, téléchargée si nécessaire | `property-platform-local-api`, construite localement depuis notre Dockerfile |
| Conteneur créé | `property-platform-local-db-1` | `property-platform-local-api-1` |

`name: property-platform-local` fixe le nom du projet Compose. Par défaut, le nom du conteneur suit **projet + service + numéro** : `property-platform-local` + `api` + `1` donne `property-platform-local-api-1`. Le numéro distingue les instances d'un service. Pour `api`, nous n'avons pas déclaré de champ `image:` : Compose attribue à l'image construite le nom `property-platform-local-api`. Ces noms correspondent aux commandes de ce guide, sans option ni variable qui remplace le nom du projet.

Dans les commandes Compose, on utilise le **service** : `exec api`, `logs api` ou `logs db`. Il n'est donc pas nécessaire d'écrire le nom complet du conteneur.

### Pourquoi `docker compose … ps` et `docker ps` affichent-ils des tableaux différents ?

Ces deux commandes consultent l'état des conteneurs ; elles ne les démarrent pas et ne modifient pas la base.

| Commande | Ce qu'elle affiche |
|---|---|
| `docker compose -f infra/local/compose.yaml ps` | Les conteneurs du projet décrit par ce YAML, avec leur service `api` ou `db` |
| `docker ps` | Tous les conteneurs actuellement démarrés sur le Docker auquel ton terminal est connecté, avec notamment leur identifiant |

Si seuls nos deux conteneurs tournent, les deux tableaux montrent les mêmes instances, avec des colonnes différentes. `IMAGE` indique le modèle utilisé ; `NAME` ou `NAMES` indique le conteneur ; `SERVICE` indique le service Compose ; `CONTAINER ID` est l'identifiant technique du conteneur. `Up` indique qu'il tourne, et `healthy` que son contrôle de santé réussit. Les durées changent entre deux commandes exécutées à des moments différents.

**Voir `api` en cours d'exécution et `db` en état `healthy` ne prouve pas que les tables Django existent déjà.** C'est le rôle de l'étape 5.1.

<a id="migrations-django"></a>

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

<a id="fichiers-modeles-migrations"></a>

#### Où sont les modèles et les fichiers de migration ?

Un **modèle** est une classe Python décrivant les données de l'application, par exemple un bâtiment et ses champs. Une **migration** est un fichier Python décrivant une évolution de la base correspondant à ces modèles. Les fichiers Python ne contiennent pas les lignes de données : celles-ci sont enregistrées dans PostgreSQL.

**Une partie des modèles et migrations est fournie par Django lui-même.** Ces fichiers sont installés dans les dépendances Python du conteneur API, pas dans nos dossiers de code métier. Nos modèles de parcelles et de provenance, décrits ensuite, sont dans le dépôt. Les applications concernées sont déclarées dans `INSTALLED_APPS`, dans [apps/api/src/property_platform/config/settings/base.py](../../apps/api/src/property_platform/config/settings/base.py).

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
apps/api/src/property_platform/modules/catalog/
├── apps.py                     Existe : déclaration du module Django
├── README.md                   Existe : responsabilités du catalogue
├── models.py                   Existe : modèle Parcel, géométrie et champs typés
├── services.py                 Existe : mutations du catalogue et conversion des géométries
└── migrations/                 Existe : historique de leur structure en base
    ├── __init__.py
    ├── 0001_initial.py         Existe : première création de la table des parcelles
    ├── 0002_enforce_data_integrity.py  Existe : contraintes SQL d'intégrité
    └── 0003_real_estate_schema.py      Existe : déplacement vers real_estate.parcel
```

Pour retrouver ces fichiers sans lire l'arborescence : [apps/api/src/property_platform/modules/catalog/models.py](../../apps/api/src/property_platform/modules/catalog/models.py), dossier `apps/api/src/property_platform/modules/catalog/migrations/`, première migration `apps/api/src/property_platform/modules/catalog/migrations/0001_initial.py`. Les modèles de provenance sont dans [apps/api/src/property_platform/modules/evidence/models.py](../../apps/api/src/property_platform/modules/evidence/models.py), avec leurs migrations dans `apps/api/src/property_platform/modules/evidence/migrations/`.

On pourra répartir les modèles dans un paquet `apps/api/src/property_platform/modules/catalog/models/` si leur taille le justifie. Les modules `apps/api/src/property_platform/modules/evidence/` et `apps/api/src/property_platform/modules/publication/` auront leurs propres modèles et migrations pour les données qu'ils possèdent ; tout ne sera pas regroupé dans le catalogue.

Le cycle de développement est **modifier les modèles → générer les migrations avec `makemigrations` → relire et conserver ces fichiers dans Git → appliquer avec `migrate`**. `makemigrations` prépare des fichiers ; `migrate` modifie la base. **À cette étape du démarrage, utilise seulement `migrate` : les migrations du dépôt sont déjà générées.** Les bâtiments et logements restent à développer.

Le Compose actuel copie le code dans l'image sans monter les fichiers Windows. Une migration générée uniquement dans le conteneur n'apparaît donc pas automatiquement dans ton dépôt et peut être perdue lors de sa recréation. Lors du développement des premiers modèles, il faudra générer les fichiers dans l'environnement local configuré ou les récupérer explicitement dans le dépôt avant de reconstruire l'image. Voir aussi [la structure des modules](REPOSITORY.md).

<a id="verifier-api"></a>

### 5.2. Vérifier les endpoints

Un **endpoint** est une adresse précise de l'API à laquelle envoyer une demande. Invoke-RestMethod envoie ici une requête HTTP depuis PowerShell et affiche la réponse. Ces requêtes de santé ne créent pas d'utilisateur ou de bien immobilier.

```powershell
Invoke-RestMethod 'http://localhost:8000/api/v1/health/live'
Invoke-RestMethod 'http://localhost:8000/api/v1/health/ready'
```

Le champ status doit valoir **ok** pour live et **ready** pour ready. live vérifie que l'API répond ; ready vérifie une connexion fonctionnelle avec PostGIS. ready ne remplace pas les migrations ni les futurs tests métier.

Ouvrir [la documentation interactive locale](http://localhost:8000/api/v1/docs) pour voir les endpoints. Elle décrit les contrôles de santé et les lectures de l'atlas local ; ces lectures de prévisualisation ne constituent pas encore une API immobilière publique approuvée.

Les ports sont limités à la machine locale : web 3000, API 8000, base 5432. Compose fournit déjà ses variables et identifiants de développement : **aucun .env n'est requis pour ce parcours**. apps/api/.env.example illustre une exécution Python native ; Django ne charge pas automatiquement une copie .env dans la configuration actuelle.

<a id="data-engineering"></a>

## 6. Importer les données et comprendre le pipeline de data engineering

Le **data engineering** consiste à organiser la récupération, le contrôle, la transformation et le stockage des données, pour pouvoir refaire le travail et vérifier son origine. Ici, il alimente les jeux configurés du pilote : parcelles, contexte géographique, références, premières présentations immobilières et aperçus satellite. La carte consulte ensuite les données déjà enregistrées ; elle ne collecte pas les sources à chaque clic.

Trois commandes répondent à trois besoins différents : **démarrer les services** les rend disponibles ; **migrate** prépare les tables ; **import_onwani** les alimente avec les données extérieures. Le navigateur et le serveur Next.js ne participent pas à l'import.

<a id="premier-import-manuel-des-parcelles-onwani"></a>

### 6.1. Lancer le premier import manuel des parcelles Onwani

**Facultatif pour lancer le site, nécessaire pour alimenter le catalogue de parcelles.** Cette commande interroge directement DMT/Onwani ; elle n'utilise pas le HTML fourni. Le parcours ci-dessous reste manuel. Pour lancer la même famille d'import depuis une UI ou selon un calendrier, suivre [le parcours Prefect](#orchestration-prefect).

**1. Ouvrir Docker Desktop**, puis un terminal PowerShell (le terminal B si le site tourne déjà). Le site web n'a pas besoin de tourner pour importer les données.

**2. Se placer à la racine du projet et vérifier la branche :**

```powershell
Set-Location 'C:\Users\Karim\Repositories\property-platform'
git status --short
git branch --show-current
```

L'import est actuellement disponible sur **`codex/onwani-import`**, pas sur `main`. Si tu dois récupérer cette branche ou sa dernière version :

```powershell
git fetch origin
git switch codex/onwani-import
git pull --ff-only
```

Ces commandes téléchargent le code et sélectionnent sa version ; elles n'importent pas de données. Si Git signale des modifications locales qui empêchent le changement de branche ou la mise à jour, les conserver avant de continuer : ne pas utiliser une commande de réinitialisation pour les effacer. Si tu es déjà sur cette branche avec la dernière version, ne change pas de branche.

**3. Reconstruire l'API, créer les tables, puis lancer l'import**, toujours dans ce même terminal et depuis la racine :

```powershell
docker compose -f infra/local/compose.yaml up -d --build api
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
docker compose -f infra/local/compose.yaml exec api python manage.py import_onwani --actor Karim
```

La première commande reconstruit le programme API avec le nouveau code et démarre aussi la base nécessaire. La deuxième applique les migrations Django du dépôt : création des tables, contraintes, puis déplacement vers les schémas `real_estate` et `evidence`. Si elles sont déjà appliquées, elle n'effectue aucun nouveau déplacement et ne duplique rien. **La troisième est celle qui récupère les parcelles auprès d'Onwani et les enregistre dans ta base locale.** Attendre le résultat de chaque commande avant de lancer la suivante. Si `Unknown command: 'import_onwani'` apparaît, vérifier la branche et refaire la reconstruction de l'API.

`--actor Karim` identifie l'opérateur dans l'audit ; ce texte ne constitue pas une authentification. La commande de maintenance est réservée aux personnes ayant accès à l'environnement serveur. La collecte peut prendre quelques minutes. Le résultat affiche un identifiant d'acquisition et les compteurs `created`, `updated`, `unchanged`, `observed` et `quarantined`.

- `created` : nouvelles parcelles du catalogue ; `updated` : versions typées ou géométries changées ; `unchanged` : parcelles déjà présentes et identiques.
- `observed` : nombre d'enregistrements collectés ; `quarantined` : géométries invalides conservées pour examen, sans correction automatique ni remplacement d'une ancienne géométrie valide.
- Un statut `quarantined` signale un lot à examiner, pas une carte entièrement validée. Une erreur de réseau, de territoire, de schéma ou de couverture laisse le catalogue précédent intact ; les captures déjà reçues et le statut de l'acquisition restent enregistrés.

Tu peux relancer l'import : il crée une nouvelle acquisition, sans dupliquer les parcelles qui gardent le même identifiant de source. Les observations et captures successives sont conservées. Aucun enregistrement absent n'est supprimé automatiquement. L'exploration locale peut consulter ces parcelles ; l'import ne constitue pas une approbation automatique de dossiers publics.

Dans l'outil de base de données, les tables métier sont sous les schémas `real_estate` et `evidence` :

**Noms actuels après migration :** `property_platform` est la base, `real_estate` un schéma et `parcel` une table, soit `property_platform.real_estate.parcel`. Les migrations déplacent et renomment les anciennes tables `public.catalog_parcel` et `public.evidence_*` ; elles ne les copient pas. UUID, données, index et relations sont conservés. Les tables techniques Django restent dans `public`. La [revue de base de données](DATABASE_DESIGN.md) explique les choix et validations.

Sur le poste Karim, ce déplacement a été appliqué et vérifié après sauvegarde : il n'est pas nécessaire de réimporter les données pour les déplacer. Sur un autre poste déjà installé, reconstruire l'API et appliquer `migrate` comme ci-dessus effectue le déplacement ; sur une base neuve, ces mêmes migrations préparent directement la structure finale. Après migration, rafraîchir l'outil SQL et sélectionner les schémas `real_estate` et `evidence`. `migrate` ne collecte aucune donnée Onwani ; seul `import_onwani` le fait.

| Table | Ce qu'elle contient |
|---|---|
| `real_estate.parcel` | Parcelles, géométries PostGIS, identité interne et révision |
| `evidence.source` | Source officielle utilisée |
| `evidence.ingestion_run` | Historique des imports, opérateur, statut et compteurs |
| `evidence.capture` | Réponses JSON exactes, URL, horaires, empreinte SHA-256 et en-têtes disponibles |
| `evidence.parcel_observation` | Attributs originaux, version de mapping et référence de capture par parcelle |
| `evidence.audit_event` | Créations et changements du catalogue, auteur et justification |
| `evidence.quarantined_observation` | Enregistrements dont la géométrie doit être examinée |

Pour vérifier les effectifs depuis le terminal, sans modifier les données :

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py shell -c "from property_platform.modules.catalog.models import Parcel; from property_platform.modules.evidence.models import IngestionRun; print('Parcelles:', Parcel.objects.count()); print('Acquisitions:', IngestionRun.objects.count())"
```

Les dates de publication inconnues restent nulles ; les dates de réception, permis et mise à jour fournies par Onwani restent préservées dans leurs attributs originaux. Voir [DATA_PROVENANCE.md](DATA_PROVENANCE.md) pour les limites, la portée des identifiants et les responsabilités de chaque module. Utiliser les services métier et cette commande pour modifier le catalogue, pas des modifications manuelles de tables dans l'outil SQL.

Les migrations d'intégrité ajoutent aussi des protections **dans PostgreSQL** : géométrie valide et non vide, identité non blanche, révision au moins égale à 1, états/dates d'acquisition cohérents et métadonnées contrôlées. Le service continue de vérifier les réponses avant écriture ; les contraintes protègent également les écritures qui le contournent. Pour les appliquer après mise à jour du code, suivre la reconstruction API et `migrate` de la section 8. Un rejet de contrainte est une erreur à examiner, pas une raison de désactiver la protection. Ces règles ne constituent pas encore des permissions de production ni un journal inviolable.

### 6.2. Ce qui se passe pendant l'import, dans l'ordre

Voici le trajet des données ; ce schéma est une explication, pas une commande à lancer :

```text
PowerShell : manage.py import_onwani --actor Karim
    → Django exécute la commande dans le conteneur api
    → le connecteur interroge l'API officielle DMT/Onwani
    → PostgreSQL conserve chaque réponse originale et ses horaires
    → le programme contrôle et prépare les parcelles
    → les géométries invalides sont isolées en quarantaine
    → une transaction applique les parcelles valides, observations et audit
    → le terminal affiche le bilan ; aucune carte n'est encore publiée
```

1. **Réserver l'exécution.** Un verrou PostgreSQL empêche deux imports Onwani de modifier le catalogue simultanément. Une acquisition reçoit un identifiant, une version de connecteur, un opérateur et une heure de début.
2. **Contrôler la source.** Le programme lit les métadonnées de la couche `PLOT`, vérifie les champs attendus, les polygones et le système de coordonnées WGS84/EPSG:4326. Un changement inattendu fait échouer le lot.
3. **Délimiter Reem.** Il demande les identifiants des enregistrements où `DISTRICTENG = 'AL REEM ISLAND'` et `MUNICIPALITYENG = 'ADM'`. Un code de district seul ne suffit pas : la recherche initiale a révélé qu'il pouvait être réutilisé ailleurs.
4. **Collecter par lots.** Il récupère jusqu'à 100 enregistrements à chaque requête. Cela évite une réponse trop longue ou tronquée. L'accès est en lecture seule : le programme ne modifie pas les données d'Onwani.
5. **Conserver les originaux.** Chaque réponse reçue dans les limites prévues est enregistrée avec URL, horaires, statut HTTP, taille et empreinte SHA-256 avant d'être interprétée. Une capture est la réponse complète d'un lot ; une observation concerne une parcelle précise de cette capture.
6. **Contrôler et transformer.** Il vérifie territoire, identifiants, types de champs, coordonnées et fermeture des contours. Il traduit les noms de champs externes vers ceux de nos modèles, et les anneaux géographiques vers une géométrie `MultiPolygon` pour PostGIS.
7. **Isoler les anomalies.** Une géométrie qui se croise elle-même peut être conservée en quarantaine avec sa preuve. Elle n'est pas corrigée silencieusement et ne remplace pas une ancienne géométrie valide. Un mauvais territoire, un schéma inattendu ou un lot manquant fait échouer l'ensemble de l'acquisition.
8. **Contrôler la couverture.** Il compare les enregistrements reçus aux identifiants demandés et relit la liste à la fin. Cela détecte les enregistrements manquants ou une liste qui a changé ; cela ne garantit pas que tous les attributs sont restés figés entre deux requêtes.
9. **Enregistrer ensemble.** Dans une transaction, il ajoute ou actualise les parcelles, conserve leurs observations, enregistre les changements et termine le bilan. Si cette phase échoue, ces mutations sont annulées ensemble. Les captures déjà collectées et la trace d'échec restent disponibles.

Une **transaction** signifie ici « tout ce groupe de modifications est validé ensemble, ou annulé ensemble ». Un **verrou** évite des imports concurrents sur cette source. Ces deux mécanismes ont des rôles différents.

### 6.3. Que signifie « nettoyer » les données ?

Le programme ne remplace pas un texte incertain par une vérité inventée. Il prépare les formats et rejette ou isole ce qu'il ne peut pas accepter.

| Opération | Exemple actuel | Ce qui est conservé |
|---|---|---|
| Vérification de territoire | Refuser une parcelle de SWEIHAN dans notre import Reem | Capture reçue et échec de l'acquisition |
| Mapping de champs | `SectorNumber_PlotID` devient `Parcel.code` | Nom et valeur originaux dans l'observation |
| Valeur absente | Un champ texte facultatif nul devient une chaîne vide dans le catalogue | Le `null` original reste dans les attributs bruts |
| Conversion géographique | Anneaux de coordonnées vers `MultiPolygon`, avec trous et parties disjointes | Contours originaux dans la capture |
| Contrôle topologique | Détecter un contour qui se croise | Enregistrement de quarantaine et référence de capture |
| Détection de changement | Comparer les attributs typés et la géométrie à la parcelle existante | Nouvelle observation ; audit et révision si le catalogue change |

WGS84/EPSG:4326 décrit les coordonnées longitude/latitude utilisées ici. Une **topologie** décrit notamment la cohérence des contours et trous. PostGIS stocke la géométrie ; MapLibre affiche ces contours dans l'exploration locale.

Une parcelle n'est pas un bâtiment ni un logement. L'usage cadastral ou le dernier permis disponible ne prouve pas à lui seul un prix, une date de livraison ou la disponibilité d'un appartement.

<a id="code-import"></a>

### 6.4. Où lire le code de collecte, contrôle et stockage ?

Dans PyCharm, ouvrir les fichiers ci-dessous. Les libellés donnent le chemin complet depuis la racine du dépôt ; les liens ouvrent les fichiers correspondants.

| Fichier | Fonction ou objet à regarder | Rôle |
|---|---|---|
| [apps/api/src/property_platform/modules/evidence/management/commands/import_onwani.py](../../apps/api/src/property_platform/modules/evidence/management/commands/import_onwani.py) | `Command.handle` | Reçoit `--actor`, déclenche l'import et affiche le bilan ou l'erreur |
| [apps/api/src/property_platform/modules/evidence/services.py](../../apps/api/src/property_platform/modules/evidence/services.py) | `import_onwani` et sa fonction interne `acquire` | Organise le travail, conserve captures/observations et gère verrou, transaction, audit et quarantaine |
| [apps/api/src/property_platform/modules/evidence/onwani.py](../../apps/api/src/property_platform/modules/evidence/onwani.py) | `fetch`, `decode`, `validate_metadata`, `object_ids`, `parse_feature` | Interroge l'API officielle, lit le JSON et contrôle les réponses/champs |
| [apps/api/src/property_platform/modules/catalog/services.py](../../apps/api/src/property_platform/modules/catalog/services.py) | `geometry_from_rings`, `reconcile_parcel` | Convertit et valide les géométries ; crée ou met à jour les parcelles |
| [apps/api/src/property_platform/modules/catalog/models.py](../../apps/api/src/property_platform/modules/catalog/models.py) | `Parcel` | Définit les données typées du catalogue et sa contrainte d'identité de source |
| [apps/api/src/property_platform/modules/evidence/models.py](../../apps/api/src/property_platform/modules/evidence/models.py) | `Source`, `IngestionRun`, `Capture`, `ParcelObservation`, `AuditEvent`, `QuarantinedObservation` | Définit les tables de provenance, historique et anomalies |
| [apps/api/tests/test_onwani_protocol.py](../../apps/api/tests/test_onwani_protocol.py) | Tests sans réseau | Vérifie les réponses malformées, mauvais territoires, doublons, coordonnées et erreurs HTTP |
| [apps/api/tests/test_onwani_postgis.py](../../apps/api/tests/test_onwani_postgis.py) | Tests avec PostGIS réel | Vérifie géométries, répétition, rollback, quarantaine et imports concurrents |

**Ordre conseillé pour comprendre :** commencer par `apps/api/src/property_platform/modules/evidence/services.py`, puis ouvrir les fonctions qu'il appelle dans les deux fichiers de connecteur et de services catalogue. Les modèles expliquent ensuite les champs enregistrés. L'ORM Django traduit les opérations comme `objects.create()` en requêtes SQL vers PostgreSQL.

Pour la collecte orchestrée, ouvrir aussi `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\`. Ce dossier possède les collecteurs, les flows Prefect, les calendriers et le stockage des reçus. Les règles métier, modèles et transactions restent dans les modules Django ci-dessus ; [INGESTION.md](INGESTION.md) donne les fichiers à lire et leur ordre d'appel.

Ici, la collecte utilise une API publique qui renvoie du JSON. Le **scraping de pages HTML**, l'OCR de documents et les traitements IA seront d'autres collecteurs ; ils ne sont pas implémentés dans cet import.

### 6.5. Comprendre provenance, dates et changements

Une **provenance** permet de répondre à « d'où vient cette information ? ». Un **audit** permet de répondre à « qui a changé quoi chez nous, quand et pourquoi ? ». L'heure de collecte ne remplace pas la date de publication de la source.

| Champ ou information actuelle | Où la trouver | Ce qu'elle signifie |
|---|---|---|
| URL, `fetched_started_at`, `fetched_at` | `evidence.capture` | Requête précise et début/fin de récupération chez nous |
| `content_sha256`, `payload` | `evidence.capture` | Empreinte et octets originaux de la réponse ; l'empreinte détecte des différences, elle ne prouve pas que la source est vraie |
| `ingested_at` | Captures, observations et quarantaine | Moment de l'enregistrement de cet objet dans notre base |
| `raw_attributes`, `field_path`, `mapping_version` | `evidence.parcel_observation` | Valeurs originales, emplacement dans la capture et version de transformation |
| `source_published_at` | Captures et observations | Inconnue dans ce connecteur, donc laissée nulle |
| `revision`, `created_at`, `updated_at` | `real_estate.parcel` | Version et dates de création/modification du catalogue chez nous |
| `actor`, `action`, `before`, `after`, `occurred_at` | `evidence.audit_event` | Opérateur et changement des attributs typés ; l'historique des géométries reste dans les captures/observations |

Par exemple, `DataReceivedDate` est une donnée reçue de la source et reste dans les attributs originaux ; elle n'est pas transformée en `source_published_at`. Les instants de notre système sont stockés en UTC et peuvent être affichés à Dubai. Une source donnant seulement un jour ne permet pas d'inventer l'heure de publication.

Si un code de parcelle change au prochain import, le catalogue est actualisé et sa révision augmente. La nouvelle observation conserve la preuve de cette acquisition ; l'ancienne observation n'est pas effacée. Si seuls des attributs bruts non projetés changent, la nouvelle observation les conserve sans nécessairement modifier la révision du catalogue.

Le rapprochement initial utilise l'identifiant de l'enregistrement dans sa source, avec une identité UUID interne pour la parcelle. Si Onwani change ses identifiants, une réconciliation supplémentaire sera nécessaire : la commande ne fusionne pas des parcelles sur la seule proximité ou un nom ressemblant. Plusieurs imports créent volontairement plusieurs observations, mais pas plusieurs parcelles pour un même identifiant de source.

<a id="consulter-la-base"></a>

### 6.6. Voir schémas, tables et lignes avec une interface graphique

Une **base** contient des **schémas**, qui regroupent les **tables**. Une table contient des lignes et colonnes. Le modèle Python décrit cette structure ; les fichiers de migration la créent ; PostgreSQL conserve les lignes. Les données immobilières ne sont pas stockées dans un fichier SQLite : SQLite sert uniquement aux tests isolés en mémoire.

La base Docker doit tourner. Dans **PyCharm Pro**, ouvrir **View → Tool Windows → Database**, puis **+ → Data Source → PostgreSQL**. Ces fonctionnalités nécessitent Pro ; si elles ne sont pas disponibles, utiliser [pgAdmin](https://www.pgadmin.org/download/) pour se connecter au même serveur.

| Paramètre local | Valeur |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `property_platform` |
| User | `property_platform` |
| Password de développement | `property-platform-local-only` |

Dans PyCharm, télécharger le pilote si demandé, cliquer sur **Test Connection**, puis **OK**. Dans les réglages de la connexion, sélectionner les schémas `real_estate`, `evidence` et `public` si nécessaire. Déplier la connexion jusqu'à **real_estate → Tables → parcel** ou **evidence → Tables**, puis ouvrir une table pour voir ses lignes. Après une migration ou un import, rafraîchir la connexion. Voir [le guide officiel PyCharm](https://www.jetbrains.com/help/pycharm/quick-start-with-database-functionality.html).

Dans pgAdmin installé sur Windows, utiliser **Servers → Register → Server**, donner un nom à la connexion et renseigner ces mêmes paramètres dans l'onglet **Connection**. La création d'une connexion n'installe pas un second serveur PostgreSQL. Ce `localhost` convient à un outil lancé sur Windows ; un outil placé lui-même dans un conteneur nécessiterait une adresse réseau adaptée.

Pour consulter le dernier bilan, ouvrir une console SQL de cette connexion et exécuter **ces lectures uniquement** : ce bloc va dans la console SQL, pas directement dans PowerShell.

```sql
SELECT COUNT(*) AS parcelles FROM real_estate.parcel;

SELECT id, status, actor, started_at, finished_at, summary, error
FROM evidence.ingestion_run
ORDER BY started_at DESC
LIMIT 10;

SELECT source_record_id, reason, ingested_at
FROM evidence.quarantined_observation
ORDER BY ingested_at DESC
LIMIT 20;
```

L'identifiant `capture_id` d'une observation permet de retrouver sa capture et son URL ; `field_path` indique l'entrée de la réponse originale. L'identifiant `parcel_id` renvoie à la parcelle. Ces liens sont des **clés étrangères**, qui maintiennent les relations entre tables. Les octets `payload` sont une réponse JSON stockée comme binaire ; l'outil peut donc afficher un blob plutôt que le JSON lisible. Ne pas modifier ces preuves pour les rendre plus jolies.

Docker Desktop → Volumes → `property-platform-local_postgres18-data` montre les fichiers internes de PostgreSQL, pas un tableau des parcelles. Des fichiers numérotés et du texte illisible sont normaux. Pour lire les lignes, utiliser la connexion SQL ; pour faire évoluer les données métier, utiliser les services/imports prévus, plutôt qu'éditer directement les tables.

### 6.7. Imports manuels et orchestration désormais disponible

Les commandes manuelles collectent parcelles, secteurs, rues et objets OSM, puis un registre borné de pages de promoteurs, courtiers, médias et forums. Prefect peut maintenant déclencher et superviser les ingestions configurées, avec le même catalogue et les mêmes règles métier. Cela ne couvre pas tous les bâtiments ou toutes les discussions. Prix structurés, avis, IA et génération vidéo ne sont pas implémentés. Les réponses et petits aperçus du pilote restent dans PostgreSQL ; stockage objet, déduplication physique et rétention viendront avec les volumes et autres formats.

Le trajet actuel est **calendrier ou clic dans Prefect → runner Python → exécution durable Django → service d'import → contrôles et stockage → consultation par l'API**. Le runner exécute les tâches ; Prefect décide quand les déclencher et suit leur état. Le serveur web n'attend pas la collecte dans une requête de visiteur. Sept calendriers sont préconfigurés en heure de Dubai, mais initialement désactivés ; l'opérateur peut les adapter et les activer dans l'UI. Les règles de reprise évitent qu'un retry du même travail réapplique silencieusement des écritures déjà validées.

Automatiser la collecte ne signifie pas accepter ou publier toutes les informations automatiquement. Prix, noms rapprochés, permis, témoignages et suggestions IA demanderont leurs propres règles de validation et preuves. Les sources indisponibles et informations inconnues resteront signalées. Les principes et limites sont détaillés dans [docs/engineering/DATA_PROVENANCE.md](DATA_PROVENANCE.md).

<a id="couches-reem"></a>

### 6.8. Ajouter les couches de l'île, les références et le satellite

**Sur ce poste, ces données ont déjà été importées dans PostgreSQL.** Pour voir le résultat, redémarrer/reconstruire l'API et le site suffit. Ne pas relancer toutes les collectes à chaque ouverture de la carte. Sur une base vide ou pour actualiser une source, utiliser le parcours suivant.

Ouvrir PowerShell dans PyCharm ou Windows et se placer à la racine :

```powershell
Set-Location C:\Users\Karim\Repositories\property-platform
docker compose -f infra/local/compose.yaml up -d --build api
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
```

`migrate` applique les fichiers de migration Django. Il crée les nouvelles tables dans leurs schémas propriétaires, conserve les parcelles existantes et **ne télécharge aucune donnée**. Les commandes suivantes exécutent le code d'import adapté à ces modèles. Attendre la fin de chaque commande avant la suivante.

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py import_onwani --actor Karim
docker compose -f infra/local/compose.yaml exec api python manage.py import_reem_map --actor Karim
docker compose -f infra/local/compose.yaml exec api python manage.py import_reem_references --actor Karim
```

- `import_onwani` relit les parcelles officielles, avec les usages détaillés et attributs observés disponibles. La commande met à jour les identités existantes et leur audit.
- `import_reem_map` collecte dans l'ordre district, secteurs, rues officielles, puis OSM. Chaque couche a sa propre acquisition et transaction ; une erreur OSM ne supprime pas les couches officielles déjà importées. Pour une seule couche, ajouter `--layer district`, `--layer community`, `--layer street` ou `--layer osm`. OSM est borné à Reem ; une indisponibilité du fournisseur exige une relance ultérieure, sans vider la base.
- `import_reem_references` relit les URL du registre. Elle conserve titre, provenance, dates et, pour les formats pris en charge, un repère déclaré. Plusieurs sources d'un même projet restent distinctes. HTTP 200 prouve la réception d'une réponse, pas la validité du contenu. La sortie indique réussite/échec par page ; l'import peut prendre plusieurs minutes.

`--actor Karim` indique qui a lancé l'opération dans l'audit interne. Pour un nom complet, écrire `--actor "Karim Serkhane"`. L'ouvrir dans le navigateur ne relance pas ces commandes. Les données restent dans le volume PostgreSQL après un arrêt normal.

Pour appliquer un nouvel extracteur aux pages déjà stockées, sans les télécharger à nouveau :

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py import_reem_references --reprocess --actor Karim
```

Ce retraitement ajoute son propre historique, conserve la date de collecte originale et relie les captures via `parent_capture_id`. Il ne prétend pas que la page vient d'être actualisée. Les repères incohérents ne deviennent pas des identités commerciales acceptées.

#### Retrouver le code et les tables

| Code sur ton PC | Ce qu'il fait |
|---|---|
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\map_sources.py` | URL fixes, requêtes bornées, contrôle des réponses/coordonnées |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\map_import.py` | Préparation, filtrage de Reem, réconciliation et observations typées |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\research_sources.py` | Extraction inerte et contrôlée des titres et repères par fournisseur |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\research_import.py` | Collecte/retraitement des pages et audit |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\project_sources.json` | Registre de liens publics à relire ; pas une liste de périmètres certifiés |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\catalog\models.py` | Modèles Parcel, Street, Building, Place, AdministrativeArea |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\catalog\map_queries.py` | Lectures spatiales et distances/surfaces calculées dans PostGIS |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\models.py` | Captures, observations, références et aperçus satellite |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\publication\land_use.py` | Couleurs/catégories ; l'usage source original reste conservé |
| `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\` | Carte, filtres, listes, fiches, sources et exports |

Dans ton outil SQL, actualiser l'arborescence après `migrate`. Tu trouveras `property_platform.real_estate.street`, `building`, `place`, `administrative_area` et les tables `property_platform.evidence.map_observation`, `research_reference`, `imagery_scene`. Les captures et historiques ont leurs tables propres. Le [dossier de couverture](REEM_MAP.md) détaille les effectifs, sources, écarts avec le HTML et règles de rapprochement.

#### Satellite : parcours facultatif de collecte, séparé du serveur

Les deux aperçus Sentinel sont déjà dans la base locale. Le bouton **Satellite** permet de choisir Esri ou une date Sentinel. Esri charge un fond externe ; Sentinel charge les petits aperçus stockés dans PostgreSQL. Une image montre une observation datée, sans certifier un permis ou un périmètre.

Pour reconstruire ces aperçus sur une autre machine, depuis la racine, avec Python 3.14 installé :

```powershell
python -m venv .cache/imagery-tools
.\.cache\imagery-tools\Scripts\python.exe -m pip install -r scripts/imagery-requirements.txt
.\.cache\imagery-tools\Scripts\python.exe scripts/acquire_reem_imagery.py --output .cache/acquisitions/sentinel-reem.json
docker compose -f infra/local/compose.yaml cp .cache/acquisitions/sentinel-reem.json api:/tmp/sentinel-reem.json
docker compose -f infra/local/compose.yaml exec api python manage.py import_reem_imagery --actor Karim --receipt /tmp/sentinel-reem.json
```

L'environnement `.cache/imagery-tools` installe Rasterio et ses dépendances **uniquement pour ce traitement**. Le script `C:\Users\Karim\Repositories\property-platform\scripts\acquire_reem_imagery.py` lit les métadonnées STAC puis seulement les plages d'octets utiles des rasters, recadre Reem, reprojette pour la carte et produit un reçu borné. Cela peut prendre plusieurs minutes. Les certificats HTTPS restent vérifiés.

`compose cp` copie ce reçu local vers `/tmp/sentinel-reem.json` **dans le conteneur API**. La dernière commande vérifie identité, coordonnées, dates, empreinte et taille, puis stocke les deux aperçus et leurs preuves en base. Ces fichiers de travail ne vont pas dans Git. Une scène existante n'est pas remplacée silencieusement si son rendu change : la commande exige alors une revue.

Enfin relancer le site avec `pnpm.cmd dev:web`, ou reconstruire le profil Docker de prévisualisation du début du guide. Ouvrir `/en/explore`, essayer RT4, une parcelle, les onglets rues/projets, la légende et les dates satellite. Les imports ne sont pas nécessaires pour simplement consulter les données déjà présentes.

<a id="orchestration-prefect"></a>

### 6.9. Programmer et suivre les ingestions avec Prefect

**Ce que cette partie ajoute :** une interface d'exploitation sur [http://localhost:4200](http://localhost:4200), indépendante du site immobilier. Une procédure enregistrée dans Prefect s'appelle un **deployment** ; une demande d'exécution crée un **flow run**, avec son état et ses logs. Le démarrage du runner enregistre ces procédures ; il ne lance pas toutes les collectes automatiquement.

Ouvrir le [guide INGESTION.md](INGESTION.md), soit `C:\Users\Karim\Repositories\property-platform\docs\engineering\INGESTION.md`, puis suivre son parcours **installation → migration → démarrage → premier contrôle dans l'UI**. Il contient les commandes complètes, les boutons à utiliser, les cas d'erreur et l'arrêt conservant les volumes. Ce guide de développement conserve les imports manuels comme alternative ; il n'est pas nécessaire de refaire tous les blocs de la section 6 avant chaque utilisation de Prefect.

| Procédures disponibles | Calendrier initial | Ce qu'elles alimentent |
|---|---|---|
| Parcelles Onwani | Préconfiguré, désactivé | Parcelles officielles et leurs preuves |
| Quatre couches : district, secteurs/community, rues officielles, OSM | Quatre calendriers préconfigurés, désactivés | Périmètres, rues, empreintes de bâtiments et lieux du pilote |
| Références de projets | Préconfiguré, désactivé | Pages du registre examiné et repères déclarés |
| Présentations immobilières et médias autorisés | Préconfiguré, désactivé | Fiches déjà examinées et photos autorisées ; pas de prix ou stock nouveaux |
| Aperçus Sentinel | Sans calendrier, manuel | Reçu existant ; l'acquisition raster reste dans son environnement séparé |
| Vérification de disponibilité de l'ingestion | Sans calendrier, manuel | Contrôle du schéma et des registres, sans collecte ni écriture métier |

Ces lignes représentent **neuf procédures : sept avec calendrier initialement désactivé, deux sans calendrier**. Avant d'activer une actualisation régulière, commencer par une exécution manuelle et examiner son résultat dans Prefect. Les changements de calendrier effectués dans l'UI sont conservés au redémarrage du runner.

Le code se trouve dans `C:\Users\Karim\Repositories\property-platform\apps\ingestion\` et l'overlay Docker dans `C:\Users\Karim\Repositories\property-platform\infra\local\compose.ingestion.yaml`. Les trois services supplémentaires sont **prefect**, **prefect-db** et **ingestion**. Prefect conserve sa supervision dans une base PostgreSQL séparée ; les objets immobiliers et leur provenance restent dans la base PostGIS existante. Les reçus de collecte vont dans un volume dédié, pas dans Git. Les photographies éditoriales et polices déjà versionnées du site restent des ressources statiques, sans ingestion planifiée.

<a id="compte-administration"></a>

## 7. Créer un compte d'administration — facultatif

**Ce que cette étape fait :** elle ajoute dans PostgreSQL un compte autorisé à utiliser l'administration Django. Ce compte reste dans le volume de base après un arrêt ordinaire. Il ne crée pas un compte GitHub, un compte Windows ou le système de connexion du futur site public.

Après les migrations :

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py createsuperuser
```

Répondre aux questions. Le mot de passe peut ne pas apparaître pendant la saisie : c'est normal. Il n'est pas enregistré dans Git.

Ouvrir [l'administration Django](http://localhost:8000/admin/) et se connecter. Elle propose actuellement les écrans Django de base ; les tables de parcelles et de preuves existent après les migrations, mais aucun écran d'édition de ces modèles n'est enregistré dans l'administration. Admin et docs interactives sont disponibles en configuration locale DEBUG ; ce parcours n'est pas prêt à publier.

<a id="routine-quotidienne"></a>

## 8. Routine quotidienne et arrêt

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

<a id="modification-backend"></a>

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

<a id="arreter-les-services"></a>

### Tout arrêter en conservant les données

Arrêter Next.js avec Ctrl+C dans le terminal A. Si Prefect est aussi lancé, utiliser [son arrêt complet](INGESTION.md). Pour le seul parcours API/PostGIS :

```powershell
docker compose -f infra/local/compose.yaml down
```

down retire les conteneurs/réseaux locaux mais conserve le volume de base. **Ne pas ajouter -v pour un arrêt ordinaire** : cela supprimerait les données PostgreSQL, notamment les comptes et futurs dossiers pilotes.

Si l'overlay Prefect est également démarré, utiliser la procédure d'arrêt de [INGESTION.md](INGESTION.md) pour arrêter aussi **ingestion**, **prefect** et **prefect-db** en conservant leurs volumes. La commande de base ci-dessus ne décrit que le parcours API/PostGIS du présent bloc.

<a id="site-compile"></a>

## 9. Vérifier le site compilé

**Ce que cette étape fait :** elle transforme le code du web en fichiers préparés pour une exécution sans rechargement de développement. Ce travail s'appelle un build, ou compilation. Ce n'est pas encore un déploiement : les fichiers restent sur ton ordinateur.

Arrêter le serveur de développement pour libérer le port 3000. Depuis la racine :

```powershell
pnpm.cmd build
pnpm.cmd --filter @property-platform/web start
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

<a id="verifier-le-code"></a>

## 10. Vérifier le code avant de le partager

**Ce que cette étape fait :** elle cherche des erreurs avant de partager ou publier le code. Les vérifications ne remplacent pas un lancement du site et ne téléchargent pas de données immobilières. Les tests isolés utilisent un environnement de test, pas le volume PostgreSQL de développement.

### 10.1. Web et documentation

Avec les dépendances installées, depuis la racine :

```powershell
pnpm.cmd lint
pnpm.cmd typecheck
pnpm.cmd test:web
pnpm.cmd docs:check
pnpm.cmd contracts:check
```

Les commandes doivent terminer sans erreur. Le typage utilise le compilateur natif TypeScript 7.0.2 via un alias explicite. Next.js utilise le paquet de compatibilité TypeScript 6.0.2 (API embarquée 6.0.3) ; le générateur OpenAPI conserve l'API TypeScript 5.9.3 requise par ses peers. Voir [les versions et exceptions](TOOLCHAIN.md).

Elles contrôlent respectivement qualité/style, types, traductions, liens Markdown locaux et cohérence des types générés avec OpenAPI. Pour vérifier aussi le serveur compilé, suivre l'étape 9.

### 10.2. Python sur Windows — installation facultative

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
Remove-Item Env:PROPERTY_PLATFORM_TEST_POSTGIS -ErrorAction SilentlyContinue
uv run --project apps/api ruff check apps/api
uv run --project apps/api ruff format --check apps/api
uv run --project apps/api lint-imports --config apps/api/pyproject.toml
uv run --project apps/api pytest apps/api/tests -c apps/api/pyproject.toml
```

Ces retraits concernent seulement ce terminal. Les tests utilisent `property_platform.config.settings.testing` : SQLite en mémoire pour les besoins HTTP, et aucun stockage de données immobilières dans SQLite. Les modules métier GIS sont exclus de ce parcours. Les tests de protocole Onwani vérifient les réponses sans accès réseau ; les tests PostGIS sont ignorés volontairement. Des tests réussis et des tests ignorés sont donc attendus, sans figer ici leur nombre. Ce parcours ne valide ni les migrations GIS ni les transactions du catalogue : les tests d’intégration nécessitent PostgreSQL/PostGIS réel.

Le serveur GeoDjango et les tests PostGIS exécutés nativement nécessitent aussi GDAL/GEOS/PROJ sur l'hôte : Python seul ne suffit pas. Le parcours Docker évite leur installation sur Windows pour lancer l'API. La CI utilise ces bibliothèques et une vraie base PostGIS avec PROPERTY_PLATFORM_TEST_POSTGIS=1. L'image API locale est une image runtime sans pytest/Ruff ; ne pas tenter d'y exécuter les outils de développement.

### 10.3. Après une modification du contrat API

Un **contrat API** décrit les adresses disponibles et les formes des demandes/réponses. L'export OpenAPI produit cette description depuis le code Python ; contracts:generate en déduit les types TypeScript pour le web. Cela permet aux deux applications de s'accorder sur les données échangées, sans partager directement leurs tables de base.

Avec uv installé, dans le terminal des tests isolés et depuis la racine :

```powershell
uv run --project apps/api python -m property_platform.export_openapi --output packages/contracts/openapi.json
pnpm.cmd contracts:generate
pnpm.cmd contracts:check
git diff -- packages/contracts
```

Revoir puis enregistrer **OpenAPI, les types TypeScript et `packages/contracts/territories.json` ensemble**. L'export Python produit aussi ce snapshot de navigation publique à côté du fichier OpenAPI ; ses nombres de parcelles restent calculés par l'API. Ne modifier aucun de ces fichiers générés à la main. Le web connaît ces contrats, pas les tables Django. La CI vérifie les deux exports backend.

<a id="depannage"></a>

## 11. Résoudre les problèmes courants

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
| API inchangée après édition Python | Reconstruire l'image API comme à l'étape 8 |
| Admin refuse la connexion | Vérifier migrations, création du superutilisateur et configuration locale |
| Unknown command: 'import_onwani' | Vérifier la branche `codex/onwani-import`, puis reconstruire l'API ; suivre la section 6.1 |
| Table real_estate.parcel ou evidence.ingestion_run introuvable | Appliquer les migrations de la branche avec `migrate --noinput`, puis rafraîchir la connexion SQL |
| Import terminé avec le statut quarantined | Consulter le bilan et `evidence.quarantined_observation` comme en section 6.6 ; conserver les preuves et examiner l'anomalie avant toute correction |
| Import en échec | Consulter `evidence.ingestion_run.error` et les journaux API ; le catalogue précédent est conservé. Corriger la cause avant une nouvelle acquisition |
| CSS/JS absent en standalone | Reconstruire puis lancer node scripts/prepare-web-runtime.mjs, ou utiliser start qui fait cette préparation |
| Erreur certificat TLS à l'installation | Vérifier les certificats du système/réseau ; Node 26 permet $env:NODE_OPTIONS='--use-system-ca', uv accepte --system-certs sur sa commande réseau ; ne pas désactiver la vérification TLS |

### Comprendre le journal du 12 octobre : le web fonctionne, le build API échoue

Le journal fourni montre plusieurs opérations indépendantes :

- `pnpm.cmd install --frozen-lockfile` a réussi. Le message proposant pnpm 12.11.2 est une information ; aucune mise à jour d'outil n'est nécessaire pour afficher le thème.
- Le build de **api** échoue lorsque uv tente de récupérer `hatchling==1.32.4`, l'outil de construction du paquet Python. `invalid peer certificate: UnknownIssuer` signifie que ce programme ne peut pas valider l'autorité du certificat HTTPS présenté pour PyPI. Cela ne prouve pas que la version Hatchling est absente. La nouvelle image n'a pas été construite ; le conteneur déjà démarré est resté utilisable dans cette session.
- `migrate` affiche `No migrations to apply` : aucune migration en attente dans le code du conteneur courant. Cette commande ne répare ni le build ni un certificat.
- `pnpm.cmd dev:web` affiche `Ready` puis des réponses `200`, y compris pour les parcelles : le site sur **3000** et son accès à l'API fonctionnent.
- `Detected scroll-behavior: smooth` était un avertissement de navigation du web, corrigé avec l'attribut `data-scroll-behavior="smooth"` dans `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\[locale]\layout.tsx`, suivant [Next.js](https://nextjs.org/docs/messages/missing-data-scroll-behavior). Ce n'était pas un échec Docker.
- `Terminer le programme de commandes (O/N) ?` puis `ERR_PNPM_RECURSIVE_RUN_FIRST_FAIL` apparaît à l'interruption du serveur dans ce journal. Les réponses précédentes montrent qu'il a fonctionné avant son arrêt. Garder le terminal ouvert pour utiliser 3000 ; après Ctrl+C, répondre `O` si Windows demande confirmation, puis relancer `pnpm.cmd dev:web` pour reprendre. Si la même erreur apparaît sans interruption, lire les lignes précédentes pour sa cause réelle.

Le problème TLS reste distinct du disque plein, désormais résolu. uv peut utiliser les certificats système avec `--system-certs` ou `UV_SYSTEM_CERTS=true`, mais **dans un build Docker, le système est Linux, pas Windows**. Un certificat approuvé dans Windows n'est pas automatiquement ajouté à cette image. Le test précédent du magasin système Linux n'a pas suffi sur ce poste. Pour une correction durable, identifier la chaîne de certificats effectivement présentée et, si nécessaire, configurer une autorité authentifiée du réseau/proxy dans l'environnement de build. Voir [la documentation uv](https://docs.astral.sh/uv/concepts/authentication/certificates/). Les images locales déjà présentes permettent de continuer le développement web pendant ce diagnostic ; elles ne valident pas une reconstruction depuis zéro. Ne pas ajouter un certificat inconnu ni désactiver la vérification HTTPS.

### Cas particulier : cache natif SWC sous Windows

Si l'erreur cite ERR_SWC_NATIVE_CACHE, un propriétaire non fiable ou des permissions de remplacement, le chargeur refuse le cache Windows. Ce n'est pas une erreur de traduction.

Un cache privé peut être sélectionné s'il a déjà été créé et vérifié sous ce nom. Les caches extérieurs au dépôt ne sont pas renommés automatiquement avec les sources. Depuis **le PowerShell du compte Karim**, vérifier le dossier avant les commandes web :

```powershell
$env:SWC_NATIVE_BINDING_CACHE = Join-Path $env:USERPROFILE '.cache\property-platform-swc-private'
Test-Path -LiteralPath $env:SWC_NATIVE_BINDING_CACHE
pnpm.cmd dev:web
```

Test-Path doit répondre **True**. La variable est propre au terminal ; la définir aussi dans celui qui exécute typecheck/build si nécessaire. Ce cache extérieur au dépôt ne doit pas être committé ; il est accessible au compte Karim, pas nécessairement au compte sandbox d'un outil.

Sur une autre machine, le cache par défaut peut fonctionner sans configuration. En cas de problème, utiliser un répertoire privé dont les permissions et celles des parents sont compatibles avec SWC. Conserver les contrôles de sécurité et ne pas modifier les permissions de tout le profil. Voir [le fonctionnement officiel du cache SWC](https://github.com/swc-project/swc/blob/main/docs/native-addon-carriers.md).

<a id="production"></a>

## 12. Du lancement local à la production

Ce guide démarre les services sur ta machine ; il ne publie rien sur Internet. Les clés et identifiants Compose sont exclusivement pour le développement.

Un déploiement public nécessitera HTTPS/reverse proxy, secrets réels (DJANGO_SECRET_KEY, DATABASE_URL, DJANGO_ALLOWED_HOSTS), accès du personnel, statiques d'administration, sauvegardes et rôles SQL. Les migrations restent une étape explicite du déploiement. La CI vérifie sources, contrats, PostGIS et images : observer son résultat GitHub avant de considérer les contrôles distants comme réussis.

**Différence entre tests ciblés et validation complète :** quelques tests réussis ou un build réussi ne remplacent pas le workflow **Foundation checks** de `C:\Users\Karim\Repositories\property-platform\.github\workflows\ci.yml`. Celui-ci lance toute la suite API sur PostGIS, puis notamment `pnpm smoke:web` pour démarrer le site compilé et vérifier les quinze langues, les liens, les fichiers servis et les protections HTTP. La construction Docker du web lance aussi ce dernier contrôle avant de produire son image ; les dépendances de test Python restent hors de l'image API. Une évolution de navigation ou de champs publics doit adapter les attentes de ces contrôles, tout en gardant la liste stricte des champs autorisés et l'exclusion des données privées. Un courriel d'échec concerne le commit indiqué : après correction et push, consulter la nouvelle exécution, car l'ancienne conserve son résultat historique.

Pour poursuivre, lire [les frontières des modules](REPOSITORY.md) et [la revue de structure](STRUCTURE_REVIEW.md). Prochaine étape métier : définir le dossier pilote, puis développer le parcours carte → fiche → preuve → correction → publication.

<a id="saadiyat"></a>

## Ajouter ou actualiser Saadiyat

Saadiyat utilise la même base PostGIS et les mêmes couches de services. Le [guide complet Saadiyat](SAADIYAT.md) explique les sources, les fichiers avec leurs chemins complets et l’ordre des imports dans Prefect. La migration evidence.0013_osm_bootstrap_execution doit être appliquée avant de démarrer le nouveau runner ; elle autorise le nouveau type d’exécution et ne remplit aucune table immobilière. Les imports acquièrent ensuite les données réelles. Sur ce poste, cette migration et les premiers imports ont déjà été effectués.

Dans le site, choisir Abu Dhabi puis Saadiyat Island, ou ouvrir [la prévisualisation Saadiyat](http://localhost:3102/en/explore?territory=saadiyat-island). Revenir à Al Reem réinitialise les couches chargées. Les textes, scènes satellite et références de Reem ne sont pas utilisés comme données Saadiyat.


<a id="contexte-abu-dhabi"></a>

## Ajouter ou actualiser le contexte Abu Dhabi

Le [guide ABU_DHABI.md](ABU_DHABI.md), soit `C:\Users\Karim\Repositories\property-platform\docs\engineering\ABU_DHABI.md`, explique les six nouvelles ingestions, les six tables de preuves, les migrations et la consultation. Sur ce poste, ces données sont présentes ; aucune collecte n’est nécessaire pour ouvrir le site. Elles incluent ventes ADREC de l’émirat, limites Onwani, santé, Charter schools, bus et indicateurs SCAD. Des calendriers dominicaux actualisent les flux validés ; ADEK utilise un document conservé et reste sans actualisation automatique après son refus HTTP 403.

Ouvrir [la vue Abu Dhabi](http://localhost:3102/en/explore?territory=abu-dhabi), ou l’onglet Neighbourhood sur les îles. Ce panneau indique sa portée **tout l’émirat** ; les anciennes cartes de parcelles restent celles de Reem et Saadiyat. Le tableau d’audit du guide indique quelles dates sont connues, approximatives ou inconnues. DARI et plusieurs autres pistes n’ont pas de connecteur qualifié ouvert ; leurs limitations restent explicites.
