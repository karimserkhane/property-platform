# Accueil et première expérience de Liwa Atlas

Proposition de design du 11 octobre 2026, fondée sur le [benchmark](BENCHMARK_CONCURRENTIEL.md). C'est une direction à prototyper et tester, pas une interface déjà implémentée ni une garantie de conversion.

## Sommaire

- [Décision et état actuel](#décision-et-état-actuel)
- [Direction visuelle](#direction-visuelle)
- [Composition de l'accueil](#composition-de-laccueil)
- [Carte et fiche](#carte-et-fiche)
- [Mobile, langues et accessibilité](#mobile-langues-et-accessibilité)
- [Ordre de développement](#ordre-de-développement)
- [Critères de validation](#critères-de-validation)

## Décision et état actuel

**Concevoir l'accueil maintenant, développer d'abord un parcours complet carte → parcelle → source.** Une belle entrée a de la valeur lorsque le bouton principal ouvre une expérience utile. La proposition combine une présentation éditoriale sobre avec une carte comme preuve du produit.

Le site actuel est une page d'attente multilingue. Le socle comprend PostgreSQL/PostGIS, un import Onwani et des données de provenance ; carte, recherche métier, fiches publiques, bâtiments/unités, prix et médias ne sont pas encore livrés. Le contrôle d'import local du 11 octobre a retrouvé 2 432 observations, dont 2 431 parcelles conservées et une géométrie en quarantaine. Cela ne prouve pas l'exhaustivité administrative de Reem. Le chiffre affiché dans le futur site devra provenir de sa propre base et d'une version publiée, jamais d'une constante copiée ici.

La première version vise les parcelles disponibles sur **toute Reem**, avec un niveau de documentation explicite. Quelques dossiers approfondis servent à valider la valeur, sans réduire la carte à quelques bâtiments.

## Direction visuelle

Une identité d'atlas contemporain : mer, contours de parcelles, typographie lisible, espace et panneaux documentaires. Je recommande cette direction parce qu'elle expose notre matière géographique tout en laissant lire les preuves ; il faudra la tester contre une variante plus immersive.

| Élément | Proposition | But |
|---|---|---|
| Fond | Ivoire clair `#F7F8F5`, panneaux blancs | Donner de l'air aux informations denses |
| Texte | Encre `#162B36`, secondaire `#4F626B` | Hiérarchie lisible et ton documentaire |
| Action principale | Pétrole `#075E63`, texte blanc | Une action immédiatement identifiable |
| Accent | Sable `#DCC9A5`, réservé aux repères décoratifs | Évoquer le territoire sans envahir les données |
| Carte | Fond calme, eau claire, contours fins ; sélection fortement contrastée | Faire ressortir le bien consulté |
| Typographie | Sans serif sobre ; corps 16–18 px, titres fluides ; police arabe adaptée | Lecture rapide, cohérence mobile et RTL |
| Formes | Cartes arrondies modérément, ombres discrètes, séparateurs fins | Organiser le contenu sans empiler des effets |
| Mouvement | Transition courte de sélection ; prise en compte de la réduction des animations | Donner un retour sans distraire |

Ce sont des couleurs candidates, pas une palette certifiée accessible. Valider chaque couple texte/fond, focus et état. Les couleurs de couches géographiques doivent avoir une légende et une alternative textuelle ; elles ne signifient pas automatiquement « fiable » ou « dangereux ». Éviter le score global vert appliqué à un bâtiment entier.

Pas de vidéo 3D automatique dans le premier écran : la carte porte déjà le propos. Les photographies réelles pourront enrichir les dossiers après vérification des droits et de leur rattachement ; un rendu génératif devra être identifié comme illustration.

## Composition de l'accueil

### Premier écran sur ordinateur

En-tête compact : marque Liwa Atlas, liens **Explore / Data & sources**, sélecteur de langue. Ces destinations sont proposées, à créer ; ne pas afficher des boutons inactifs de comparaison, compte ou favoris.

Grille de douze colonnes : cinq pour le texte, sept pour l'aperçu cartographique. Largeur de contenu indicative 1 280 px ; marges adaptées à l'écran. Le titre et le bouton doivent rester visibles sur une hauteur d'ordinateur courante, sans dépendre d'un écran géant.

Texte anglais proposé pour le premier produit :

> **See Al Reem, parcel by parcel.**
>
> Explore mapped parcels, inspect available records, and see where each detail comes from.

Bouton principal : **Explore Al Reem**. Lien secondaire : **How our data works**. Mention de périmètre : **Al Reem Island · Abu Dhabi · Pilot**.

Ces textes décrivent ce que la première tranche devra réellement livrer. La promesse plus large « Understand the property. See the bigger picture. » pourra remplacer le titre lorsque bâtiments, environnement et dossiers seront effectivement reliés.

L'aperçu représente la vraie géographie disponible de Reem, avec une parcelle sélectionnée et une petite fiche donnant code, source et date de récupération. Il peut être une image statique dérivée de nos géométries et autorisée, puis charger la carte à l'interaction. Un schéma inventé ne doit pas être présenté comme géographie réelle.

```text
LIWA ATLAS                 Explore   Data & sources    English ▾

AL REEM ISLAND · PILOT      ┌──────────────────────────────────┐
See Al Reem,               │ Aperçu de la carte réelle        │
parcel by parcel.          │ Contours, sélection, légende     │
                          │                                  │
Courte explication        │ ┌──────────────────────────────┐ │
                          │ │ Parcelle sélectionnée        │ │
[ Explore Al Reem ]       │ │ Source · Retrieved on …      │ │
How our data works        │ └──────────────────────────────┘ │
                          └──────────────────────────────────┘
Couverture disponible · Source utilisée · Date de récupération
```

### Après le premier écran

1. **Une courte preuve de couverture.** Nombre de parcelles publiées, source et date de récupération, calculés dynamiquement. Ne pas appeler cela « bâtiments vérifiés » ou « données en temps réel ».
2. **Le parcours en trois gestes.** Explore the map → Open a parcel → Check the source. Chaque illustration correspond à un écran réellement livré.
3. **Ce que la fiche permet de comprendre.** Un extrait de dossier réel avec données disponibles et champs « Not yet documented ». Ajouter prix, plans et environnement seulement quand leur chaîne de preuve fonctionne.
4. **Sources et limites.** Expliquer en langage courant récupération, publication originale et vérification. Une date de récupération n'est pas une date de mise à jour du permis.
5. **Une deuxième invitation à explorer**, puis un pied de page avec méthodologie, couverture, confidentialité et contact lorsque ces destinations existent.

Éviter un mur de vingt fonctionnalités, des témoignages inventés et des logos institutionnels suggérant un partenariat. La collecte d'e-mails n'est pas nécessaire à cette première expérience ; l'ajouter avec un usage et un traitement définis.

## Carte et fiche

Proposer une route d'exploration localisée, par exemple `/en/explore` et `/ar/explore`, distincte de l'accueil. Ce sont des routes futures.

Sur ordinateur : carte dominante, recherche simple, liste alternative et panneau de détail. Sur mobile : carte avec fiche inférieure pouvant devenir une page complète. Conserver sélection et position dans l'URL pour partager un bien et revenir au contexte ; préférer un identifiant stable au nom commercial.

Première fiche : référence officielle, district/communauté disponibles, attributs sélectionnés et compréhensibles, source, récupération, publication originale si connue et limites. Les noms de champs bruts ne deviennent pas des libellés produit sans revue. Une géométrie valide n'est pas une certification administrative.

Ne pas exposer les captures intégrales ou toutes les colonnes collectées via l'API publique. Construire une projection explicite des champs autorisés à publier. Le module publication reste actuellement un cadre : définir la validation et les droits de diffusion avant d'ouvrir l'accès public.

La recherche commence par les références et attributs réellement indexés. Ne pas promettre une recherche par appartement, prix ou promoteur avant d'avoir ces objets et leurs rapprochements. La forme de la carte et le détail réel doivent rester cohérents entre aperçu et exploration.

## Mobile, langues et accessibilité

Anglais par défaut et quinze langues existantes, conformément à [INTERNATIONALIZATION.md](../engineering/INTERNATIONALIZATION.md). Traduire les nouveaux messages par fonctionnalité et faire relire les termes immobiliers. Prévoir l'arabe dès la maquette : espaces suffisants, propriétés CSS logiques, codes isolés et panneaux adaptés ; ne pas retourner la carte ou les plans.

Sur petit écran : titre → texte → action → aperçu, sans hauteur fixe ni défilement horizontal. L'accès liste/fiche doit rester possible sans interaction tactile avec la carte. Tester navigation au clavier, focus, lecteurs d'écran, fermeture du panneau, taille des cibles et zoom du navigateur. Une interface attractive doit aussi permettre de lire et de retrouver le même bien sans couleurs ni geste précis.

Rendre l'accueil côté serveur ; réserver le JavaScript interactif à la carte et aux contrôles. Ne pas envoyer tout le catalogue ni les preuves brutes dans le premier chargement. Pour l'exploration, servir des géométries selon la zone et le zoom, avec une limite de résultat explicite ; mesurer avant d'ajouter des tuiles vectorielles ou un moteur de recherche séparé. Choisir fournisseur de fond de carte, attribution, droits et quotas avant publication. Le budget d'infrastructure visé reste inférieur à 500 AED/mois, hors données et génération de médias ; aucune compatibilité tarifaire n'est encore prouvée par ce design.

## Ordre de développement

| Étape | Livrable concret | Condition de passage |
|---|---|---|
| 1. Contrat produit et maquette | Accueil, carte et fiche en anglais/arabe ; inventaire des champs publiables | Promesse et écrans correspondent aux données disponibles |
| 2. Lecture métier API | Parcelles par zone, détail par identifiant, provenance publique limitée | Contrats typés, limites de requête, validation spatiale et tests PostGIS |
| 3. Première tranche utilisable | Carte de toute la couverture Reem importée, liste/recherche supportée, fiche sourcée | Un clic ouvre le bon objet et sa source ; états vide/erreur documentés |
| 4. Accueil final | Composition proposée branchée sur cette tranche, aperçu réel et couverture dynamique | Toutes les actions fonctionnent, mobile/RTL/accessibilité vérifiés |
| 5. Dossiers approfondis | Quelques bâtiments/projets documentés, rapprochements revus et correction possible | Utilité démontrée face aux mêmes cas chez les concurrents |
| 6. Suivi et enrichissement | Mises à jour planifiées, alertes ; puis prix, documents et autres sources | Droits, freshness, maintenance et coûts maîtrisés |

La maquette peut commencer avant l'API, mais l'accueil final et la carte doivent être livrés ensemble. L'application mobile dédiée, les scores IA et les vidéos 3D viennent après validation du parcours et de leurs besoins ; la structure modulaire existante permet de les ajouter sans les développer tous maintenant.

## Critères de validation

Un utilisateur cible doit pouvoir expliquer ce que le produit couvre, ouvrir une parcelle, identifier une source et distinguer donnée manquante et donnée confirmée. Tester cela sur ordinateur et téléphone, y compris en arabe.

Mesurer accueil → exploration, exploration → fiche et fiche → preuve, ainsi que les difficultés observées ; ne pas optimiser uniquement le clic du bouton d'accueil. Pour les performances, mesurer la page compilée et le parcours sur connexion mobile, avec une carte utilisée ; un rendu statique rapide ne valide pas l'exploration. Fixer les seuils de payload et de latence après une première mesure sur le jeu réel de Reem.

Ce document recommande une première direction visuelle. Son efficacité devra être évaluée avec une maquette concrète et des essais utilisateurs avant de figer le design.
