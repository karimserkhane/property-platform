# Prix observés et prix demandés (C01)

Tâche [C01](../tasks/C01.md), plan : [prix observés contre prix demandés](../product/PLAN_CONCURRENTIEL_20261023.md). Ce guide décrit d'abord le rapprochement entre les fiches projet et les ventes ADREC ; la projection des fourchettes et le prix demandé viendront dans la même tâche.

## 1. Le problème

Les ventes ADREC (`evidence.adrec_sale_observation`, voir [ABU_DHABI.md](ABU_DHABI.md)) nomment le projet d'une vente par un texte libre (`project_name`) dans un district, sans numéro d'enregistrement ni identifiant de bâtiment. Ces libellés ne sont pas toujours les noms du registre ADREC des projets : « Saadiyat Grove - The Heart » dans les ventes, « The Grove - Heart » au registre. Un rapprochement automatique flou rattacherait des ventes au mauvais projet. Le lien est donc relu, explicite et révocable.

## 2. Registre relu des libellés

- Fichier : `apps/api/src/property_platform/modules/evidence/project_market_labels.json`. Une ligne = `project` (slug), `district` (texte ADREC exact du district du projet), `label` (texte ADREC exact du projet), `evidence`, `registration_number` (pour `register_name`), `basis` (en anglais), `reviewed_on`.
- Deux preuves seulement, vérifiées sans base par `project_protocol.validate_project_market_labels` :
  - `register_name` : le libellé est égal, à la casse, aux espaces et à la ponctuation près, au nom d'un enregistrement ADREC (`adrec_project_v1`) que le registre des projets rattache déjà à la fiche, cité par son numéro ;
  - `project_name` : le libellé est égal, aux mêmes conditions, au nom enregistré de la fiche.
- Le district doit être celui du territoire de la fiche (`adrec.DISTRICTS`) ; un libellé d'un district désigne au plus un projet.
- Pas de ressemblance, de préfixe ni de numéro deviné : « Marlin » n'est pas rattaché à `marlin-1`, « Muheira A » ni à `muheira` ni à `muheira-2`, « Vista 1 » pas à `al-maryah-vista-1`.

Premier registre (26 octobre 2026) : **53 libellés** des trois îles, dont 16 par nom d'enregistrement ADREC, issus de toutes les fenêtres de ventes déjà collectées. **69 libellés** restent sans lien : programmes absents du catalogue (Reem Hills phases 1A–2D, Tara A, Radiant Bridges…), composants dont la fiche n'est pas séparée (Saadiyat Beach Residences - Block 1 à 6), noms proches mais non identiques (Hydra Avenue (Hydra Towers), Louvre Residences, Marina Bay by DAMAC) et lots de terrain. Ils demandent une revue humaine, ligne par ligne, avec une source citée.

## 3. Table et exécution

- Table `evidence.project_market_label` (migration additive `0036`), journalisée, rattachée au pipeline des fiches projet dans `pipeline_inventory.py`. Contraintes : preuve connue, numéro présent si et seulement si `register_name`, un seul lien actif par `(district, label)`, révocation complète.
- `apply_project_market_labels` s'exécute dans la transaction de `import_project_details`, à la fin du rejeu d'archives et via `python manage.py apply_project_market_labels --actor <nom> [--territory <id>]`. Idempotente : un lien modifié est révoqué puis recréé, un lien retiré est révoqué (`revoked_at`, `revoked_by`, motif), jamais supprimé ; un lien attend (`waiting`) tant que sa fiche n'existe pas.
- Les ventes ne sont pas recopiées : elles sont sélectionnées à la lecture par `(district, project_name)` égal au lien actif. Un libellé peut donc précéder la première fenêtre ADREC qui le contient, et une fenêtre nouvelle s'y rattache sans réécriture.

## 4. Ajouter ou retirer un libellé

1. Trouver le libellé exact dans les ventes collectées (`district`, `project_name`) et la fiche concernée.
2. Ajouter la ligne dans `project_market_labels.json` avec la preuve applicable ; si aucune ne s'applique, ne pas lier : enregistrer d'abord le nom au registre des projets (source ADREC citée), puis lier par `register_name`.
3. `pytest apps/api/tests/test_project_market_labels.py` valide le registre ; le prochain passage du pipeline des fiches (ou la commande) crée le lien. Retirer une ligne révoque le lien.

## 5. Reste à faire dans C01

- Projection par projet et type (fourchette, effectif, période de la fenêtre, primaire/secondaire), jamais une valeur unique sans intervalle.
- Prix demandé : aucun n'est collecté aujourd'hui (les extracteurs de fiches projet l'excluent volontairement, par exemple `project_propertyfinder.py` et `project_psi.py`). Le plan n'autorise à citer un prix demandé que lié à une annonce porteuse d'un permis Madhmoun vérifié ; la source de ces annonces reste à qualifier.
