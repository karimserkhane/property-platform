# Identité technique et marque affichée

`property-platform` est l'identité technique durable du dépôt. Le nom commercial est une configuration de présentation publique, indépendante de la base, des imports et de Docker.

## Changer le nom du site

1. Dans PyCharm, ouvrir `C:\Users\Karim\Repositories\property-platform\packages\branding\src\brand.ts`.
2. Modifier uniquement `displayName`, actuellement `Property Platform`, puis enregistrer.
3. En développement avec `pnpm.cmd dev:web`, actualiser le navigateur. Pour le site compilé Docker, reconstruire depuis `C:\Users\Karim\Repositories\property-platform` :

```powershell
docker compose -f infra/local/compose.yaml --profile web-preview up -d --build web
```

Cette seule valeur alimente le titre des pages, le nom accessible et visible de l'en-tête, la section de découverte, le pied de page et la signature des exports PNG. Elle reste une marque propre, identique dans les quinze langues ; les descriptions et autres textes de l'interface restent dans `apps/web/messages/<langue>.json`. Les noms originaux des sources et des lieux conservent leur sens propre.

Les pages sont précompilées : changer la marque d'une version compilée exige une reconstruction. Aucune lecture de base, requête réseau ou variable de secret n'est nécessaire pour afficher le nom. Une future application mobile pourra consommer le même paquet `@property-platform/branding` ; son rendu natif de logo devra être adapté à ses assets.

## Changer le logo et le thème

- Le symbole neutre par défaut est une grille de parcelles dans `C:\Users\Karim\Repositories\property-platform\apps\web\public\brand\mark.svg`. Remplacer ce SVG pour changer le symbole. Il sert aussi d'icône d'onglet.
- Pour utiliser un autre fichier local, changer `webMarkPath` dans `brand.ts`, avec un chemin commençant par `/brand/`, et placer le fichier correspondant dans `apps/web/public/brand/`. Le composant `BrandMark` utilise un masque monochrome : employer un SVG avec un fond transparent. Un logo multicolore nécessitera un rendu d'image adapté dans ce composant.
- Les couleurs communes et variables `--control-*` sont dans `C:\Users\Karim\Repositories\property-platform\apps\web\src\app\globals.css`. Le traitement des photos et boutons d'accueil reste dans `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\home.module.css`, décrit dans [VISUAL_DESIGN.md](VISUAL_DESIGN.md).

Ce paquet contient seulement de la présentation publique. Aucun mot de passe, fournisseur, identifiant de source, territoire de collecte, permission ou nom de schéma n'y entre. Les clients dépendent de `branding` ; ce paquet ne dépend ni du web, ni de Django, ni des contrats métier.

## Ce qui reste stable et ce qui se configure

| Élément | Règle |
|---|---|
| Nom et symbole visibles | Configurables avec le paquet de marque et les assets web |
| Textes et langues | Dictionnaires d'interface et registre des locales |
| Photos et crédits | Configuration de galerie et manifeste des médias |
| Connexion API et secrets | Variables propres à l'environnement ; aucun secret dans `branding` |
| Identités techniques | `property-platform`, `property_platform`, `@property-platform/*`, `PROPERTY_PLATFORM_*` ; conservées lors d'un changement commercial |
| Schémas SQL | `real_estate`, `evidence`, `public` ; noms métier stables, indépendants de la marque |
| Labels Django | `catalog`, `evidence`, `publication` ; préservent migrations et types de contenus existants |
| Territoires, données et fournisseurs | Paramètres métier et preuves ; changer un nom commercial ne modifie pas la couverture réelle d'Al Reem |

Les noms des études produit et architecture ont aussi été rendus génériques, avec mise à jour de leurs liens. Les migrations Django déjà appliquées n'ont pas été réécrites. Le changement technique ne crée pas une deuxième identité pour les biens et ne réécrit pas les captures originales.

## Reprendre une ancienne base locale sous le nouveau nom

Cette opération est distincte de `manage.py migrate`, qui applique les évolutions des tables. Le script `C:\Users\Karim\Repositories\property-platform\scripts\migrate-local-identity.mjs` prépare une sauvegarde PostgreSQL, démarre une base cible neuve et vérifie les effectifs et empreintes du contenu de toutes les tables de `public`, `real_estate` et `evidence` après restauration. Il n'écrase jamais un environnement ou un volume cible préexistant. Il conserve les anciens conteneurs et leur volume arrêtés pour récupération.

Pour une installation qui utilise encore les anciens noms, depuis la racine et avec Docker Desktop démarré, exécuter **une seule fois**, sans import concurrent :

```powershell
node scripts/migrate-local-identity.mjs --source-container liwa-local-db-1 --source-database liwa --source-role liwa
```

Les anciens noms dans cette commande servent uniquement à identifier l'installation à reprendre. Le script accepte aussi d'autres identités source explicites ; il n'introduit pas de dépendance de l'application à une ancienne marque. Les sauvegardes et rapports vont dans `.cache/backups/`, exclu de Git. En cas d'échec, il arrête la nouvelle base et redémarre les anciens services. Ne pas relancer sur une cible déjà créée : examiner le rapport et l'installation avant toute reprise.

Après réussite, construire les nouveaux programmes, puis vérifier leurs migrations :

```powershell
docker compose -f infra/local/compose.yaml --profile web-preview up -d --build web
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
```

La base active devient `property_platform`, le rôle de développement `property_platform` et le volume `property-platform-local_postgres18-data`. La connexion dans PyCharm utilise `localhost:5432`, ces deux nouveaux noms et le mot de passe local `property-platform-local-only`. Le guide [DEVELOPMENT.md](DEVELOPMENT.md) donne les étapes ordinaires. Il n'est pas nécessaire de réimporter les données après une restauration vérifiée.

Cette reprise conserve les données locales ; elle ne constitue pas une procédure de production. La restauration `--no-owner --no-privileges` adapte les objets au rôle local cible. Les rôles et permissions de production devront suivre leur procédure dédiée. Le nom des ressources de récupération peut conserver l'ancienne identité ; elles ne sont plus utilisées par l'application active.

Références techniques : [paquets locaux dans Next.js](https://nextjs.org/docs/app/api-reference/config/next-config-js/transpilePackages), [pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html), [volumes Compose](https://docs.docker.com/reference/compose-file/volumes/).

## Vérification du changement — 12 octobre 2026

La reprise locale a comparé avec succès les 25 tables. Les 15 fichiers de migrations existants, y compris les fichiers d'initialisation des paquets, conservent leur contenu. Les 101 tests backend passent sur un serveur PostGIS temporaire séparé de la base active ; Ruff, Import Linter, les contrôles Django et la génération de contrats passent également.

Après reconstruction des services actifs, `manage.py migrate --plan` indique qu'aucune opération de migration n'est prévue. La reprise sous un nouveau nom ne nécessite donc pas de réappliquer les migrations déjà enregistrées. Les conteneurs et le réseau temporaires de validation ont été supprimés ; la base et le volume actifs ainsi que la source de récupération sont conservés.

Le site compilé a été contrôlé dans les quinze langues avec le nom par défaut, puis avec `Example & Brand` dans une image de validation distincte : titres et navigation reprennent la configuration et échappent correctement le caractère `&`. Cette valeur temporaire n'a pas été écrite dans le dépôt ou dans la base. La carte locale retrouve les 2 431 parcelles. Le rendu anglais et arabe a été vérifié sur une largeur de téléphone de 320 pixels, sans débordement horizontal.
