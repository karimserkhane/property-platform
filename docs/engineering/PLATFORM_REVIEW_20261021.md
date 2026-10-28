# Revue critique de la plateforme — 21 octobre 2026

## Périmètre et conclusion

Revue croisant architecture/qualité technique, interprétation immobilière et parcours utilisateur. Lecture du code web/API/ingestion, vérifications dans une vraie base PostGIS de test et parcours navigateur français sur téléphone simulé, puis vérification du web compilé. Les données immobilières, preuves et identités existantes sont conservées.

Le socle de traçabilité est utile, mais la présentation pouvait encore faire croire à une source officielle ou à une position fiable sans preuve suffisante. La limitation de l'annuaire et les exclusions appliquées de façon incohérente étaient également des défauts concrets. Les corrections ci-dessous améliorent ces points ; elles ne constituent pas une certification exhaustive du code ou du marché.

## Défauts confirmés et corrections

| Priorité | Défaut et conséquence | Correction |
| --- | --- | --- |
| P1 | Une source entièrement exclue pouvait laisser sa fiche dans l'annuaire, alors que le dossier n'était plus publiable. Un lien cartographique indépendant pouvait encore exposer son identité. | Même sélection de snapshots acceptés pour le dossier, l'annuaire et les liens carte ; la date de dernière vérification vient d'une preuve acceptée. |
| P1 | Un média plus récent provenant d'une source exclue pouvait masquer une référence valide plus ancienne. L'exclusion ciblée `#media` n'était pas appliquée au rendu. | Choix du dernier média parmi les sources autorisées, respect de l'exclusion ciblée et maintien de l'historique. Le blocage explicite d'un média reste prioritaire ; il ne réactive pas une ancienne publication. |
| P1 | L'API plafonnait l'annuaire à 200 fiches et le web ne permettait pas d'atteindre les suivantes. La recherche portait uniquement sur les fiches chargées. | Paramètres bornés `q`, `offset`, `limit`, total explicite et ordre stable ; pages web de 48 fiches, recherche serveur, URL partageable conservant langue et île. Contrat HTTP régénéré. |
| P2 | Un lien actif suffisait à annoncer une localisation même si l'objet était inactif, supersédé, invalide ou hors des bornes du territoire. | Règles géométriques communes aux liens carte, dossier et annuaire avant limitation des résultats. |
| P2 | L'annuaire proposait « Ouvrir la page du projet » vers `/explore`, y compris sans position disponible. | Action de localisation correctement nommée et présente uniquement si une identité cartographique utilisable existe ; la fiche reste accessible dans tous les cas. |
| P1 | Sur Global Gate, « Voir la galerie officielle » ouvrait une page Square Yards. Une URL non corroborée pouvait également être présentée comme site du promoteur. | Statut officiel réservé à une preuve de promoteur/éditeur correspondant exactement à l'URL ; liens d'agence ou non corroborés libellés comme sources. Même règle dans couverture et dossier. |
| P2 | Une fiche projet sur la carte pouvait n'afficher que le quartier sans indiquer l'absence de point. Les positions d'agence avaient peu de contexte. | Message de position en attente dans la fiche carte ; indication de localisation non vérifiée pour les coordonnées issues d'agences. Aucune position inventée. |
| P2 | Les résumés commerciaux étaient présentés sans attribution immédiatement visible ; leur langue pouvait être celle d'une autre source prioritaire. | Source affichée sous le résumé, avec l'état historique existant ; `lang` vient de la source du résumé. |
| P2 | Deux registres JSON ne passaient pas le formatage demandé par la CI. | Formatage des registres, sans modification de leur contenu métier ni des reçus archivés. |

Le champ source `kind` exprime l'origine, pas un niveau universel de vérité. Un promoteur peut annoncer une date future ; une agence peut donner une position approximative ; un enregistrement ADREC peut désigner une entité légale différente de la marque commerciale. Les totaux annoncés/enregistrés et la précision des dates restent distincts.

## Vérifications reproductibles

Les régressions PostGIS couvrent notamment :

- Exclusion complète d'une source avec conservation des snapshots et retrait de l'annuaire/carte.
- Exclusion complète ou ciblée des médias, avec reprise d'une référence acceptée d'une autre source.
- Désactivation, révocation et géométrie hors territoire, sans action trompeuse de localisation.
- Jeu synthétique de 206 projets : accès aux fiches après la 200e, absence de doublons entre pages, recherche d'un résultat hors première page et contrôle des bornes HTTP.
- Conservation des garanties existantes de droits média, historique des faits, limites de requêtes et absence de corps bruts dans les lectures publiques.

Le test web supplémentaire vérifie qu'une agence, une URL sans preuve et une autre page du même hôte ne deviennent pas une source officielle. Les sources promoteur/éditeur exactes sont reconnues. Les textes existants des seize langues sont réutilisés pour les actions et états.

Le contrôle TypeScript Windows a rencontré une erreur de chargement du cache natif SWC dans le bac à sable. Aucune permission système n'a été assouplie : vérification des types, compilation Next.js et smoke des seize langues exécutés dans l'image Docker reproductible. Les résultats finaux et contrôles de la prévisualisation sont consignés à la fin de ce document.

## Priorités encore ouvertes

1. **Hiérarchie et alias des identités — P1.** Modéliser des relations typées, datées et réversibles entre programme, phase, résidence et tour. Auditer les candidats `gate-arc` / `the-arc` et les ensembles Gate, Radiant et Maysan avant d'en déduire un nombre de programmes indépendants ou un stock total. [Aldar présente Gate et Arc dans un ensemble commun](https://www.aldar.com/properties/en/uae/reem-island/gate) ; [Aldar Experiences décrit The Arc dans cet ensemble](https://www.aldarexperiences.com/gate-and-arc/). Cela motive une revue, pas une fusion automatique de toutes les fiches du quartier. Le total de 174 désigne des fiches nommées.
2. **Qualification des localisations — P1.** La présence d'un point d'agence reste distincte d'une emprise cadastrale examinée. Prioriser les fiches sans géométrie documentée, puis les coordonnées déclarées, en conservant méthode, source et révocation. Un centre d'île ou une parcelle voisine ne suffit pas.
3. **Reconstruction complète — P1.** La [preuve nocturne](PROJECT_CATALOGUE.md#preuve-finale-des-174-fiches) couvre le catalogue et son historique. Étendre le scénario de restauration aux couches géographiques, graphes, tuiles, médias et décisions opérateur, puis valider les sauvegardes des preuves privées. La réussite d'un contrôle d'inventaire ne démontre pas à elle seule cette restauration complète.
4. **Informations nécessaires à une décision d'achat — P2.** Ajouter progressivement, avec preuves propres au logement/programme, plans, unités/surfaces, charges, échéancier, état observé du chantier et date de livraison réellement constatée. Une date annoncée passée ne suffit pas à classer le projet « livré ». Ne pas substituer des prix d'annonces à des transactions ni additionner des populations de biens différentes pour promettre un rendement.
5. **Fraîcheur et exploitation — P2.** Définir par famille de source une fréquence de collecte, un seuil de revue et un état de fraîcheur affichable. Tester ensuite la perte d'une source et les alertes utiles, sans remplacer un fait documenté par une valeur vide. Surveiller latence des lectures cartographiques et taille des archives avec des données plus volumineuses.
6. **Validation utilisateur réelle — P2.** Les contrôles navigateur et le RTL simulé doivent être complétés par des parcours avec acheteur, agent et résident, sur téléphone réel, clavier et lecteur d'écran. Cette revue technique ne prétend pas être une consultation effective d'un panel externe.

Les relations métier et données absentes ne sont pas inventées pour fermer ces points. Les identités et preuves restent disponibles pour leur traitement séparé.

## Résultat final des contrôles

- **375 tests API réussis sur PostGIS**, suite complète après les corrections finales.
- **78 tests web réussis** ; contrôles Biome, Ruff, format Python et contrats générés réussis.
- Vérification TypeScript, compilation Next.js et smoke du runtime autonome réussis pour **16 langues dans Docker**.
- Trois contrats de frontières de dépendances respectés ; aucune migration manquante ; liens de 45 documents Markdown vérifiés.
- Images API, ingestion et web actualisées dans la prévisualisation privée. Serveur Prefect, base métier, métadonnées et volumes persistants conservés ; aucune collecte active interrompue lors du remplacement du runner.
- Annuaire réel : **174 fiches**, pages de 48, puis 48 pour la suivante, 30 pour la dernière à l'offset 144 ; aucun chevauchement entre les deux premières pages. Recherche `Global Gate` : un résultat au bon territoire et aucune fausse action de localisation.
- Navigateur : recherche française par formulaire, URL partageable, passage à l'arabe avec filtre conservé, `lang=ar`, `dir=rtl`, un résultat. Sur le viewport mobile contrôlé, largeur de contenu et largeur visible toutes deux de 375 px, sans débordement horizontal.
- La fiche carte Global Gate signale l'emplacement en attente de vérification. Dans le dossier, le résumé nomme Square Yards et la couverture affiche « Source » à la place d'une galerie officielle. Aucune erreur ou alerte console relevée sur ces parcours.
- API et runner sains après mise à jour ; accès HTTPS privés du site et de Prefect sur 8443 conservés.

Ces contrôles portent sur la prévisualisation et les scénarios décrits. Ils ne remplacent pas un benchmark en production, une certification d'accessibilité, une revue humaine des traductions ou la validation juridique/cadastrale des données.
