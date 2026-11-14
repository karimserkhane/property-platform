# Permis de construire et QR de chantier d'Abu Dhabi — qualification du 15 novembre 2026

Tâche [B10](../tasks/B10.md). Suite de l'[enquête du 22 octobre](ENQUETE_FONCIER_PERMIS_20261022.md) (§3, et étape 4 du §8).

## Résultat

**Aucun permis de construire d'Abu Dhabi ne se vérifie publiquement en ligne sans connexion.** Le QR de chantier existe bien, mais son contenu n'est accessible qu'en le scannant sur place : aucune adresse de destination, aucun exemple de page et aucun service public de recherche par numéro de permis n'a été trouvé. Les services de permis passent par TAMM avec UAE PASS, et TAMM est protégé par reCAPTCHA. Une collecte automatique, même bornée, n'a donc rien de légitime à lire aujourd'hui.

Décision (déléguée par Karim, voir plus bas) : **saisie opérateur sourcée**, à partir d'un QR scanné par Karim sur un chantier réel. La tâche [B15](../tasks/B15.md) la met en œuvre.

## Où un permis se vérifie, et ce qu'on y trouve

| Lieu | Ce qui est public | Accès | Constat du 15/11/2026 |
| --- | --- | --- | --- |
| QR de chantier (DMT, données MePS) | Lieu, numéro, type du projet, aperçu du permis, entreprises et consultants, mises à jour | Scanner le QR affiché à l'entrée du chantier | Obligatoire depuis octobre 2024, chantiers neufs et en cours ([annonce DMT, 8/11/2024](https://www.dmt.gov.ae/en/Media-Centre/News/New-Guidelines-for-Construction-Signboards-in-the-Emirate-of-Abu-Dhabi) ; [Media Office](https://www.mediaoffice.abudhabi/en/transport/department-of-municipalities-and-transport-dmt-launches-guidelines-to-replace-construction-signboards-with-qr-codes-in-abu-dhabi/)). Ni l'annonce ni la presse ne donnent l'adresse ouverte par le QR, ni s'il faut se connecter. |
| MePS (Municipal e-Permitting System) | Rien en lecture publique | Professionnels (consultants, entrepreneurs) | Système de permis des trois municipalités depuis 2017 ([communiqué Accela](https://www.prnewswire.com/news-releases/abu-dhabi-department-of-municipal-affairs-and-transport-launches-the-municipal-electronic-permitting-system-on-accela-civic-platform-300485828.html)). Aucune page publique ni API documentée ; on ne devine pas son adresse. |
| Binaa / système unifié de permis (DMT, centre UPPC) | Rien en lecture publique | Via TAMM, demandeurs et entités publiques | [Binaa](https://www.mediaoffice.abudhabi/en/infrastructure/department-of-municipalities-and-transport-launches-binaa-digital-platform-to-enhance-building-permit-processes-in-abu-dhabi/) ; la [circulaire n° 9 de 2026](https://www.cbnme.com/news/urban-planning-permits-centre-streamline-construction-procedures-urban-planning/) (15/10/2026) remplace certains permis de clôture de phase par des rapports certifiés déposés dans ce système, sans publication. |
| TAMM | Fiches de services | Connexion UAE PASS pour les permis ; reCAPTCHA sur tout le site | [Conditions](https://www.tamm.abudhabi/en/terms-and-conditions) lues dans un navigateur : pas de clause sur la lecture automatisée, mais accès non autorisé et charge excessive interdits, tous droits réservés. La page « Copyrights » a renvoyé une page de blocage du pare-feu : notée bloquée, pas de nouvel essai. |
| Statistiques | Nombre de permis par région et par période | Communiqués DMT et SCAD ; un jeu SCAD 2010-2016 sur la plateforme fédérale | Agrégats seulement (par exemple 11 000 permis en 2025, selon la DMT), jamais un permis par chantier. La page du jeu SCAD a répondu 403 : licence non vérifiée, rien ajouté au registre. |

## Format attendu d'un permis

D'après l'annonce DMT et les guides du secteur : numéro de permis, type (fondations, construction, modification…), lieu (secteur et lot), projet, entreprise et consultant, statut et mises à jour. La forme exacte (page web, PDF, champs) reste **inconnue** tant qu'aucun QR réel n'a été lu. Le permis papier ou PDF remis au demandeur porte aussi un QR de vérification, mais il n'est pas public.

## Conditions de réutilisation

- `dmt.gov.ae` : conditions limitées à la vie privée et aux statistiques de visite ; aucune licence, aucune interdiction. Entrée ajoutée au registre : collecte permise, publication en faits datés avec lien.
- `tamm.abudhabi` : tous droits réservés, reCAPTCHA, connexion pour les permis. Entrée ajoutée : collecte permise par les conditions, mais rien n'est lisible sans contournement ; publication en lien seulement.
- L'hôte réel ouvert par un QR de chantier sera qualifié à la première lecture (B15), avec sa propre entrée dans le registre avant toute lecture automatisée.

## Exemples sur trois chantiers réels

Aucun des trois n'a de permis vérifiable en ligne. Ce que montrent les sources publiques :

1. **Seamont Autograph Collection Residences, Reem** (Royal Development Holding et SAAS Properties). Travaux préparatoires terminés, contrat principal attribué à Fibrex, construction annoncée pour octobre 2026 et 27 mois ([Zawya](https://www.zawya.com/en/business/royal-development-saas-properties-award-215.11mln-main-works-deal-for-al-reem-island-project-1509743)). Aucun numéro de lot ni de permis publié : seul le QR à l'entrée du chantier le donnerait.
2. **Marsa Al Saadiyat, Saadiyat** (Aldar). Travaux d'aménagement et d'infrastructure annoncés pour le troisième trimestre 2026 ([Zawya](https://www.zawya.com/en/projects/aldar-to-begin-enabling-work-on-27bln-marsa-al-saadiyat-in-q3-2026-408290)). Pas de lot ni de permis publics ; une annonce de démarrage n'est pas une autorisation.
3. **Radiant Square, lot RT3-13, City of Lights, Reem** (conception-réalisation TCR, client Malaih). Le portfolio de l'entreprise donne le lot, le client et le consultant, sans date ni permis ([TCR](https://tcrgroup.ae/projects_tcr/radiant-square-project/)). Ouvrage achevé : antérieur à l'obligation du QR, il n'en a sans doute pas.

## Limites

- Pas de photo de QR ni de capture dans ce dépôt public ; aucune lecture d'image de forum n'a été tentée.
- Aucun identifiant de permis deviné ou énuméré, aucun compte, aucun formulaire envoyé.
- Toutes les observations datent du 15 novembre 2026. Une absence d'adresse publique aujourd'hui n'empêche pas qu'un QR ouvre une page publique : c'est ce que B15 vérifiera sur un cas réel.

## Décision déléguée par Karim (15/11/2026)

**Retenu : saisie opérateur sourcée.** Karim scanne le QR d'un chantier ; l'adresse obtenue est saisie avec la date, le lieu et le projet. Si la page s'ouvre sans connexion, le collecteur la lit une fois, conserve l'original en stockage privé, en tire les faits typés (numéro, type, statut, entreprises, date) et les rattache au projet. Sinon, seule la saisie de l'opérateur est gardée, avec sa source.

Raisons : c'est la seule voie qui lit une source primaire sans contournement ; elle est bornée par construction (une adresse fournie par un humain, jamais devinée) ; elle est réversible (une saisie se retire, sa source reste dans le journal).

Écartés :
- **Collecte automatique bornée (pilote)** : aucune liste d'adresses découvertes légalement à lui donner ; il faudrait deviner l'hôte MePS ou énumérer des numéros, ce que l'enquête du 22 octobre et B10 interdisent.
- **Lien de vérification seulement** : aucun lien public ne mène à un permis précis ; un lien vers TAMM ne prouve rien pour un chantier donné.
- **Annonces d'entreprises et de promoteurs comme preuve de permis** : une attribution de contrat ou un démarrage annoncé n'est pas un permis ; elles restent des événements datés distincts (B11).
