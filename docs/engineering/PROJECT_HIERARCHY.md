# Hiérarchie des projets — audit et règles (A01, 23 octobre 2026)

Le registre compte 183 fiches nommées. Certaines désignent un programme (Gate & Arc), d'autres une tour ou une phase de ce programme (The Gate Tower 1, Seamont Phase 2). Jusqu'ici, elles apparaissaient à plat, sans lien. A01 ajoute un lien relu « fait partie de », sourcé et révocable, **sans jamais fusionner deux fiches** : chaque fiche garde son nom, ses sources et ses faits, et l'annuaire compte toujours les fiches nommées.

## Modèle

- Registre relu : `apps/api/src/property_platform/modules/evidence/project_relations.json`. Une ligne = `child`, `parent`, `kind`, `component` (libellé de la source : « Tower 1 », « Phase 2 »), `source_url`, `basis` (pourquoi ce lien, en anglais comme les autres notes de revue), `reviewed_on`.
- Validation (`project_protocol.validate_project_relations`) : deux fiches enregistrées et distinctes, même territoire, type connu, source parmi les sources non contractuelles de l'enfant ou du parent, champs de revue présents, un seul parent par fiche, aucun cycle.
- Table `evidence.project_relation` (migration 0031, journal de lignes, inventaire `property-platform-project-details`). La base refuse deux parents actifs, l'auto-lien et une révocation incomplète.
- Application : `apply_project_relations` s'exécute dans la transaction de `import_project_details` (pipeline Prefect des fiches) et via `python manage.py apply_project_relations --actor <nom> [--territory <id>]`. Elle est idempotente : un lien modifié est révoqué puis recréé, un lien retiré du registre est révoqué (`revoked_at`, `revoked_by`, motif), jamais supprimé. Un lien attend (`waiting`) tant que l'une des fiches ou la capture HTTP 200 de sa source manque. La preuve citée est la dernière capture HTTP 200 de `source_url` au plus tard à la fin du jour `reviewed_on` (heure des Émirats), quel que soit l'ordre d'import ; une capture de cette fenêtre importée plus tard (rejeu d'archives) remplace la citation sur le même lien, l'ancienne restant dans le journal des lignes ([A12](../tasks/A12.md)).
- Lecture publique : l'annuaire expose `parent` et `component_count`, la fiche `parent` et `components`, chacun avec composant, justification, URL source et date de collecte. Un lien n'est affiché que si les deux fiches sont publiées (snapshot accepté, non exclu).

### Types de relation

Un seul type est ouvert : `part_of` (l'enfant fait partie du parent). Il couvre à la fois « contient » (lu depuis le parent) et « phase de » (le libellé `component` dit s'il s'agit d'une tour, d'une phase ou d'un bâtiment, tel que la source le nomme). `same_as_candidate`, prévu dans la tâche, n'est pas ouvert : l'audit ci-dessous n'a trouvé aucun doublon d'identité. Pour l'ajouter, élargir `RELATION_KINDS`, la contrainte `project_relation_kind_valid` (migration additive) et l'affichage, en gardant la règle « jamais de fusion automatique ».

## Audit des cas ambigus

| Cas | Décision | Raison |
| --- | --- | --- |
| **Gate & Arc** (`gate-arc`) | Parent de `gate` (The Gate Towers) et `the-arc` (The Arc Towers) | La page communauté Aldar Gate & Arc présente les deux ensembles. |
| **The Gate Towers** (`gate`) | Parent de `the-gate-tower-1/2/3` | La page Aldar Gate décrit trois tours reliées par une passerelle ; la numérotation vient de PSI (agence), signalée dans `basis`. |
| **Radiant** (`radiant-*`, 6 fiches) | Aucun lien | Radiant Real Estate publie chaque tour comme un projet distinct ; aucune source ne décrit de programme parent. Le développeur commun suffit à les regrouper dans l'annuaire. |
| **Maysan** (`maysan`) | Parent de `mayar-in-maysan` | La fiche PSI présente Mayar comme composante de Maysan (Modon). Source d'agence, signalée comme telle dans `basis`. |
| **Talay** (`talay-beach`, `talay-marsa-al-saadiyat`) | Aucun lien | Deux communautés Aldar distinctes à Saadiyat ; aucune source ne dit que l'une contient l'autre. À revoir si Aldar publie un programme « Talay ». |
| **Parkside Residence A/B** | Aucun lien | Pas de fiche parente « Parkside Residence » dans le registre ; un lien vers une fiche inventée violerait les règles de provenance. |
| **Global Gate** (`global-gate-saadiyat`) | Aucun lien | Homonymie seulement (autre développeur, autre île). |

Autres liens relus (titres de Property Finder ou PSI qui nomment explicitement le programme) : Radisson Residences Tower 2/3, Rotana Residences North/South Tower, Seamont Phase 2, The Row Saadiyat Phase 2, Tara Park 2 (la source ne dit pas s'il s'agit d'une phase ou d'un bâtiment ; le libellé reste « Tara Park 2 »).

## Ajouter ou retirer un lien

1. Vérifier que la page source nomme explicitement le programme parent, et qu'elle figure parmi les sources (non `terms`) de l'enfant ou du parent dans `project_registry.json`.
2. Ajouter ou retirer la ligne dans `project_relations.json`, avec `basis` qui dit ce que la source affirme (et si c'est une agence plutôt que le développeur).
3. `pytest apps/api/tests/test_project_relations.py` valide le registre sans base ; le prochain passage du pipeline de fiches (ou la commande `apply_project_relations`) crée ou révoque le lien.
