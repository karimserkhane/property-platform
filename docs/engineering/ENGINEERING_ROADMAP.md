# Feuille de route technique — performance, fiabilité et modularité

Document vivant ouvert le 23 octobre 2026 par Claude Code, à partir de mesures locales. Il complète la [revue de plateforme du 21 octobre](PLATFORM_REVIEW_20261021.md), centrée sur la qualité des données et le parcours utilisateur. Chaque chantier ci-dessous est livré par une pull request courte, testée et documentée ; mettre à jour ce document quand un chantier est terminé ou repriorisé.

## Principes retenus

- **Mesurer avant d'optimiser.** Une optimisation cite sa mesure avant/après dans sa PR. Les chiffres ci-dessous servent de référence.
- **Ne pas recalculer pour chaque visiteur ce qui ne change qu'à l'ingestion.** Les lectures lourdes sont mises en cache avec une invalidation liée à la version des données, jamais avec une durée arbitraire qui afficherait une source exclue.
- **Une seule implémentation par préoccupation transverse** : gardes d'accès, erreurs, compression, journaux, pagination. Une nouvelle route ou une nouvelle source les réutilise au lieu de les recopier.
- **Envoyer au navigateur seulement ce qu'il affiche** : données compressées, découpées par zone et par zoom, images servies comme fichiers cachables.
- **Tester au bon niveau** : fonctions pures en tests unitaires, requêtes et transactions sur PostGIS réel, parcours utilisateur dans un vrai navigateur.
- **Contrats stables** : une optimisation interne ne modifie pas le contrat OpenAPI ; un changement de contrat est explicite et régénéré.

## Mesures du 23 octobre 2026

Environnement local Docker, données réelles d'Al Reem, zone `54.39,24.48,54.42,24.51`, médiane de cinq appels directs à l'API.

| Lecture | Temps serveur | Taille JSON | Compressée (gzip) |
| --- | --- | --- | --- |
| `parcels` (1 000 parcelles) | 0,30 s | 1,04 Mo | 160 Ko |
| `map-context` (rues, bâtiments, lieux, zones) | 0,70 s, 41 requêtes SQL | 1,68 Mo | 216 Ko |
| `district-map` | 0,67 s | 478 Ko | 118 Ko |
| `market-map` | 0,82 s | 140 Ko | 41 Ko |
| `imagery` | 0,11 s | 857 Ko | 649 Ko |
| `projects` (48 fiches) | 0,09 s | 22 Ko | 5 Ko |

Autres constats :

- **Les relais `/api/atlas/*` du site renvoyaient ce JSON sans compression** : Next.js compresse les pages, pas les réponses des route handlers, et l'accès privé Tailscale n'ajoute pas de compression. Un téléphone téléchargeait donc 1 à 1,5 Mo à chaque déplacement de carte. Corrigé par le chantier 2.
- **JavaScript** : environ 500 Ko (165 Ko compressés) de socle React/Next.js par page ; MapLibre n'est chargé que sur les pages de carte. Le poids JavaScript n'est pas la priorité.
- **`district-map`** : la simplification des 216 contours est faite ligne par ligne en Python (GEOS), avec une lecture d'historique par ligne ; seules deux requêtes SQL sont lourdes.
- **`imagery`** : les images sont intégrées en base64 dans le JSON (857 Ko quasi incompressibles) au lieu d'être des fichiers cachables.
- **Base** : `evidence.capture` stocke 817 Mo de contenus bruts dans PostgreSQL pour 2 420 captures, ce qui alourdit chaque sauvegarde.

## Chantiers

| # | Chantier | Gain attendu | État |
| --- | --- | --- | --- |
| 1 | Journaux et trace complète des échecs ; gardes communes des routes API | Diagnostic des imports ; moins de code recopié | Fusionné (PR #1) |
| 2 | Compression brotli/gzip et relais partagé des lectures `/api/atlas/*` | 5 à 7 fois moins de données par affichage de carte | Fusionné (PR #2) |
| 3 | Tuiles vectorielles PostGIS (`ST_AsMVT`) pour parcelles et bâtiments | Carte fluide à l'échelle des sept émirats ; fin de la limite de 12 000 parcelles | Parcelles de l'explorateur : PR #3 ; bâtiments et index par zone à suivre |
| 4 | Cache des lectures lourdes avec `ETag` lié à la version des données (`evidence.row_revision`) | `district-map`, `market-map`, `map-context` instantanés en lecture répétée | PR #4 (instantané PostgreSQL) ; version par famille de tables à suivre |
| 5 | Simplification des contours en SQL et regroupement des requêtes de `map-context` | Temps serveur divisé avant même le cache | À faire |
| 6 | Images satellite servies comme fichiers cachables au lieu de base64 dans le JSON | −850 Ko sur la vue imagerie | À faire |
| 7 | Sauvegarde automatique PostgreSQL + stockage privé, avec test de restauration planifié | Reprise après perte de données | À faire |
| 8 | Tests de parcours navigateur (Playwright) : recherche, fiche, arabe RTL, mobile ; budgets de performance en CI | Régressions visibles avant fusion | À faire |
| 9 | Contenus bruts des captures vers le stockage objet, adressés par SHA-256 | Base et sauvegardes beaucoup plus légères | À faire |
| 10 | Découpage interne d'`evidence` (95 fichiers, 14 700 lignes) en sous-paquets : projets, cartes, sources, historique | Ajout de fonctionnalités sans module fourre-tout ; même application Django et mêmes migrations | À faire |
| 11 | Composants carte : état regroupé en hooks/reducers (`explorer.tsx` 20 états, `map-workbench.tsx` 18) | Fonctionnalités carte plus simples à ajouter et à tester | À faire |
| 12 | Chaîne d'approvisionnement : images et actions par digest, mises à jour automatisées, analyse de vulnérabilités | Builds reproductibles et sûrs | À faire |

Ordre proposé : 3 et 4 d'abord (passage à l'échelle et temps de réponse), puis 7 et 8 (filets de sécurité), puis les chantiers de structure. Le chantier 4 doit traiter un cas limite : deux transactions concurrentes peuvent valider dans le désordre, donc une version fondée sur le seul maximum de `row_revision` doit être complétée (par exemple par l'horizon des transactions en cours) pour ne jamais servir une donnée exclue.

## Tuiles vectorielles des parcelles — 23 octobre 2026

L'explorateur dessine les contours de parcelles depuis des tuiles vectorielles PostGIS au lieu de télécharger toutes les géométries en GeoJSON.

- `GET /api/v1/preview/parcel-tiles/{z}/{x}/{y}` (zooms 8 à 16, `territory` facultatif) renvoie une tuile Mapbox Vector Tile, couche `parcels`, avec la seule propriété `id`. Mêmes règles d'identité que `/parcels` : parcelles courantes (`superseded_by` nul) et espaces de noms du territoire.
- `GET /api/v1/preview/parcel-index` renvoie les mêmes lignes publiées que `/parcels`, sans géométrie, avec `bounds`, `label_point`, `area_m2` et `nearby_projects`. Les distances aux repères de projet (50 m au plus, 0 à l'intérieur) sont calculées dans PostGIS ; le navigateur applique les mêmes règles de choix qu'avant (identité de projet, ambiguïté sous 10 m).
- Côté carte, la catégorie et la visibilité de chaque parcelle sont posées en `feature-state` à partir de l'index : une tuile ne peut pas afficher une parcelle que l'index n'a pas publiée, ni une couleur différente. Les libellés viennent d'une petite source de points.
- La carte de quartier des fiches projet garde ses parcelles GeoJSON (zone réduite) ; le style partagé n'est pas modifié.

Mesures (vue « toute la zone » d'Abu Dhabi, réponses compressées) : une ligne d'index pèse environ 63 octets contre 135 avec sa géométrie ; une tuile vaut 37 Ko au zoom 14 et 175 Ko au zoom 10 à 12 pour toute l'île. Le gain actuel tient surtout au rendu (MapLibre ne découpe plus 10 000 polygones dans le navigateur) et au chargement progressif par zone ; il devient décisif à l'échelle nationale. Prochaines étapes : servir l'index par zone visible plutôt que pour tout le territoire, puis les bâtiments en tuiles.

## Cache des lectures et requêtes conditionnelles — 23 octobre 2026

`api/read_cache.py` met en cache les lectures `/preview` sans effet de bord (parcelles, index, tuiles, contexte, quartiers, marché, projets, références, imagerie) et répond aux requêtes conditionnelles.

- **Version des données** : `pg_current_snapshot()` (prochain identifiant de transaction et écritures en cours) est lu *avant* les données. Toute validation qui pourrait changer une lecture change cet instantané ; une réponse ou un ETag n'est donc jamais servi après un changement, exclusion de source comprise. Aucune durée arbitraire.
- **Validation d'abord** : pour une adresse jamais servie, l'instantané est relevé juste avant la première requête de données de la route ; une requête rejetée par la validation n'atteint toujours pas la base.
- **Mémoire bornée** : une entrée par adresse (la plus récente), 64 Mo au total, 8 Mo par réponse, éviction LRU. Les erreurs et les flux (médias) ne sont jamais mis en cache.
- **Navigateur** : les relais transmettent `If-None-Match`, renvoient `304` et `ETag` faible avec `Cache-Control: private, no-cache` ; sans ETag, la réponse reste `no-store`.

Mesures par le relais (réponses brotli) : `district-map` 0,7 s → 0,08 s en relecture et 0,03 s en revalidation `304` sans corps ; `market-map` 0,8 s → 0,05 s ; index et tuiles de parcelles 0,02 s en `304`. Limite actuelle : n'importe quelle écriture renouvelle la version. Les collectes planifiées chaque minute (file des fonds de carte, zones de marche) la font donc changer environ une fois par minute en local ; une version par famille de tables (`evidence.row_revision.table_name`) permettrait de garder le cache des lectures non concernées.

## Ajouter une fonctionnalité sans dégrader la structure

- **Nouvelle lecture HTTP** : route dans `apps/api/src/property_platform/api/` sur un routeur `/preview` existant ou enregistré dans `router.py` (gardes communes automatiques), service dans `publication`, contrat régénéré, relais web de trois lignes avec `relayPreview`.
- **Nouvelle source** : protocole et import dans `evidence`, échec enregistré avec `mark_failed`, collecteur dans `apps/ingestion`, propriétaire documenté dans [REPOSITORY.md](REPOSITORY.md), puis horaire désactivé par défaut.
- **Nouvelle zone ou nouvel émirat** : suivre [UAE_COVERAGE.md](UAE_COVERAGE.md) ; aucune règle propre à une île dans le code partagé.
- **Nouvelle couche de carte** : données servies par zone et par zoom (tuiles dès le chantier 3), libellés dans les seize langues ([INTERNATIONALIZATION.md](INTERNATIONALIZATION.md)).
