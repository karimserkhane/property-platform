# Revue UI/UX immobilière — 21 octobre 2026

Cette passe complète la [revue du code et des données](PLATFORM_REVIEW_20261021.md). Elle examine les parcours chercher un projet → comprendre le dossier → trouver les plans → explorer son quartier, avec les exigences de lisibilité d'un acheteur. Il s'agit d'une revue interne du produit et du code, pas d'une validation par un promoteur ou un panel de clients.

## Défauts corrigés

| Priorité | Défaut observé | Correction |
| --- | --- | --- |
| P1 | Sur téléphone, la navigation globale disparaissait : annuaire, carte et marché devenaient difficiles à retrouver. | Menu mobile natif commun, page active, fermeture par Échap avec retour du focus, clic extérieur et sortie clavier. |
| P1 | Une grande photo d'ambiance et un faux diaporama de deux photos occupaient le premier écran du dossier avant ses faits. | Identité, promoteur, localisation qualifiée, livraison annoncée et total du programme en tête ; photo bornée, ambiance unique explicitement identifiée. Une galerie exige plusieurs photographies de projet autorisées. |
| P1 | Les plans étaient étiquetés « Document » et placés après la carte sur mobile. Leur section disparaissait si les références manquaient. | Accès direct et section après les typologies ; plans explicitement qualifiés séparés des brochures et fiches, état « non documenté » visible. |
| P1 | Une image de plan ou de brochure approuvée pouvait être choisie comme photo de couverture. | Le rôle documentaire exclut ces images de la galerie photographique, même avec un MIME image approuvé. |
| P1 | Dans la carte de quartier en 3D, un toit générique pouvait prendre le clic d'un repère projet. | Les repères projets ont priorité sur les volumes mondiaux, comme dans Explore. |
| P2 | Plusieurs cartes répétaient un même type de logement, avec ou sans nombre de chambres, repoussant les plans. | Une carte par type, chambres explicitement documentées et triées ; toutes les assertions originales et sources restent accessibles dans les preuves. Aucun croisement de types et chambres indépendants. |
| P2 | Le bouton de recherche long écrasait le champ mobile ; le total ne distinguait pas les 48 fiches visibles. | Libellé d'envoi court, en-tête compact, plage affichée sur total, pagination avant et après la liste. |
| P2 | Changer de zone effaçait la recherche ; une ancienne page hors limites semblait vide malgré des résultats. | URL commune conservant la requête et réinitialisant le décalage ; redirection vers la dernière page disponible après réduction des résultats. |
| P2 | L'action pour ouvrir le dossier était après toutes les typologies dans la petite fiche de carte. | Action directement sous le nom et le promoteur ; aperçu limité à trois types, variantes détaillées dans le dossier. |
| P2 | Certaines erreurs de sélection et de carte de quartier n'offraient aucun moyen de réessayer. | Nouvelle tentative explicite, annulation des anciennes lectures, nettoyage de la carte et masquage des outils sur une carte en échec. |
| P2 | La carte du dossier ne signalait une position absente qu'après son activation et ne qualifiait pas les points issus d'agences. | Information visible avant chargement, même qualification que la fiche courte ; aucune épingle inventée. |

Les prix, disponibilités, charges et modalités de paiement non documentés restent visibles comme manquants. Une livraison annoncée passée ne signifie jamais « livré ». Les monogrammes et photographies d'ambiance ne constituent pas des preuves sur le bâtiment. Les références PDF externes restent chez leur éditeur sans intégration ou copie automatique.

## Qualité du code

- `components/site-navigation.tsx` possède la navigation commune ; un seul jeu de liens traduit sert aux deux présentations. Le menu conserve la sémantique d'une navigation, sans faux rôle ARIA de menu applicatif.
- `projects/directory-navigation.ts` possède la taille de page, les liens et la reprise après réduction du catalogue. L'annuaire est rendu sur le serveur ; son formulaire n'exige plus d'état React client.
- `projects/presentation.ts` possède le regroupement réversible des typologies et la sélection de médias tenant compte des droits et rôles.
- `documents.tsx`, `media-card.tsx` et `evidence.tsx` séparent documents, livraison média et preuves du dossier. `directory.module.css` et `dossier.module.css` isolent les compositions ; les anciens styles d'annuaire et de couverture inutilisés sont retirés. Une vérification des huit importeurs ne trouve aucune classe utilisée absente de la feuille commune.
- Les nouveaux messages sont présents dans les seize langues. Aucune dépendance, migration, assertion source ou règle d'ingestion n'est ajoutée par cette passe.

## Vérification et limites

Validation : 85 tests web réussis, Biome sur 160 fichiers, TypeScript et compilation Docker avec contrôles HTTP standalone des seize langues ; liens locaux de 46 documents Markdown valides. La vérification navigateur couvre le dossier The District et son accès direct au plan, un dossier sans plans ni point vérifié (Global Gate), l'annuaire, recherche « Grove » et filtre Saadiyat, passage en arabe conservant les paramètres, ancienne URL de résultats hors limites, menu mobile et fermeture par Échap/clic extérieur/sortie clavier. Le résumé cartographique garde The District sélectionné après « Localiser ». Une parcelle inexistante présente une nouvelle tentative qui relance la lecture. Aucune erreur console sur le parcours normal observé.

Largeurs vérifiées : 320 et 390 pixels sur mobile simulé, 1440 pixels sur ordinateur, plus largeur normale du panneau. Pas de débordement horizontal observé sur ces parcours, y compris l'annuaire arabe. La carte du quartier et ses états de reprise sont aussi contrôlés dans le code ; une panne réelle de WebGL n'a pas été provoquée. Cette passe ne constitue pas une certification WCAG, une épreuve avec lecteur d'écran ni un test sur téléphone physique. Les tests API/PostGIS et ingestion ne sont pas relancés pour cette modification de présentation sans changement de leurs sources ou contrats.

Le web a été reconstruit dans l'aperçu privé existant ; l'accès reste réservé au réseau Tailscale. [Annuaire](https://property-platform-preview.taila64c9f.ts.net/fr/projects) · [Exemple de dossier et plans](https://property-platform-preview.taila64c9f.ts.net/fr/projects/the-district#project-documents).

Les priorités métier restantes sont la hiérarchie programme/phase/tour, les coordonnées justifiées, les plans et médias réellement disponibles et publiables, puis les unités, prix et conditions à jour avec leurs preuves. La présentation ne comble pas ces absences avec des données fictives. Une comparaison de projets et des filtres de budget demandent d'abord ces données fiables. Les [limites du catalogue](PROJECT_CATALOGUE.md) restent applicables.

## Correctif après captures mobiles : preuves et équipements

**Cette première correction ciblée est remplacée par [l’audit complet des 174 fiches](PROJECT_DISPLAY_AUDIT_20261021.md). Le parcours public ne présente plus aucun extrait ou volet technique ; les preuves exactes restent dans la base et l’API.**

Les captures de Radiant Bay et A1LA ont révélé un défaut non repéré lors du premier parcours : ouvrir une preuve de typologie affichait plusieurs fois le même fragment JSON et les chemins techniques PSI. Les équipements gardaient aussi leurs libellés anglais dans l'interface française.

`presentation.ts` déduplique maintenant les citations identiques d'une même capture, sans regrouper des versions, sources, pointeurs ou extraits différents. `evidence.tsx` présente le lien source et sa date de consultation ; les citations rédigées restent dans leur langue d'origine. Les reçus JSON et pointeurs sont réservés à un sous-volet technique fermé, avec leur contenu exact. Les données et captures historiques restent intactes. Les équipements connus utilisent un libellé d'interface traduit dans les seize langues à partir de leur code existant ; le texte original demeure dans la preuve. Un équipement inconnu conserve son libellé original.

Sans association explicite entre chambres et type de bien, la fiche indique « Nombre de chambres non précisé pour ce type de logement ». Elle ne répartit pas artificiellement une liste commune entre appartements et duplex. Cette passe ne corrige pas une ambiguïté de la source en créant des combinaisons.

Les trois tests supplémentaires vérifient les citations communes aux variantes de chambres, la conservation des captures distinctes, la séparation reçus structurés/prose et la sélection sûre des libellés d'équipements. Total : 88 tests web réussis et Biome propre. Aucun changement d'API, de contrat, de modèle ou de pipeline.

Validation du correctif : compilation Docker, typage et contrôles standalone dans les seize langues réussis. Radiant Bay et A1LA vérifiés sur mobile simulé en français ; une seule citation PSI pour les quatre chambres de Radiant Bay, reçus techniques fermés puis ouverts explicitement, équipements traduits et répartitions non précisées conservées. Vérification arabe à 320 pixels : source et date lisibles sans débordement, aucune erreur console observée. Version déployée sur le même aperçu privé Tailscale.
