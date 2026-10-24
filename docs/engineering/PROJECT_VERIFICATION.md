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
