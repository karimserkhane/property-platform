# Revue critique de structure — 10 octobre 2026

## Verdict

La séparation applications / contrats / infrastructure / documentation est adaptée au monolithe modulaire. Aucun besoin établi de Turborepo, nouveau service ou bibliothèque partagée universelle. La revue a conduit aux corrections concrètes suivantes, sans changer le socle de stack.

| Point relevé | Correction |
|---|---|
| Documents de cadrage mélangés avec les points d'entrée du dépôt | Produit, architecture actuelle et archives séparés dans `docs`, index et références mis à jour |
| Interface française et textes en dur, incompatibles avec le nouveau besoin | Layout par langue, dictionnaires, next-intl, anglais par défaut et RTL |
| Multilingue risquant de se limiter à un bouton sans vérification | Tests de dictionnaires et contrôle HTTP de toutes les pages compilées, langue/sens de lecture et CSS |
| Liens documentaires susceptibles de casser après un déplacement | Contrôle des liens locaux dans les Markdown, lancé aussi en CI |
| Export OpenAPI couplé au nombre de parents du chemin source | Destination de l'artefact demandée explicitement par la CLI et la CI |
| Contrôles source sans validation des images fournies | Construction des deux images en CI ; contrôle Django dans l'image API avec ses bibliothèques GIS |
| Poussées successives pouvant gaspiller les minutes CI | Annulation des exécutions supersédées et délais maximum par job |
| Stockage pnpm configuré différemment de l'environnement local existant | Alignement du stockage local ignoré par Git ; dépendances toujours verrouillées |
| Échec reproductible de la copie standalone avec Turbopack sous Windows | Compilation de production explicitement avec Webpack, validée avec les 15 routes ; Turbopack reste disponible en développement |

## Ce qui reste volontairement progressif

Le dossier `components` contient un véritable composant transversal, le sélecteur de langue. Les futures fonctions carte/catalogue auront leurs dossiers `src/features/<fonction>` lorsqu'elles existent. Extraire une bibliothèque UI commune web/mobile avant de connaître leur intersection serait prématuré.

Les modules catalogue, preuves et publication représentent une direction de dépendance ; Import Linter contrôle les imports, pas chaque accès ORM indirect. Les services métier, leurs tests et les revues de migrations devront faire respecter la propriété des écritures. Le dossier pilote est nécessaire pour définir les premières tables typées.

Les contrats générés constituent une frontière API. La CLI d'export n'a pas à deviner un emplacement de monorepo lorsqu'elle est exécutée depuis un autre dossier ou paquet installé. Elle reçoit désormais `--output`, et son résultat reste contrôlé avec les types TypeScript.

Les images de base sont des tags de version, pas des digests immuables. Les bibliothèques applicatives sont verrouillées ; figer aussi les images/actions par digest et organiser leurs mises à jour devra accompagner la première release déployée. Ce dépôt ne revendique pas encore une chaîne de publication entièrement reproductible.

La CI PostGIS et les builds Docker sont configurés ; leur résultat distant doit être observé. Les vérifications HTTP locales et SQLite ne se substituent pas à ces contrôles. Protection de branche, revue obligatoire, stratégie de sauvegarde et environnement public ne sont pas activés par l'ajout d'un YAML.

La comparaison locale a isolé un échec `ENOENT` au moment de copier les dépendances React dans le standalone avec Turbopack ; la génération des pages elle-même réussissait. Le build Webpack a ensuite produit un serveur qui répond correctement pour les quinze langues. Ce choix concerne le compilateur de production, pas le modèle de données ni la vitesse de réponse du site. Une future mise à jour pourra réévaluer Turbopack avec ces mêmes contrôles. Le cache natif SWC de Windows a également nécessité un répertoire privé compatible avec ses règles de permissions ; aucune vérification de sécurité SWC n'a été désactivée.

## Prochaine étape structurante

Définir puis tester le modèle typé du dossier pilote : identité, relations, preuves contradictoires, corrections réversibles et publication. La langue de l'interface, celle d'une source et celle d'une traduction sont des attributs distincts ; une copie complète de chaque bien par langue serait une erreur de modèle.
