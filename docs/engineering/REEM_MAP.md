# Atlas Al Reem : carte alimentée par PostgreSQL

État vérifié localement le 11 octobre 2026. Le HTML fourni sert de référence visuelle et de répertoire de liens à examiner. Ses contours, noms attribués aux parcelles, périmètres supposés et images intégrées ne sont pas importés comme données de référence.

## Couverture réellement collectée

| Couche | Base et source | Effectif actuel |
|---|---|---|
| Parcelles | `property_platform.real_estate.parcel`, service PLOT de DMT/Onwani | 2 431 géométries valides ; une identité source invalide reste en quarantaine |
| Île et secteurs | `property_platform.real_estate.administrative_area`, couches DMT/Onwani | 1 district + 26 secteurs |
| Rues | `property_platform.real_estate.street` | 64 objets officiels + 601 tronçons OSM ; ces tronçons ne représentent pas 665 rues distinctes |
| Empreintes de bâtiments | `property_platform.real_estate.building`, OpenStreetMap | 188 ; couverture communautaire partielle |
| Lieux et repères | `property_platform.real_estate.place` | 196 actifs : 167 OSM, 3 repères de promoteurs, 26 repères de courtiers |
| Pages de recherche | `property_platform.evidence.research_reference` | 110 URL avec capture conservée, dont une réponse HTTP non disponible ; trois autres collectes ont échoué avant capture |
| Aperçus satellite | `property_platform.evidence.imagery_scene` | Sentinel-2 du 29 juin et du 4 octobre 2026 |

Les effectifs changent avec les sources et les imports. Une page de recherche n'est pas un projet distinct : plusieurs fournisseurs peuvent décrire le même projet. Les positions restent séparées par fournisseur ; les contradictions ne sont pas fusionnées automatiquement. Les anciennes observations et un repère retiré restent dans l'historique.

## Priorité de sélection — 12 octobre 2026

Un clic choisit parmi les objets actuellement rendus sous le curseur : **bâtiment → parcelle réelle → repère → rue → périmètre de projet → secteur → île**. Le contour Onwani `RT4_TMP_PL2` est une parcelle de type `ProjectLimits`, distincte du secteur officiel RT4 ; sa grande surface pouvait auparavant prendre le clic avant les vraies parcelles. Le choix ne dépend plus du seul ordre visuel des couches.

Les secteurs et l'île utilisent une surface transparente sur leurs géométries officielles, activée avec la couche secteurs. [MapLibre](https://maplibre.org/maplibre-gl-js/docs/API/classes/Map/#queryrenderedfeatures) interroge les surfaces d'opacité nulle, mais pas les couches masquées ou hors de leur plage de zoom. Un bâtiment caché ou non disponible dans les données n'est donc pas inventé. La sélection d'un bâtiment ne certifie pas son rattachement cadastral ; aucune nouvelle relation ou mutation SQL n'est déduite de ce clic. Les choix explicites dans les listes restent inchangés. La règle et ses tests résident dans `apps/web/src/features/atlas/presentation.ts`, `parcel-map.tsx`, `map-style.ts` et `apps/web/tests/atlas.test.mjs`.

## Correspondance avec le HTML

| Fonction du HTML | Implémentation actuelle | Précision |
|---|---|---|
| Parcelles colorées et légende | Huit catégories, filtre par catégorie et usage original dans la fiche | Classification d'affichage `land-use-v2`, pas une nouvelle décision d'urbanisme |
| Île, secteurs, rues et noms | Couches activables, noms anglais/arabe disponibles, codes de parcelles au zoom rapproché | Les libellés se raréfient au petit zoom pour limiter les collisions |
| Lieux et bâtiments | Points nommés et empreintes OSM, recherche et sélection | Empreintes 2D ; hauteur/niveaux seulement lorsqu'ils sont déclarés dans OSM |
| Projets futurs et sources | Références promoteurs, courtiers, autorités, médias et forums ; repères déclarés lorsque l'extracteur est validé | Aucun rattachement commercial ou périmètre cadastral certifié n'est déduit d'un point |
| Fiche de parcelle | Surface calculée, usage, construction, planification, allocation, propriété, dates, champs permis/MEPS et lien DCR disponibles | Une case vide signifie information absente ; elle ne prouve pas l'absence d'un permis |
| Proximité | Lieux couverts par la géométrie ; rues à moins de 120 m du centroïde | Distance indicative calculée dans PostGIS en UTM 40N ; ce n'est pas un frontage certifié |
| Recherche et filtres | Codes, usages, noms localisés, secteurs, terrains temporaires ; listes rues/lieux/bâtiments | Noms de rues recherchés dans l'onglet rues ; les prix et appartements ne sont pas encore recherchables |
| Vues RT4, quartier, île | Boutons de cadrage et zoom sur un repère sélectionné | Les données restent celles de la base |
| Fond satellite | Esri World Imagery en ligne + deux aperçus Sentinel issus de la base | Dates Esri variables ; Sentinel source 10 m, recadrage et rééchantillonnage déclarés |
| Coordonnées et exports | Coordonnées du curseur, export CSV filtré et PNG avec légende/crédits | Les anciens repères Waze du HTML ne sont pas recopiés sans nouvelle acquisition |

Les 73 fiches commerciales et 56 hypothèses spatiales du HTML ne deviennent pas automatiquement des relations acceptées en base. Les pages utiles ont été relues ; les attributions restantes nécessitent une extraction propre au fournisseur ou une vérification documentaire. De même, tous les anciens liens de brochures/images ne sont pas téléchargés et publiés. Cette différence est explicite plutôt que cachée par des noms ou contours inventés.

## Sources et portée

- [Parcelles Onwani](https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/0), [districts](https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/1), [communautés](https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/2), [rues](https://onwani.abudhabi.ae/arcgis/rest/services/Onwani/UDM_AddressingLayers/MapServer/2). Le filtre communauté utilise **nom du district et identifiant** : l'identifiant 57 seul n'est pas unique à l'échelle du service.
- [OpenStreetMap](https://www.openstreetmap.org/copyright), collecté via une requête Overpass fixe, bornée et manuelle. L'édition OSM est une date de modification de l'objet communautaire, pas une date de construction. Un centroïde ou centre de boîte peut servir de repère lorsque la source ne fournit pas de point.
- [The District, source promoteur](https://reportagegroup.com/projects/residential-apartments/the-district/), pages de projets et de courtiers enregistrées dans `project_sources.json`. Les labels de ce registre sont des repères éditoriaux de découverte ; le titre réellement reçu est conservé séparément. La famille de source affichée n'est pas un score automatique de fiabilité.
- [Earth Search Sentinel-2](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a) : scènes `S2C_40RBN_20261004_0_L2A` et `S2C_40RBN_20260629_0_L2A`. Acquisition satellite en UTC conservée ; le pourcentage de nuages porte sur la tuile entière, pas sur Al Reem seulement. Les aperçus sont des dérivés, pas les rasters originaux.

Un extracteur de repère exige un format reconnu, un nom cohérent avec la page et un point couvert par le district officiel. Les coordonnées génériques d'une organisation, les noms contradictoires et plusieurs positions contradictoires dans une même page sont refusés. Une attribution ancienne invalidée par ce contrôle est désactivée avec observation `retired`, raison et révision ; elle n'est pas supprimée.

## De la collecte à l'écran

1. Les commandes Django collectent les sources fixes. La carte ouverte par un visiteur ne lance aucun scraping.
2. `evidence.capture` conserve réponse originale, URL, statut HTTP, SHA-256, début/fin de collecte, méthode d'acquisition et date d'ingestion. La publication reste inconnue lorsqu'elle n'est pas explicitement fournie.
3. Le collecteur contrôle schéma source, identités, exhaustivité, CRS et géométries. Chaque couche officielle est entièrement préparée avant sa transaction. Les objets OSM invalides sont isolés. Une collecte interrompue conserve la version précédemment matérialisée.
4. Les services propriétaires de `catalog` réconcilient les identités source et les géométries typées ; `evidence.map_observation` conserve valeurs observées, capture, empreinte incluant la géométrie, version de mapping, action, révision et avant/après.
5. `publication` assemble les lectures autorisées et l'API locale renvoie les contrats générés. Le web affiche ces réponses ; il ne connaît pas les tables SQL.

La première réponse OSM obtenue pendant cette session a été rejouée après l'indisponibilité du fournisseur. Son audit indique `manual_receipt_replay`, une date issue du fichier de réception local et un début inconnu ; aucun nouveau téléchargement n'est prétendu. Un retraitement de page déjà stockée utilise `stored_capture_reprocess`, conserve ses dates et relie la nouvelle capture à l'originale avec `parent_capture_id`. L'ingestion et le mapping ont leurs dates/versions propres.

L'absence d'un objet dans une acquisition ultérieure ne prouve pas une démolition ; les identités manquantes ne sont pas supprimées automatiquement. Leur dernière date de source reste visible.

## Code et exploitation

Voir [le guide de développement, section 6.8](DEVELOPMENT.md#couches-reem) pour les commandes et chemins complets. Le recadrage satellite s'exécute dans un environnement isolé, avec les dépendances de `scripts/imagery-requirements.txt`. Aucun Rasterio, NumPy ou traitement lourd n'est ajouté au runtime API/web.

Les deux petits PNG du pilote sont stockés dans `evidence.imagery_scene`, bornés à 768 pixels par dimension et 4 Mio par reçu. Ce stockage limité ne préjuge pas du futur domaine médias : grands originaux et dérivés iront dans un stockage objet avec métadonnées et droits de diffusion. La réponse locale ne livre que deux aperçus.

Les routes restent protégées par DEBUG + le flag aperçu. Le relais web limite chemins, paramètres, temps et taille (8 Mio). Géométries, données brutes, opérateurs et captures internes ne sont pas accessibles par une route d'écriture publique. Les lectures géographiques utilisent PostGIS ; l'accueil ne charge pas MapLibre.

Avant ouverture publique : projection approuvée, droits de diffusion par source, authentification/limitation de trafic, CSP complète et validation linguistique/accessibilité. Aucun tarif, avis, score IA ou volume 3D généré n'est présenté comme une donnée collectée par cette tranche.
