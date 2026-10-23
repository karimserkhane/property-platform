# Reconstruction et contrôle des captures archivées

La tâche [A04](../tasks/A04.md) distingue deux opérations :

- **restore-check** restaure une sauvegarde SQL dans une base temporaire et vérifie
  sa fidélité à l'instantané sauvegardé ([BACKUPS.md](BACKUPS.md)).
- **rebuild-check** crée une base vide, applique les migrations et repasse les octets
  des sources dans les importateurs typés actuels. Il ne restaure aucune ligne du
  catalogue et ne contacte aucun site immobilier.

Le second contrôle peut échouer alors qu'une restauration réussit : un ancien format
de source peut ne plus être pris en charge, une capture peut manquer, ou une décision
ancienne peut ne pas figurer dans les registres versionnés. Un écart n'est jamais
masqué en recopiant les lignes attendues depuis la base de référence.

## Lancer le contrôle

Après fusion, reconstruire et recréer l'ingestion selon
[AGENT_WORKFLOW.md](AGENT_WORKFLOW.md#7-mettre-à-jour-la-prévisualisation-de-karim).
Le déploiement Prefect **rebuild-check**, flow **property-platform-rebuild-check**,
est manuel, sans calendrier. Il accepte seulement `actor` ; aucune adresse de base
ni nom de cible ne peut être choisi dans l'interface Prefect.

Lancement direct depuis le runner, avec le même environnement que son service :

```bash
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion exec ingestion python -c "from property_platform_ingestion.flows import rebuild_check; rebuild_check(actor='operator-check')"
```

Ne pas lancer un deuxième contrôle identique en parallèle (rien ne l'empêche
techniquement). Prévoir au moins quelques Go libres pendant le contrôle : les octets
dédupliqués des captures et une base de travail s'ajoutent à la base en service.
Les octets copiés sont supprimés à la fin du contrôle. Les originaux privés doivent être accessibles au même chemin que
dans le runner ; un conteneur de contrôle les monte **en lecture seule**.

Ordre du flow :

1. Ouvrir une transaction **REPEATABLE READ, READ ONLY** dans la base de référence.
   Relever les comptes exacts de toutes les tables possédées et l'inventaire des
   pipelines/triggers sur le même instantané que les captures exportées.
2. Écrire un paquet privé sous `BACKUP_DIR/rebuild-checks/<UUID Prefect>/` :
   `manifest.json`, octets sous `blobs/<SHA-256>`. Aucun dump SQL ni secret.
3. Créer une nouvelle base `rebuild_check_<UUID aléatoire>` depuis `template0`.
   Refuser une cible existante/non vide ; exécuter les migrations explicites.
4. Rejouer les acquisitions par dépendance : parcelles, comparaison AD-SDI,
   géographie/OSM, références, présentations, projets, catalogues, contexte/marché.
   L'ordre des exécutions originales est préservé dans chaque phase.
   Les importateurs revalident formats, identités, géométries et droits. Les projets
   sont découpés par URL enregistrée ; les relations sont réconciliées à la fin.
   Les dates de collecte restent celles des captures ; les heures d'ingestion et
   les journaux sont ceux de cette nouvelle exécution.
   Une référence historiquement indisponible reste indisponible : son HTTP d'origine
   est conservé, sans transformer ce rejeu attendu en nouvelle erreur de collecte.
5. Comparer chaque table, vérifier l'inventaire et écrire `report.json`.
   Un import échoué, un statut différent de l'exécution d'origine (`diverged_steps`,
   par exemple une acquisition acceptée à l'origine et mise en quarantaine au rejeu),
   une table non couverte ou un écart sur une table comparée exactement fait échouer
   le flow Prefect. Seule exception attendue : une référence indisponible à l'origine
   (`failed`) rejouée comme indisponible (`replayed_unavailable`).
6. Supprimer uniquement la base créée par cette invocation, même si le rejeu échoue.
   Aucun `DROP ... FORCE`, aucune suppression de volume. `manifest.json` et
   `report.json` restent disponibles à l'opérateur, privés et ignorés par Git ; le
   dossier `blobs/` est supprimé (les octets restent dans la base et les sauvegardes
   A03). Un export interrompu supprime le dossier qu'il venait de créer.

Si une base `rebuild_check_*` subsiste (par exemple après l'arrêt forcé d'un worker),
la lister en lecture seule avec
`SELECT datname FROM pg_database WHERE datname LIKE 'rebuild_check_%';`, vérifier
qu'aucun contrôle n'est en cours dans Prefect, puis demander l'accord du propriétaire
avant de la supprimer : aucun outil ne supprime automatiquement une base qu'il n'a
pas créée dans la même invocation.

Le SHA-256 du manifeste est fixé après l'export ; chaque lecture de capture vérifie
sa taille et son empreinte. Une requête absente, différente ou une capture non
consommée fait échouer son import. Il n'existe aucun repli réseau pendant le rejeu.
Les contrôles ETag sur le serveur partagé sont à exécuter après le rejeu lourd :
le cache utilise encore un instantané PostgreSQL global et peut être invalidé par
ses transactions, même dans une autre base ([A08](../tasks/A08.md)).

## Lire le rapport

Toutes les tables de `real_estate` et `evidence` figurent avec compte attendu,
compte obtenu, résultat et politique. Une table inconnue reste une comparaison
exacte et fait également échouer l'inventaire ; elle n'entre pas dans une exception
automatique.

| Politique | Signification |
| --- | --- |
| `exact` | Le nombre de lignes doit être égal ; les différences et étapes échouées restent visibles. L'égalité des comptes ne prouve pas l'égalité des contenus. |
| `new_audit` | Sources, captures, exécutions, jonctions, journaux, audits de mutation et quarantaines sont recréés par les importateurs actuels ; leurs comptes sont affichés séparément. Ils ne remplacent pas les traces originales conservées par A03. |
| `backup` | État non rétabli par le rejeu des captures : conserver/restaurer A03 ou relancer son pipeline dédié selon le tableau suivant. |

`ok` concerne le périmètre du **rejeu des sources**, pas une restauration complète
des comptes utilisateurs, décisions et états dérivés. Le détail `omitted` indique
les captures sans adaptateur de rejeu, ainsi que les captures d'une fiche projet non
sélectionnées (URL répétée dans le même run ou retirée du registre) ; le rapport ne
prétend pas qu'elles ont été réimportées. Les anciens importateurs ne sont pas embarqués : une dérive du parseur
ou du registre est un écart à examiner, pas une preuve de perte dans la source.

## Ce qui exige une sauvegarde ou un autre pipeline

| État | Reprise |
| --- | --- |
| Exclusions et révocations, alias d'identité revus | Sauvegarde SQL A03 ; ne jamais inventer une décision opérateur à partir d'une proximité ou d'une absence. |
| Originaux privés et objets stockés, liaisons, autorisations de publication | Sauvegarde SQL et miroir `files/media/` A03 ; les pipelines de stockage vérifient les originaux, ils n'inventent pas les droits. |
| Graphe routier et fragments | Sauvegarde A03, ou pipeline `routing-osm-graph` puis reconstruction avec le worker Valhalla. Ce contrôle de sources n'appelle pas le moteur lourd. |
| Demandes et contours de marche | Sauvegarde A03 ; recalcul possible par `walking-areas` après reprise du graphe et de la file. |
| File des tuiles demandées mais non acquises | Sauvegarde A03 ou nouvelles demandes de consultation. Les versions réellement archivées sont rejouées et comparées. |
| Utilisateurs, sessions et identifiants Django ; base Prefect | Hors schémas métier. A03 sauvegarde la base applicative ; la configuration/secrets et les métadonnées Prefect ont leur propre politique de reprise. |
| Fond Esri diffusé en ligne | Aucune archive permanente qualifiée ; exception explicite dans [DATA_HISTORY.md](DATA_HISTORY.md). |

Pour une reprise après incident, restaurer dans une **nouvelle** base, vérifier et
faire valider la bascule. Ne jamais exécuter un outil de réparation directement sur
la base en service. Une copie du paquet de captures, du miroir privé, des registres
versionnés et du commit des extracteurs est nécessaire pour un rejeu hors ligne ;
la disponibilité actuelle des sites d'origine ne suffit pas.

## Premier contrôle réel — 23 octobre 2026

Run Prefect `451f59df-47c3-41b8-930f-f65d59331c18`, instantané à
`2026-10-23T13:26:26.478410+00:00` : 1 279 étapes, 50 tables comparées,
409 versions de tuiles. Les 183 projets, 60 promoteurs, 1 409 bâtiments, 1 043 rues,
les données ADREC, le contexte officiel et les tuiles sont retrouvés en effectifs.
Le flow échoue comme prévu sur les différences, et sa base temporaire est supprimée.

**La reconstruction complète n'est pas démontrée.** Les divergences sont suivies
dans [A11](../tasks/A11.md) (anciens protocoles Onwani/OSM et dépendances) et
[A12](../tasks/A12.md) (versions des interprétations de fiches/catalogues).
Le contrôle ne corrige ni n'efface les lignes en service. Les sauvegardes A03 restent
nécessaires ; un compte égal ne garantit pas à lui seul l'identité des valeurs.

Après correction de l'ordre des dépendances, de la sélection des cibles de
présentation et des références indisponibles, dernier run
`2f579f83-9747-4629-b471-bca02dabb7ef`, instantané à
`2026-10-23T14:03:23.446517+00:00` : **1 281 étapes, cinq acquisitions refusées,
onze tables en écart**. Les 18 présentations, six médias associés et 230 références
sont maintenant retrouvés exactement, en plus des familles déjà citées. A11/A12
restent nécessaires pour démontrer la reconstruction complète.
