# Tableau des tâches

Tâches issues du [plan concurrentiel](../product/PLAN_CONCURRENTIEL_20261023.md) et de la [feuille de route technique](../engineering/ENGINEERING_ROADMAP.md). A28 à A38, B08 à B13, C06, D03, E03 et F09 à F15 viennent de l'audit du 31/10 (plans comparés au code, aux tâches et à l'historique de `main`). Règles d'usage : [AGENT_WORKFLOW.md](../engineering/AGENT_WORKFLOW.md). Le fichier de chaque tâche fait foi ; ce tableau en est le résumé et se met à jour dans la même PR. Les branches partent de `main` et les PR la visent (branche de référence depuis le 28/10).

Priorité : 1 = d'abord. Une tâche est prenable si son statut est `todo`, si toutes ses dépendances sont `done` et si aucune décision du propriétaire n'est en attente.

| Tâche | Phase | Titre | Priorité | Dépend de | Décision requise | Statut | Responsable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [A01](A01.md) | A | Hiérarchie des identités de projet | 1 | — | non | done | claude |
| [A02](A02.md) | A | Qualification des positions de projet | 1 | A01 | non | done | claude |
| [A03](A03.md) | A | Sauvegardes automatiques et restauration testée | 1 | — | non | done | claude |
| [A04](A04.md) | A | Contrôle de reconstruction depuis les pipelines | 1 | A03 | non | done | codex |
| [A05](A05.md) | A | Tests de parcours navigateur (Playwright) | 1 | — | non | done | claude |
| [A06](A06.md) | A | Index des parcelles par zone visible | 2 | — | non | done | claude |
| [A07](A07.md) | A | Bâtiments et contexte en tuiles vectorielles | 2 | A06 | non | done | claude |
| [A08](A08.md) | A | Version de cache par famille de tables | 3 | — | non | done | claude |
| [A09](A09.md) | A | Découpage interne du module evidence | 3 | — | non | done | claude |
| [A10](A10.md) | A | Contenus bruts des captures vers le stockage objet | 3 | A03 | non | done | claude |
| [A11](A11.md) | A | Rejeu des anciens protocoles géographiques | 1 | A04 | non | done | claude |
| [A12](A12.md) | A | État publié reconstruit et historique des interprétations | 1 | A04 | non (décidée le 24/10) | done | claude-interactive |
| [A13](A13.md) | A | Parcours navigateur en CI | 2 | A05 | non (décidée le 25/10 : option 1) | done | claude |
| [A14](A14.md) | A | Contrôle réel du rejeu géographique : identités et divergence revue | 1 | A11 | non | done | claude |
| [A15](A15.md) | A | Écarts restants du rejeu géographique et anciennes identités OSM | 1 | A14 | non | done | claude |
| [A16](A16.md) | A | Version de cache des tables de provenance par source | 3 | A08 | non | done | claude |
| [A17](A17.md) | A | Délai dépassé de l'index des parcelles dans le job CI e2e | 1 | A13 | non | done | claude |
| [A18](A18.md) | A | Captures sous licence non qualifiée dans le dépôt public | 1 | A13 | non (décidée le 27/10 : retrait d'Aldar) | done | claude |
| [A19](A19.md) | A | Droits et licences de chaque source | 1 | A18 | non (décidée le 27/10) | done | claude |
| [A20](A20.md) | A | Licences et attributions affichées sur le site | 2 | A19 | non | done | claude |
| [A21](A21.md) | A | Qualifier les conditions des sources non relues | 2 | A19 | si une source interdit la collecte | todo | unassigned |
| [A22](A22.md) | A | Tout collecter et afficher, droits enregistrés et appliqués par interrupteur | 1 | A19 | non (décidée le 27/10) | done | claude |
| [A23](A23.md) | A | Statut de droits de chaque ligne de la base | 1 | A22 | non (décidée le 29/10) | done | claude |
| [A24](A24.md) | A | Droits de chaque source dans toute l'API et sur la carte | 1 | A22 | non (décidée le 29/10) | done | claude |
| [A25](A25.md) | A | Interrupteur de collecte respecté par tous les collecteurs | 2 | A22 | non | done | claude |
| [A26](A26.md) | A | Runner Prefect libéré des files minute et des exécutions orphelines | 1 | — | non | done | claude |
| [A27](A27.md) | A | Interrupteur de collecte respecté par le script d'imagerie manuel | 2 | A25 | non | done | claude |
| [A28](A28.md) | A | Contrôle de reconstruction réel sur main après l'émirat et les droits | 1 | A15, A23, F06 | non | todo | unassigned |
| [A29](A29.md) | A | Captures déplacées vers le stockage objet sur la base partagée | 2 | A10 | oui (exécuter `relocate` sur la base partagée) | todo | unassigned |
| [A30](A30.md) | A | Copie des sauvegardes hors de la machine | 2 | A03 | oui (destination et rétention) | todo | unassigned |
| [A31](A31.md) | A | Parcours e2e instable du signal satellite | 1 | A13, B07 | non | todo | unassigned |
| [A32](A32.md) | A | Fraîcheur par famille de sources et alertes d'exploitation | 2 | A26 | non (si une alerte sort de Prefect) | todo | unassigned |
| [A33](A33.md) | A | Budgets de performance en CI | 2 | A13 | non | todo | unassigned |
| [A34](A34.md) | A | Contours simplifiés en SQL et requêtes de map-context regroupées | 3 | A08 | non | todo | unassigned |
| [A35](A35.md) | A | Provenance publiée une fois par réponse dans les lectures de carte | 3 | A07, A24 | non | todo | unassigned |
| [A36](A36.md) | A | Images satellite servies comme fichiers cachables | 3 | A08 | non | todo | unassigned |
| [A37](A37.md) | A | État des composants carte regroupé en hooks et reducers | 3 | A07 | non | todo | unassigned |
| [A38](A38.md) | A | Chaîne d'approvisionnement figée par digest et analysée | 3 | — | oui (outil de mises à jour) | todo | unassigned |
| [B01](B01.md) | B | Qualifier l'accès au registre des projets ADREC | 1 | — | si ambiguïté | done | claude |
| [B02](B02.md) | B | Modèle et collecte de la vérification de projet | 1 | B01, A01 | non | done | claude |
| [B03](B03.md) | B | Historique de livraison des promoteurs | 1 | A01 | non | done | claude |
| [B04](B04.md) | B | Calculateur de retenue en cas d'annulation | 2 | B02 | non | done | claude |
| [B05](B05.md) | B | Fiche « Vérification » d'un projet | 1 | B02, B03, B04 | non | done | claude |
| [B06](B06.md) | B | Indice d'activité de chantier par satellite | 2 | A02 | non (décidée le 26/10 : option 3) | done | claude |
| [B07](B07.md) | B | Signal d'activité satellite sur la fiche projet | 2 | B06 | non | done | claude |
| [B08](B08.md) | B | Liens de vérification officielle DARI des projets enregistrés | 1 | B02 | oui (qui consulte l'annuaire DARI) | todo | unassigned |
| [B09](B09.md) | B | Liens de parcelle relus des projets sur plan | 2 | B06, A02 | non | todo | unassigned |
| [B10](B10.md) | B | Qualifier les permis de construire et QR de chantier d'Abu Dhabi | 2 | — | si ambiguïté | todo | unassigned |
| [B11](B11.md) | B | Frise d'avancement d'un projet sur sa fiche | 2 | B05, B07, B03 | non | todo | unassigned |
| [B12](B12.md) | B | Complétude du dossier et nature de chaque valeur affichée | 2 | B05 | non | todo | unassigned |
| [B13](B13.md) | B | Démonstration sur téléphone et essais avec cinq utilisateurs cibles | 1 | B05 | oui (recrutement et consentement) | todo | unassigned |
| [C01](C01.md) | C | Prix observés contre prix demandés | 2 | A01 | non (décidée le 28/10 : découpage vers C03) | done | claude |
| [C02](C02.md) | C | Simulateur d'échéancier et coût total | 2 | B02 | non (décidée le 28/10 : découpage vers C04, C05) | done | claude |
| [C03](C03.md) | C | Prix demandés d'annonces à permis Madhmoun vérifié | 2 | C01, A19 | si aucune source autorisée | todo | unassigned |
| [C04](C04.md) | C | Frais officiels d'enregistrement d'Abu Dhabi cités | 2 | C02, A19 | si aucun texte officiel trouvé | todo | unassigned |
| [C05](C05.md) | C | Plans de paiement des promoteurs sourcés | 2 | C02, A19 | non | todo | unassigned |
| [C06](C06.md) | C | Comparer deux ou trois projets côte à côte | 2 | C01, C02, B05 | non | todo | unassigned |
| [D01](D01.md) | D | Comptes utilisateurs | 2 | — | oui | todo | unassigned |
| [D02](D02.md) | D | Liste de suivi et alertes explicables | 2 | D01, D03 | non | todo | unassigned |
| [D03](D03.md) | D | Canal d'envoi des alertes | 2 | D01 | oui (canal, fournisseur, budget) | todo | unassigned |
| [E01](E01.md) | E | Index de recherche des preuves | 3 | A01 | non (décidée le 28/10 : option 2, mesure en E02) | done | claude |
| [E02](E02.md) | E | Assistant IA qui cite ses preuves | 3 | E01 | oui | todo | unassigned |
| [E03](E03.md) | E | Recherche dans les preuves sur le site | 2 | E01 | non | todo | unassigned |
| [F01](F01.md) | F | Parcelles de tout l'émirat d'Abu Dhabi | 3 | A06, B01 | non | done | claude |
| [F02](F02.md) | F | Qualifier les sources de Dubai | 3 | — | non | done | claude |
| [F03](F03.md) | F | Charge des parcelles de l'émirat sur les tuiles et l'index par zone | 3 | F01 | non | done | claude |
| [F04](F04.md) | F | Parcelles de l'émirat sur la carte et imports ADM et AAM | 3 | F03 | non | done | claude |
| [F05](F05.md) | F | Fin des imports de l'émirat : Madinat Al Riyad et AAM | 3 | F04 | non | done | claude |
| [F06](F06.md) | F | Réimports des derniers districts de l'émirat et mesures | 3 | F05 | non | done | claude |
| [F07](F07.md) | F | Index des identifiants officiels de parcelles pour les imports de district | 3 | F05 | non | done | claude |
| [F09](F09.md) | F | Fiches projet hors des trois îles d'Abu Dhabi | 3 | B02, F06 | oui (communautés à ajouter) | todo | unassigned |
| [F10](F10.md) | F | Bâtiments, rues et lieux sur la carte au-delà des trois îles | 3 | F06, A07 | non | todo | unassigned |
| [F11](F11.md) | F | Retrouver les jeux ouverts de Dubai sur Data.Dubai | 3 | F02 | si un compte ou une demande officielle est exigé | todo | unassigned |
| [F12](F12.md) | F | District SA' depuis une source ouverte | 3 | F08 (PR #47) | non | todo | unassigned |
| [F13](F13.md) | F | Ce qui va changer autour d'un bien | 3 | F06, B09 | non | todo | unassigned |
| [F14](F14.md) | F | Deux adresses côte à côte et trajet vers un lieu saisi | 3 | — | non | todo | unassigned |
| [F15](F15.md) | F | Ensoleillement d'un étage donné | 3 | — | non | todo | unassigned |
