# Atlas Al Reem — validation finale du 12 octobre 2026

**Portée de ce compte rendu :** livraison locale précédente de l'atlas Reem. La modification ultérieure de navigation nationale est décrite dans [UAE_COVERAGE.md](UAE_COVERAGE.md), avec ses contrôles propres et la validation navigateur restant à terminer ; les vérifications ci-dessous ne doivent pas lui être attribuées automatiquement.

## Livré localement

L'exploration affiche les données de PostgreSQL/PostGIS : 2 431 parcelles, un district et 26 secteurs, 64 objets de rues officiels, 601 tronçons OSM, 188 empreintes de bâtiments et 196 lieux actifs. Parmi ces lieux, 29 sont des positions déclarées sur des pages de promoteurs ou de courtiers. Les 110 URL de recherche et les deux aperçus Sentinel-2 disposent de captures traçables. Les détails de couverture et les différences avec le HTML sont dans [REEM_MAP.md](REEM_MAP.md).

La carte comporte huit couleurs d'usage et une légende, des couches activables, les noms anglais/arabe disponibles, les codes au zoom rapproché, recherche, filtres, listes paginées, fiches sourcées, vues de cadrage, coordonnées du curseur et exports CSV/PNG. Les repères commerciaux restent des déclarations de leurs fournisseurs ; un point couvert par une parcelle produit un candidat spatial, pas une attribution acceptée. Les dates de publication inconnues restent inconnues.

L'accueil est précompilé dans quinze langues et ne charge pas le moteur cartographique. L'exploration charge MapLibre et son worker empaquetés avec Next.js. Les noms originaux des preuves sont conservés. Les lectures sont séparées par propriétaire puis assemblées dans `publication` ; OpenAPI et types TypeScript sont générés ensemble. Les migrations et imports nécessaires ont été appliqués à la base locale pendant cette livraison, avec sauvegarde préalable hors Git.

## Limites et contrôles

- Requête spatiale obligatoire, coordonnées finies et ordonnées, étendue maximale 0,2 degré par axe et limite de 3 000 objets par couche. Une troncature est indiquée à l'écran.
- Intersection et calculs métriques dans PostGIS ; délai SQL local à chaque transaction de lecture cartographique de 3 secondes. Aucun accès SQL depuis le web.
- Relais web : origine configurée côté serveur, chemins et paramètres fixes, absence de redirection amont, délai de 5 secondes et réponse limitée à 8 Mio. Aucun URL de collecte fourni par un visiteur.
- Captures brutes, opérateurs, quarantaine et données internes restent hors des réponses publiques. Les routes de l'exploration sont en lecture seule.
- Django refuse l'aperçu hors DEBUG, même avec son flag activé. Le web compilé refuse également par défaut ; l'opt-in du profil Docker sert seulement à la prévisualisation locale.
- Listes limitées à 40 éléments affichés par page. Les changements de sélection ne renvoient pas toutes les géométries au moteur. Les aperçus Sentinel sont chargés à l'activation du satellite.
- Fond Esri optionnel avec crédits et dates variables ; deux aperçus Sentinel datés issus de la base. Source Sentinel à 10 m, recadrage et rééchantillonnage déclarés. Aucun serveur de glyphes externe.
- Acquisition satellite dans un environnement Python isolé ; traitement raster absent des images API/web. Lectures HTTPS partielles bornées avec validation TLS maintenue.
- En-têtes contre iframe, MIME sniffing et accès caméra/micro/localisation ; CSP limitée à frame-ancestors, object-src et base-uri. Une CSP complète reste à préparer pour la publication.

## Vérifications exécutées

95 tests backend réussis sur une base PostGIS isolée : migrations aller/retour et propriétaires de schémas, refus en production, limites HTTP/spatiales, imports répétés, échecs de sources, géométries invalides, captures, repères contradictoires, candidats spatiaux ambigus et reçus satellite. Après ajustement de la classification d'affichage, 60 tests sans GIS réussis, cinq intégrations ignorées comme prévu. Ces contrôles sans GIS ne remplacent pas les tests PostGIS.

Cinq tests JavaScript réussis, dont cohérence des quinze langues, sécurité des cellules CSV, recherche Unicode et bornes des géométries multiparties. Ruff, Import Linter, TypeScript, Biome, contrats générés et liens documentaires contrôlés. L'artefact web autonome est vérifié sur quinze accueils et quinze explorations, avec refus des routes de données sans opt-in, des paramètres inconnus et des POST.

La validation navigateur couvre le rendu des couches et des libellés, une fiche de parcelle réelle, les sources et les vues satellite, le passage à l'arabe et un viewport de téléphone sans débordement horizontal. Elle ne certifie pas tous les appareils ni les lecteurs d'écran.

La lecture des parcelles représente environ 2 Mo de JSON non compressé pour l'île entière, auxquels s'ajoutent environ 1,1 Mo de contexte cartographique et les références. C'est une observation locale de développement, pas un benchmark de production. Mesurer transfert compressé, rendu et latence avec concurrence avant extension ; géométries par viewport/zoom et tuiles vectorielles restent des évolutions à déclencher selon ces mesures.

La compilation native Windows de l'agent avait échoué sur les permissions du cache SWC. La variante Docker du [guide de développement](DEVELOPMENT.md) permet la validation sans désactiver de protection. L'image conserve un cache de dépendances distinct du code applicatif.

## Avant un accès public

Valider droits de diffusion, projection approuvée, authentification, rôles d'exploitation, limitation de trafic, CSP complète, traductions et accessibilité. Ne pas activer DEBUG pour publier cet aperçu. Prix, unités, avis, exhaustivité des permis, volumes 3D et scores IA ne sont pas encore livrés. Les périmètres futurs et attributions commerciales du HTML ne sont pas recopiés sans vérification documentaire.
