# Voir le site depuis un téléphone à distance

Le parcours par défaut donne un **accès privé de développement** au site Docker sur 3102. Il ne déploie pas la plateforme en production. Le PC, Docker Desktop et le site doivent rester allumés. En mode privé, le téléphone doit être connecté au réseau Tailscale autorisé ; `localhost:3102` sur le téléphone désigne le téléphone, pas le PC. Le mode sans VPN protégé par clé est décrit plus bas ; son ouverture Internet nécessite une autorisation explicite.

## Solution retenue

Le fichier `C:\Users\Karim\Repositories\property-platform\infra\local\compose.remote-preview.yaml` ajoute un connecteur facultatif **remote-preview**, avec l'image officielle Tailscale 1.104.1 fixée par empreinte. Il fonctionne en mode userspace : aucun pilote VPN Windows, mode Docker privilégié, périphérique TUN, route de sous-réseau ou sortie Internet ne lui est nécessaire.

Le connecteur partage l'espace réseau du conteneur web. **Tailscale Serve** relaie HTTPS vers `http://127.0.0.1:3000` dans cet espace. Prefect peut être ajouté séparément sur le port HTTPS privé 8443, selon la procédure ci-dessous. Les ports Windows PostgreSQL, Django et Prefect restent liés à `127.0.0.1`. Le mode privé reste le défaut : ne pas remplacer Serve par **Funnel** sans demande explicite d'accès sans VPN et sans protéger l'aperçu. Les permissions du réseau Tailscale déterminent quels appareils/membres peuvent accéder au site ; ce n'est pas une authentification applicative par utilisateur.

Le volume `property-platform-local_remote-preview-state` conserve l'identité privée du connecteur et sa configuration. Ne pas copier son contenu, des clés d'authentification ou des liens de connexion dans Git. Ce connecteur n'archive ni fichier métier ni donnée PostgreSQL.

## Préparer le connecteur

**Changement du 22 octobre :** Karim a demandé un lien sans VPN. Le web compilé
avec `PROPERTY_PLATFORM_ENABLE_LOCAL_PREVIEW=1` demande désormais une clé d'aperçu
HTTP Basic avant toute page, API ou ressource statique. Le proxy respecte les langues
existantes. Sans empreinte valide, il répond 503 ; sans bonne clé, 401 avec le dialogue
natif du navigateur. Aucun secret n'est accepté dans une URL. Les réponses protégées
sont privées/non stockables et interdites d'indexation. Ce contrôle temporaire ne
remplace ni des comptes utilisateurs ni l'authentification du personnel.

Compose charge automatiquement le fichier ignoré `.env.preview-access.local` à la
racine, contenant `PROPERTY_PLATFORM_PREVIEW_ACCESS_REQUIRED=1` et
`PROPERTY_PLATFORM_PREVIEW_ACCESS_DIGEST=<sha256 UTF-8 de utilisateur:clé>`. Générer
une clé aléatoire cryptographique d'au moins 120 bits ; cette empreinte n'est pas
adaptée à un mot de passe humain faible. Le clair reste dans le coffre opérateur,
jamais dans le dépôt, l'image ou les logs. Une recréation ordinaire du web réutilise
le fichier ; son absence ne désactive pas silencieusement la protection de recherche.
Le serveur de développement et les builds de validation sans aperçu ne changent pas.

Après compilation, vérifier 401 sans clé et 200 avec clé sur pages **et** API avant
d'activer un accès public. `tailscale funnel --bg --https=443 http://127.0.0.1:3000`
peut alors ouvrir uniquement le web protégé. L'activation initiale peut demander une
validation du propriétaire dans Tailscale. Ne pas ouvrir 8443 : Prefect reste privé.
Le PC et Docker doivent rester allumés. Une fois Funnel activé, un navigateur externe
sans VPN doit recevoir 401 et un certificat valide, puis accéder au site après saisie
de la clé. Pour revenir au privé, réappliquer la commande `tailscale serve` sur 443.

Dans PowerShell, exécuter les commandes séparément depuis la racine :

```powershell
Set-Location 'C:\Users\Karim\Repositories\property-platform'

docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview config --quiet

docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview up -d --no-build
```

La première commande valide les fichiers YAML sans publier leurs variables. La seconde démarre les services et images déjà préparés, sans reconstruire le code ni importer de données. Sur une nouvelle machine, préparer d'abord l'API, le site et la base comme dans [DEVELOPMENT.md](DEVELOPMENT.md). Les images PostgreSQL et web ne sont pas remplacées par Tailscale.

Pour autoriser un nouveau connecteur :

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview exec remote-preview tailscale --socket=/tmp/tailscaled.sock up --hostname=property-platform-preview --accept-dns=false --accept-routes=false --timeout=15s
```

Ouvrir le lien de connexion affiché sur son téléphone, se connecter à son compte Tailscale et autoriser **property-platform-preview**. Installer ensuite [Tailscale sur le téléphone](https://tailscale.com/download), utiliser le même réseau/compte et activer la connexion. Une création de compte, ses conditions et les éventuelles confirmations sont à effectuer par l'utilisateur. Aucun abonnement payant n'est souscrit par ces commandes.

Le délai de 15 secondes peut expirer pendant cette étape humaine : cela ne signifie pas que la demande de connexion a disparu. Contrôler l'état ; `NeedsLogin` attend encore l'autorisation, `Running` signifie que le connecteur est connecté :

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview exec remote-preview tailscale --socket=/tmp/tailscaled.sock status
```

## Activer le site privé

Une fois le connecteur autorisé :

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview exec remote-preview tailscale --socket=/tmp/tailscaled.sock serve --bg --https=443 http://127.0.0.1:3000

docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview exec remote-preview tailscale --socket=/tmp/tailscaled.sock serve status
```

Si Tailscale demande d'activer HTTPS/Serve, ouvrir son lien de configuration et faire la validation dans son compte. Conserver la vérification TLS ; ne pas contourner un avertissement de certificat. Le nom DNS du connecteur est utilisé pour le certificat HTTPS et peut apparaître dans les journaux publics de certificats ; cela ne rend pas le service accessible publiquement.

La commande affiche l'**adresse HTTPS réelle** attribuée au connecteur. Ouvrir cette adresse sur le téléphone avec `/fr/explore` pour la carte ou `/fr/projects` pour les fiches. Ne pas remplacer ce nom par un exemple inventé. Les requêtes du navigateur passent par le site ; l'API métier reste dans Docker.

`--bg` conserve la configuration Serve après le redémarrage du connecteur. Les règles d'accès et l'expiration des clés restent celles de Tailscale ; ne pas désactiver leur expiration pour contourner une reconnexion.

## Accéder à Prefect depuis le téléphone

Sur Docker Desktop, le connecteur peut joindre le port local de Prefect via `host.docker.internal:4200`. L’overlay ingestion configure l’API de son interface sur `/api`, pour conserver la même origine sur ordinateur et téléphone. Après une modification de ce réglage, recréer uniquement le serveur Prefect, en conservant sa base et le runner :

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion up -d --no-build --no-deps prefect

docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview exec remote-preview tailscale --socket=/tmp/tailscaled.sock serve --bg --https=8443 http://host.docker.internal:4200
```

Ouvrir l’adresse réelle affichée, avec `:8443/`, dans le navigateur du téléphone connecté à Tailscale. Cet accès permet aussi les actions d’exploitation de Prefect aux membres autorisés du réseau privé. Il ne publie pas le service sur Internet. Pour le fermer sans retirer l’accès au site :

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview exec remote-preview tailscale --socket=/tmp/tailscaled.sock serve --https=8443 off
```

## Mettre à jour ou arrêter

Après **recréation du conteneur web**, recréer aussi le connecteur pour qu'il rejoigne son nouvel espace réseau :

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview up -d --no-build --no-deps --force-recreate remote-preview
```

Pour fermer l'accès distant sans arrêter la base ou le site local :

```powershell
docker compose -f infra/local/compose.yaml -f infra/local/compose.remote-preview.yaml --profile web-preview --profile remote-preview stop remote-preview
```

Les volumes sont conservés. La suppression d'un appareil dans l'administration Tailscale révoque son identité ; arrêter un conteneur ne supprime pas l'appareil du compte. Aucune modification du routeur ni ouverture de port Internet n'est requise pour ce parcours.

## Validation sur ce poste

Le 16 octobre 2026, l'installation Windows native est restée en attente de confirmation administrateur et sa commande a été interrompue. Le connecteur Docker a été démarré à la place. L'utilisateur a autorisé l'appareil puis HTTPS/Serve ; le connecteur est `Running`. Serve relaie uniquement le port HTTPS 443 vers le web sur 3000, sans configuration Funnel. Les routes `/fr/explore`, `/fr/projects` et `/api/atlas/projects/reem-nine` ont répondu **200 à travers Tailscale, avec certificat TLS vérifié**. Le test physique d'affichage sur le téléphone reste à confirmer par l'utilisateur. L'adresse réelle est lisible avec `serve status` et n'est pas versionnée dans le dépôt. Ne pas lancer une seconde installation native pour compléter le parcours Docker ; si une ancienne demande Windows reste affichée, elle peut être annulée.

Sources : [Docker Tailscale](https://tailscale.com/docs/features/containers/docker), [réseau userspace](https://tailscale.com/docs/concepts/userspace-networking), [commande Serve](https://tailscale.com/docs/reference/tailscale-cli/serve).

**Protection vérifiée le 22 octobre :** les 96 tests web, la compilation Linux et
le smoke des 16 langues passent. Un conteneur de validation distinct, puis le web
effectif sur 3102, refusent pages/API/fichiers statiques sans clé ou avec une clé
incorrecte ; page, API et chunk compilé répondent 200 avec la bonne clé. Le secret
n'est pas inclus dans l'image. Après clarification du premier besoin localhost,
Karim a ensuite explicitement demandé la mise en ligne avec mot de passe.
`PROPERTY_PLATFORM_PREVIEW_ACCESS_REQUIRED=1` est réactivé et les contrôles HTTP
ont été rejoués avant l'ouverture Funnel. Seul le port HTTPS 443 est ouvert sur
Internet ; 8443 reste indiqué `tailnet only` pour Prefect. Aucun port DB/API métier
n'est publié. La mise à jour DNS publique peut prendre jusqu'à dix minutes selon
[la documentation Funnel](https://tailscale.com/docs/features/tailscale-funnel).

Le contrôle externe sans VPN a ensuite réussi après propagation DNS : 401 sur les
pages, API, images et fichiers statiques sans clé ou avec une clé erronée ; 200 sur
la page Explore, l'API des territoires et un vrai chunk compilé après authentification.
La vérification TLS reste active avec les autorités système approuvées. La
configuration Funnel confirme uniquement 443 dans `AllowFunnel` ; Prefect 8443 reste
privé. Les identifiants sont remis à Karim dans le chat, sans les versionner.
