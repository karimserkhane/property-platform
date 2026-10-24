# Qualification de l'accès au registre des projets ADREC — 24 octobre 2026

Note de la tâche [B01](../tasks/B01.md). Elle qualifie où et comment un acheteur peut vérifier un projet sur plan enregistré à Abu Dhabi, ce que la source montre réellement, ce que ses conditions permettent, et ce que la plateforme en fera. Observations du 24 octobre 2026 entre 10:30 et 10:45 UTC ; aucune donnée n'a été importée dans la base.

## Méthode

- Lecture des pages publiques avec un navigateur, sans compte, sans connexion UAE PASS, sans accepter les cookies non essentiels.
- Lecture du code JavaScript public de l'application pour identifier les routes, sans l'exécuter hors du navigateur.
- Une seule requête directe à l'interface de données, **sans** jeton, pour vérifier si elle est ouverte (réponse `401`). Aucun jeton n'a été demandé ou réutilisé hors de la page.
- Une seule fiche de projet ouverte en détail. Pas de pagination ni de parcours de l'annuaire.

## Où se trouve le registre consultable

| Élément | Constat |
| --- | --- |
| Page publique | [Annuaire DARI, onglet Projects](https://www.dari.ae/en/app/directory), titre de page « Property Directory of Abu Dhabi - ADREC ». Consultable sans compte. |
| Fiche de projet | `https://www.dari.ae/en/app/directory/project/<id>`, où `<id>` est un identifiant interne DARI distinct du numéro de projet (exemple : `730` pour le projet `20260001482662`). |
| Exploitant | DARI est fourni par Advanced Real Estate Services LLC (ADRES LLC), autorisée par le Department of Municipalities and Transport (DMT) ([conditions DARI](https://www.dari.ae/en/app/term-and-condition)). La [FAQ ADREC](https://adrec.gov.ae/en/faqs) renvoie vers DARI pour l'avancement des projets ([inventaire du 13 octobre](SOURCES_DONNEES_UAE.md)). |
| Effectif affiché | « 325 Results », toutes municipalités, à 10:38 UTC. C'est l'effectif affiché par l'annuaire, pas un inventaire vérifié de tous les projets sur plan. |
| Interface de données | La page appelle `https://api.dari.ae/property-service/api/v1/property/project?page=0&size=12&direction=desc&sort=projectCreateDate` après avoir obtenu un jeton sur `https://api.dari.ae/authentication-service/oauth/token`. Sans jeton : `401`, corps vide (10:38:56 UTC). Ce n'est pas une API publique documentée. |
| Accès API officiel | [ADREC — API Subscription](https://adrec.gov.ae/en/apisubscription) : formulaire de demande (« Single Service API … brokers, directory, etc. »), sans tarif ni conditions de réutilisation publiés. Aucune demande n'a été envoyée. |

## Format observé

**Carte de liste** : type (Building, Plot, Villas), badge « New », nom, numéro de projet, pourcentage d'avancement (« 0% Completion »), usage (Mixed use, Residential), municipalité, district, communauté.

**Fiche détaillée** (projet `730`) : nom, promoteur, municipalité, district, communauté, nombre d'unités résidentielles et commerciales, date d'enregistrement, type, numéro de projet, usage, description du promoteur, coordonnées et numéro de licence du promoteur, répartition des unités par nombre de chambres.

Non visibles sur la liste ni sur la fiche ouverte : date à laquelle l'avancement a été mesuré, compte séquestre, banque, date de livraison prévue, unités vendues. Le code public de l'application contient des routes `directory/property/project-progress-report` et `directory/property/project-service-charges` ; leur contenu et leurs conditions d'accès n'ont pas été examinés.

## Trois projets réels

Valeurs recopiées de l'annuaire le 24 octobre 2026 vers 10:40 UTC, pour qualification uniquement ; elles ne sont pas importées.

| Projet | Numéro de projet | Avancement affiché | Localisation affichée | Remarques |
| --- | --- | --- | --- | --- |
| Sei Saadiyat 1 | 20260001482662 | 0 % | Abu Dhabi City, Al Saadiyat Island, SDN8 | Fiche `730` : promoteur ALDAR DEVELOPMENT - L.L.C - O.P.C, enregistré le 13/10/2026, 265 unités résidentielles et 4 commerciales. La description du promoteur annonce 267 appartements alors que la répartition affichée totalise 265 (140 + 103 + 22) : les deux valeurs doivent rester distinctes et sourcées. |
| Yas Canal | 20260000773844 | 12 % | Abu Dhabi City, Al Rahah, RBE1 | Fiche détaillée non ouverte. |
| Zaitouna Residence | 20260001484664 | 90 % | Abu Dhabi City, Al Shamkhah, SH36 | Fiche détaillée non ouverte ; badge « New » malgré 90 % : le badge ne décrit pas l'avancement. |

## Conditions de réutilisation

Les [conditions DARI](https://www.dari.ae/en/app/term-and-condition) s'appliquent à l'annuaire (« Services » et « Content »). Elles sont explicites sur les points qui décident de la collecte :

- interdiction d'utiliser un robot, un scraper ou tout procédé automatisé pour accéder, obtenir, copier, surveiller ou republier une partie des services ou du contenu ;
- interdiction de contourner les dispositifs de sécurité ;
- interdiction d'accéder aux services pour construire un produit ou service concurrent ;
- droits de propriété intellectuelle, y compris droits sur les bases de données, réservés à ADRES LLC et à ses concédants ; aucun droit accordé sauf accord exprès ;
- contenu fourni à titre d'information générale, sans garantie d'exactitude ni de disponibilité.

## Limites

- L'avancement n'est pas daté par la source : la date de relevé est la seule date disponible et ne doit pas être présentée comme date de mesure.
- Le séquestre et les unités vendues, cités par les commentaires juridiques sur la vérification ADREC ([A&O Shearman, 4 septembre 2026](https://www.aoshearman.com/en/insights/abu-dhabi-real-estate-five-changes-and-what-they-mean-for-your-next-transaction)), n'apparaissent pas dans l'annuaire public examiné. Ils relèvent peut-être de services réservés aux parties concernées.
- L'identifiant de fiche est interne à DARI ; sa stabilité dans le temps n'est pas garantie.
- 325 projets affichés ne prouvent pas l'exhaustivité du registre.

## Décision

**Lien de vérification seulement**, avec rattachement de référence :

1. **Pas de collecte automatique.** Les conditions l'interdisent sans ambiguïté et l'interface exige un jeton émis à la page ; aucun collecteur Prefect ne sera écrit pour DARI.
2. **Ce que la plateforme conserve** : pour un projet, le numéro de projet officiel et le lien vers sa fiche DARI, saisis par un opérateur via une commande auditée et réversible, avec date et auteur du rattachement. Ce sont des références permettant à l'acheteur de vérifier lui-même, pas une copie du contenu.
3. **Ce que la plateforme ne republie pas** : avancement, unités, promoteur ou licence tels qu'affichés par DARI. La fiche « Vérification » (B05) renvoie vers la page officielle et explique ce qu'il faut y regarder.
4. **Évolution possible, sur décision du propriétaire** : demander un accès via [API Subscription](https://adrec.gov.ae/en/apisubscription) ou une autorisation écrite d'ADRES/ADREC. Seule une telle autorisation permettrait une collecte automatique ou l'affichage des valeurs. Aucune demande n'est faite par les agents.

Conséquence pour [B02](../tasks/B02.md) : le modèle stocke des rattachements projet ↔ numéro ADREC ↔ lien de vérification, datés et réversibles, sans collecteur. Les faits datés (avancement, séquestre) restent vides tant qu'une source autorisée ne les fournit pas.
