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

## Anciens protocoles d'acquisition

Une acquisition ancienne peut avoir envoyé d'autres requêtes que le connecteur actuel
(autres `outFields` Onwani, autre requête Overpass). Le rejeu ne répond jamais à la
requête actuelle avec les octets d'une autre requête : l'importateur réémet la
**requête historique enregistrée**, le run rejoué porte la version de ce protocole
(`connector_version`) et les observations gardent la version du **mappage actuel**
(`mapping_version`). Aucun champ absent de l'ancienne requête n'est ajouté.

Le registre `evidence/replay_protocols.py` liste uniquement les versions dont les
requêtes diffèrent, recopiées depuis les commits cités ([A11](../tasks/A11.md)) :

| Versions d'origine | Différence rejouée |
| --- | --- |
| `onwani-reem-v1` | 18 `outFields` (les champs d'usage détaillé et de planification arrivent en v2) |
| `reem-map-v1` à `reem-map-v3`, `district-map-v4` (couche `osm`) | Requête Overpass limitée aux équipements et loisirs **nommés**, sans commerces ni transports |

Une version absente du registre garde la requête actuelle : la comparaison stricte des
URL fait alors échouer l'étape, comme avant. Ajouter une version exige de citer le
commit du connecteur et un test PostGIS sur ses requêtes exactes.

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
| `identity` | Parcelles et zones administratives : les identités **actives** doivent être identiques (nombre et empreinte des couples espace de noms/identifiant source). Les lignes remplacées absentes du rejeu doivent correspondre exactement aux réparations revues de doublons (alias A03 avec `superseded_*`) ; l'importateur actuel résout ces enregistrements à l'import et ne recrée pas le doublon. Un manifeste plus ancien, sans ces statistiques, garde la comparaison `exact`. |
| `history` | Historique des lectures de fiches et de catalogues (`project_snapshot`, `project_typology`, `project_amenity`, `project_media`, `project_source_candidate`, liens révoqués de `project_identity_link`) : compte affiché et expliqué (`history_differences`, `interpretations`), **non bloquant**, parce que l'[état publié](#état-publié-a12) est comparé à sa place. Sans état publié dans le manifeste, ces tables restent `exact`. |

Chaque étape rejouée porte aussi, quand ils diffèrent de l'exécution d'origine, les
comptes d'observations écrites par cette étape (`rows.expected` / `rows.actual`) :
`map_observation` par cible (`street`, `building`, `place`, `administrative_area`) et
par action (`created`, `updated`, `unchanged`, `retired`), `parcel_observation` et
`quarantined_observation`. `row_differences` donne le nombre de ces étapes. C'est un
**diagnostic** qui situe l'acquisition à l'origine d'un écart de table ; il ne décide
pas de `ok` (les politiques de table ci-dessus le font). Un manifeste plus ancien,
sans `original_rows`, n'a pas ce détail.

**Divergences revues.** Le registre `REVIEWED_DIVERGENCES` (`rebuild_archive.py`)
liste, une par une, les exécutions dont le statut d'origine n'est pas reproductible
depuis le dépôt et qu'une exécution ultérieure des **mêmes octets** a déjà
interprétées autrement. Une entrée n'est acceptée que si tout concorde : identifiant
du run, statut d'origine et statut rejoué, empreintes des captures, aucune
observation en quarantaine au rejeu, et observations par cible (toutes actions
confondues) égales à celles de l'exécution ultérieure citée. L'étape porte alors
`reviewed_divergence` au lieu de `diverged_from` (`reviewed_divergences` les compte) ;
ses lignes mesurées sont reportées sur la table (`reviewed_delta`), qui reste
comparée exactement pour tout le reste. Une divergence non listée, une nouvelle
quarantaine ou un rejeu qui ne concorde pas échoue toujours.

| Run d'origine | Statut d'origine → rejoué | Même capture que | Raison |
| --- | --- | --- | --- |
| `d7b5f4bc-3390-4e62-85ef-90e765e842c0` | `quarantined` → `succeeded` | `29a909a9-b094-40e2-aeca-f25b86a950be` | Interprétation `reem-map-v1` non commitée (antérieure à `087241d`), remplacée une minute plus tard sur la même capture `06a6dedd…` |

`ok` concerne le périmètre du **rejeu des sources**, pas une restauration complète
des comptes utilisateurs, décisions et états dérivés. Le détail `omitted` indique
les captures sans adaptateur de rejeu, ainsi que les captures d'une fiche projet non
sélectionnées (URL répétée dans le même run ou retirée du registre) ; le rapport ne
prétend pas qu'elles ont été réimportées. Les anciens importateurs ne sont pas embarqués : une dérive du parseur
ou du registre est un écart à examiner, pas une preuve de perte dans la source.

## État publié (A12)

Décision du propriétaire du 24 octobre 2026 ([A12](../tasks/A12.md)) : le rejeu doit
reproduire **ce que le site publie** ; l'historique des lectures est une alerte.

- L'export relève, sur le même instantané que les captures, la fiche de chaque projet
  publié (`project_detail`) et les liens d'identité actifs (projet, cible, espace de
  noms, identifiant source, motif). Les identifiants de base (UUID), l'emplacement
  privé d'un média et l'heure d'ingestion sont retirés ; l'ordre des listes est
  ignoré, celui des coordonnées d'une géométrie conservé. Valeurs, sources (URL,
  empreinte, date de collecte), positions et hiérarchie sont comparées.
- Le rejeu recalcule le même état dans la base reconstruite (`rebuild_published.py`).
  Le rapport `published` liste chaque fiche différente avec ses chemins (`.summary`,
  `.typologies`…) ; `published_blocking` compte les différences bloquantes. Une fiche,
  une valeur, une source, une position ou un lien manquant fait échouer le contrôle.
  Rien n'est recopié de la base de référence vers la base reconstruite.
- Une différence n'est mise à part (`requires_backup`) que si une décision d'opérateur
  conservée par A03 l'explique, et seulement sur les champs qu'elle touche :
  révocation d'un lien (positions, liens), publication d'un média (médias),
  exclusion d'historique (toute la fiche).
- `interpretations` explique l'alerte d'historique : lectures et reçus distincts par
  version d'extracteur, lectures et identités distinctes des candidats de catalogue,
  à l'origine et au rejeu.
- **Lecture courante.** Une relecture des mêmes octets (même URL, empreinte et date de
  collecte) par une nouvelle version d'extracteur ou de registre remplace la lecture
  précédente pour la publication ; l'ancienne reste dans l'historique. Une collecte
  différente ne masque toujours pas un fait déjà observé.
- **Preuve d'une revue datée.** Une relation entre fiches (`reviewed_on`, `source_url`)
  et un lien d'identité daté du registre des fiches (mêmes clés, facultatives) citent la
  dernière capture HTTP 200 de leur page au plus tard à la fin du jour de revue (heure
  des Émirats), et non la capture lue au moment où le lien est créé : le rejeu, qui
  crée ces liens dès la première lecture, cite la même preuve. Un lien sans date garde
  la lecture qui l'a créé.
- **Identité d'interprétation.** Depuis la migration `0032`, chaque lecture garde
  `registry_sha256` (entrée de registre) et `extractor_sha256` (code d'extraction, fins
  de ligne normalisées), en plus de `extractor_version`. Les lectures antérieures les
  laissent vides.
- Après un changement d'extracteur ou de registre qui lit autrement des octets déjà
  archivés, la base en service publie encore l'ancienne lecture et le contrôle le
  signale. Relire alors les reçus conservés par l'import ordinaire (flow
  `property-platform-project-details`, `acquisition_mode=archive_all`), puis relancer
  le contrôle.

## Ce qui exige une sauvegarde ou un autre pipeline

| État | Reprise |
| --- | --- |
| Exclusions et révocations, alias d'identité revus | Sauvegarde SQL A03 ; ne jamais inventer une décision opérateur à partir d'une proximité ou d'une absence. |
| Lectures de fiches et de catalogues par d'anciennes versions d'extracteur ou de registre, recollectes identiques | Sauvegarde SQL A03 (décision du 24 octobre 2026). Les octets d'origine restent rejoués par le code actuel ; l'état publié est comparé. |
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
dans [A11](../tasks/A11.md), [A14](../tasks/A14.md) et [A15](../tasks/A15.md) (anciens protocoles Onwani/OSM, contrôle réel et dépendances) et
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

## Contrôle réel après A11 — 23 octobre 2026

Run Prefect `67566bed-e70d-4ff8-a7c8-dc0e53921958`, instantané à
`2026-10-23T18:38:44.041852+00:00`, code A11 déployé dans l'ingestion : 1 281 étapes,
**aucune étape refusée** ; les cinq acquisitions Onwani/OSM sont rejouées avec leur
protocole historique ([A14](../tasks/A14.md)).

- `parcel_observation` est maintenant exact (25 504). L'écart restant de 2 431
  parcelles (10 808 contre 8 377) correspond aux 2 431 doublons Reem créés par la
  version v2 d'Onwani avant la résolution d'identité à l'import, puis remplacés par
  une réparation revue (2 431 alias actifs avec `superseded_parcel`). Les identités
  actives de la base en service sont 8 377, comme le rejeu. Même cas pour 8 zones
  administratives (77 contre 69, 69 actives). La politique `identity` ci-dessus
  rend ce contrôle sémantique ; elle s'appliquera au prochain contrôle après fusion.
- `d7b5f4bc` diverge comme prévu : mis en quarantaine à l'origine (30 observations,
  1 093 éléments « géométrie ou métadonnées OSM invalides »), il est accepté au rejeu
  avec les mêmes octets que `29a909a9`. `map_observation` passe à 9 820 contre 8 400
  attendues (6 883 au contrôle précédent) et `place` à 2 005 contre 2 012 : à
  qualifier dans A14 (hypothèse non vérifiée : mappage actuel différent de celui
  d'origine ; les comptes par étape ne sont pas encore dans le rapport).
- Qualification de `d7b5f4bc` (24 octobre, lecture seule de la base en service) :
  `d7b5f4bc` (18:53 UTC), `29a909a9` (18:54) et `ece1a59f` (19:17, `reem-map-v2`)
  ont la **même capture** (`06a6dedd…`). À l'origine : `d7b5f4bc` crée 30 lieux et
  met 1 093 éléments en quarantaine ; `29a909a9` crée 601 rues, 188 bâtiments,
  137 lieux et retrouve les 30 lieux inchangés (956 observations) ; `ece1a59f` en
  retrouve 956 inchangées. Le premier commit qui contient `reem-map-v1` (`087241d`,
  12 octobre 01:41 UTC) est postérieur à ces runs : l'interprétation qui a refusé
  les 1 093 éléments était du code non commité, modifié entre les deux runs sous la
  même version. Elle n'est pas reproductible depuis le dépôt ; ce n'est pas une
  perte de source. Au rejeu, `d7b5f4bc` reçoit l'interprétation de `29a909a9`, ce qui
  explique au plus 926 des 1 420 observations en plus ; le reste et l'écart `place`
  seront situés par les comptes par étape du prochain contrôle. Cette divergence est
  inscrite au registre des divergences revues ci-dessus ; le prochain contrôle réel
  ([A15](../tasks/A15.md)) vérifiera qu'elle concorde avec `29a909a9`.
- Écarts inchangés des fiches/catalogues : voir [A12](../tasks/A12.md).
