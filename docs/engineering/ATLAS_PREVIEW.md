# Première tranche de l'atlas — validation du 11 octobre 2026

## Livré localement

Accueil précompilé dans quinze langues, exploration MapLibre, recherche par début de référence, liste paginée et fiche liée à la provenance. Les géométries viennent de l'import Onwani existant ; aucun bien, prix ou avis fictif n'a été ajouté. Le panneau d'accueil est une couverture typographique, pas une fausse carte ou une photographie générée. La carte réelle se trouve dans l'exploration.

Les lectures sont séparées par propriétaire et assemblées dans publication ; OpenAPI et types TypeScript sont générés ensemble. Aucune migration ni modification des parcelles locales n'est nécessaire pour cette tranche. Le mode aperçu local reste distinct d'une publication approuvée.

## Limites et contrôles

- Requête spatiale obligatoire, coordonnées finies et ordonnées, étendue maximale 0,2 degré par axe, limite de 3 000 résultats et recherche de 80 caractères maximum.
- Intersection PostGIS ; délai SQL local à la transaction de 2 secondes. Aucun ORM ni accès à la base depuis le web.
- Relais web avec origine côté serveur, chemins fixes, absence de redirection amont, délai de 5 secondes et réponse limitée à 2 Mio. Les identifiants sont des UUID ; les valeurs de recherche restent paramétrées par l'ORM.
- Champs de provenance autorisés seulement ; captures, opérateurs, données brutes et quarantaine restent internes. Aucune route d'écriture ajoutée.
- Accès refusé par Django hors DEBUG, même avec le flag aperçu activé. Le web compilé refuse aussi par défaut, avec un opt-in réservé à la prévisualisation locale.
- Accueil sans JavaScript MapLibre ; moteur et worker empaquetés par Next.js chargés dans l'exploration. Liste limitée à 50 boutons de parcelles par page. Pas de tuiles ou d'images tierces.
- En-têtes contre l'inclusion en iframe, MIME sniffing, accès caméra/micro/localisation ; CSP limitée aux directives frame-ancestors, object-src et base-uri. Ce n'est pas une CSP complète contre les scripts injectés ni une certification de sécurité.

## Vérifications exécutées

63 tests backend réussis sur une base PostGIS isolée, dont refus en production, validation des entrées, intersection, recherche, troncature et provenance. 32 contrôles HTTP/protocole réussis sans GIS, avec intégrations ignorées comme prévu. Ruff, Import Linter, TypeScript, cohérence des traductions, contrat généré et liens documentaires contrôlés.

Image Docker web compilée et tests de l'artefact autonome réussis : quinze accueils et quinze explorations, langue/direction, ressources CSS, en-têtes, refus sans opt-in, paramètres non autorisés, identifiant invalide et POST refusé. Vérification navigateur : contours rendus, recherche d'une référence réelle, fiche sourcée et passage à l'arabe conservant la sélection. Vérification d'un viewport de téléphone : direction RTL, canvas présent et absence de débordement horizontal. Cela ne certifie pas tous les appareils ni les lecteurs d'écran.

L'API locale a renvoyé les 2 431 parcelles sans troncature : environ 1,8 Mo de JSON non compressé et 595 ms pour une première requête observée sur ce poste. C'est une mesure locale en développement, **pas un benchmark de production ni une mesure des Core Web Vitals**. La réponse complète n'est pas chargée par l'accueil. Mesurer transfert compressé, rendu de carte et latence avec concurrence avant extension ; géométries par viewport/zoom et tuiles vectorielles restent des évolutions à déclencher selon ces mesures.

La compilation native Windows de l'agent a échoué sur les permissions du cache SWC. Aucune protection n'a été désactivée ; la variante Docker du [guide de développement](DEVELOPMENT.md) a été validée. L'image utilise désormais un cache de dépendances distinct du code applicatif, pour éviter leur réinstallation à chaque modification.

## Avant un accès public

Valider les droits de diffusion, les critères d'approbation, les comptes/rôles d'exploitation, la limitation de trafic, une CSP complète compatible avec Next et le worker, les traductions et les tests d'accessibilité. Puis publier une projection contrôlée ; ne pas basculer DEBUG pour rendre cet aperçu accessible en production. Bâtiments, unités, prix, permis complets, médias, alertes et IA ne sont pas livrés par cette tranche.
