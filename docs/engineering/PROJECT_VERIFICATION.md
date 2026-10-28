# Vérification des projets (B02)

Deux tables portent ce que la plateforme sait du statut officiel d'un projet. Aucune ne copie l'annuaire DARI, dont les conditions interdisent la collecte automatique ([décision B01](../product/QUALIFICATION_REGISTRE_ADREC_20261024.md)).

## Faits du registre ADREC

- Source : les fiches `adrec.gov.ae/api/feature/Profession/ProjectDetail` déjà déclarées dans `project_registry.json` (analyseur `adrec_project_v1`) et collectées par le pipeline des fiches (`property-platform-project-details`).
- Table `evidence.project_verification` (migration `0033`) : une ligne par lecture (`ProjectSnapshot`), donc l'historique est la suite des lectures. Numéro de projet, permis, statut, vente sur plan, avancement et date d'inspection, rapport, part vendue (texte d'origine conservé), banque et numéro de séquestre, licence du promoteur.
- Dates : l'observation est la date de capture ; la mesure de l'avancement est la date d'inspection donnée par le registre, jamais la date de collecte.
- Réversibilité : retirer la source ADREC d'un projet du registre arrête les lectures sans effacer l'historique.

## Liens vers la fiche officielle

- Registre relu : `apps/api/src/property_platform/modules/evidence/project_verification_links.json`. Une ligne = `project` (slug), `registration_number`, `url`, `basis` (en anglais : ce que l'opérateur a vu sur la page), `reviewed_on`.
- Règles vérifiées sans base (`project_protocol.validate_project_verification_links`) : le numéro doit être porté par une source ADREC enregistrée du projet, ce qui rattache chaque lien à une fiche collectée ; l'URL est exactement `https://www.dari.ae/en/app/directory/project/<id>` ; une page par enregistrement et un enregistrement par page.
- Table `evidence.project_verification_link` (migration `0034`), journalisée. `apply_project_verification_links` s'exécute dans la transaction de `import_project_details`, à la fin du rejeu d'archives et via `python manage.py apply_project_verification_links --actor <nom> [--territory <id>]`. Idempotente : un lien modifié est révoqué puis recréé, un lien retiré est révoqué (`revoked_at`, `revoked_by`, motif), jamais supprimé ; un lien attend (`waiting`) tant que son projet n'existe pas.
- La page n'est jamais lue par la plateforme : c'est une référence que l'acheteur ouvre lui-même (fiche « Vérification », [B05](../tasks/B05.md)). L'identifiant de fiche DARI est interne et peut changer ; une revue datée le remplace.

## Ajouter un lien

1. Ouvrir à la main la fiche de l'annuaire DARI et vérifier que son numéro de projet est celui de la source ADREC du projet.
2. Ajouter la ligne dans `project_verification_links.json`.
3. `pytest apps/api/tests/test_project_verification_links.py` valide le registre ; le prochain passage du pipeline de fiches (ou la commande) crée le lien.

## Retenue en cas d'annulation (B04)

`publication/cancellation_retention.py` lit, pour un avancement déclaré, la part du prix
qu'un promoteur peut retenir quand l'unité d'un acheteur défaillant est annulée
(décision administrative n° 165 de 2025, Abu Dhabi). Le texte officiel n'a pas été
obtenu : le barème est recopié des commentaires cités dans le module, avec leur date de
publication et de consultation ([A&O Shearman, 8 septembre 2026](https://www.aoshearman.com/en/insights/abu-dhabis-new-escrow-and-off-plan-sales-regime-from-momentum-to-regulated-delivery),
[Trowers & Hamlins, 22 avril 2026](https://www.trowers.com/insights/2026/april/four-key-decisions-reshaping-abu-dhabi)).

| Avancement | Retenue du prix de vente |
| --- | --- |
| Travaux non commencés pour une cause extérieure au promoteur | 0 % (remboursement intégral) |
| Moins de 10 % | 10 % |
| De 10 à 30 % | 15 % |
| De 30 à 60 % | 25 % |
| De 60 à 100 % | 40 % |

Règles de lecture :

- Les sources ne disent pas à quelle tranche appartiennent 10, 30 et 60 % : à ces valeurs
  exactes, les deux taux sont rendus (`status: boundary`), jamais un seul choisi.
- Un avancement de 0 % donne 10 % et signale le cas du remboursement intégral : sa cause
  ne se lit pas dans le registre, l'ADREC l'apprécie.
- L'avancement retenu par la décision est celui que l'ADREC ou ses consultants
  constatent à l'annulation ; la fiche n'affiche que le dernier avancement déclaré et sa
  date.
- Au-delà de 60 % du prix payés par l'acheteur, l'ADREC fixe la retenue au cas par cas :
  toujours signalé, puisque la part payée est propre à chaque acheteur.
- Avancement absent ou hors de 0 à 100 % : aucun taux. Aucun conseil juridique ; la
  fiche renvoie aux sources.
- Le barème régit la vente sur plan : aucune retenue n'est lue pour un projet que le
  registre ne déclare pas sur plan (`off_plan` faux ou absent).

Sur la fiche projet, `GET /projects/{slug}` porte `declared_progress` (dernière lecture
ADREC de portée projet ayant un avancement : taux, date d'inspection, statut, vente sur
plan, source) et `cancellation_retention` (lecture du barème à cet avancement, avec la
source de l'avancement et les références du barème). Le web
(`features/projects/cancellation-retention.tsx`, namespace `Retention`) affiche, dans le
volet achat, la retenue au stade actuel déclaré, l'avancement et sa date d'inspection,
le cas des 60 % payés, le remboursement intégral possible à 0 %, puis la règle et ses
sources datées.

## Fiche « Vérification » (B05)

`GET /projects/{slug}` porte `verification`, assemblé par `evidence/projects/verification_sheet.py`
en lecture seule, sur les mêmes lectures que l'[historique de livraison](DELIVERY_HISTORY.md)
(`delivery_history.delivery_readings`, une seule lecture des fiches du projet) :

- `latest_reading` : dernière lecture ADREC de portée projet, valeurs telles que publiées
  (numéro, permis, statut, vente sur plan, date d'enregistrement, avancement, date et
  société d'inspection, rapport et sa validité, part vendue et texte d'origine, banque et
  numéro de séquestre, licence du promoteur) avec sa source. `progress_report_expired` est
  jugé à la date de la lecture, jamais à celle du visiteur.
- `register_readings` et `completion` : la suite des statuts lus et le premier achèvement,
  comme pour la page promoteur.
- `official_links` : liens actifs vers la fiche officielle (numéro, URL, date de revue) ;
  la note de l'opérateur et son nom ne sont pas publiés, un lien révoqué disparaît.
- `contradictions` : deux lectures citées mises côte à côte, sans cause déduite ni source
  désignée comme juste. Seule la dernière valeur annoncée par chaque source est comparée.
  - `announced_after_completion` : une source annonce encore, après le premier achèvement
    lu au registre, une période qui commence plus tard ;
  - `announced_period_passed` : la période annoncée est terminée et une lecture postérieure
    ne dit pas « achevé » (retard minimal en jours) ;
  - `sources_disagree` : deux sources annoncent des périodes qui ne se recouvrent pas ;
  - `progress_decreased` : une fiche du registre déclare plus tard un avancement plus bas.

Sur la fiche projet, la section « Vérification » (`#project-verification`, juste après la
présentation, entrée dans la navigation de la fiche) affiche, sur une colonne au téléphone :

- la dernière lecture : statut au registre (texte d'origine, en anglais), numéro, permis,
  vente sur plan, avancement et date d'inspection, rapport et validité (« expiré à la date
  de la lecture » si l'API le juge ainsi), part vendue, banque et numéro de séquestre,
  licence, avec la preuve dépliable ; une valeur absente est dite « non indiquée au
  registre », jamais déduite ;
- le premier achèvement lu, puis les « points à vérifier » : chaque contradiction connue
  avec son explication et les annonces ou lectures citées, comme sur la page promoteur.
  Un code inconnu n'est pas affiché ; une même contradiction n'apparaît qu'une fois ;
- les lectures successives du registre (repliées), les liens officiels relus ou, à défaut,
  l'invitation à chercher le numéro sur le registre de l'ADREC ;
- des renvois vers l'historique de livraison du promoteur et la retenue en cas
  d'annulation (B04), puis l'avertissement « pas un conseil ».

Un projet sans lecture du registre affiche seulement que rien ne lui est encore rattaché.
