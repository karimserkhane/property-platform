# Tableau des tâches

Tâches issues du [plan concurrentiel](../product/PLAN_CONCURRENTIEL_20261023.md) et de la [feuille de route technique](../engineering/ENGINEERING_ROADMAP.md). Règles d'usage : [AGENT_WORKFLOW.md](../engineering/AGENT_WORKFLOW.md). Le fichier de chaque tâche fait foi ; ce tableau en est le résumé et se met à jour dans la même PR. Les branches partent de `main` et les PR la visent (branche de référence depuis le 28/10).

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
| [A21](A21.md) | A | Qualifier les conditions des sources non relues | 2 | A19 | non (décidée le 28/10 : option a) | in-progress | claude |
| [A22](A22.md) | A | Tout collecter et afficher, droits enregistrés et appliqués par interrupteur | 1 | A19 | non (décidée le 27/10) | done | claude |
| [B01](B01.md) | B | Qualifier l'accès au registre des projets ADREC | 1 | — | si ambiguïté | done | claude |
| [B02](B02.md) | B | Modèle et collecte de la vérification de projet | 1 | B01, A01 | non | done | claude |
| [B03](B03.md) | B | Historique de livraison des promoteurs | 1 | A01 | non | done | claude |
| [B04](B04.md) | B | Calculateur de retenue en cas d'annulation | 2 | B02 | non | done | claude |
| [B05](B05.md) | B | Fiche « Vérification » d'un projet | 1 | B02, B03, B04 | non | done | claude |
| [B06](B06.md) | B | Indice d'activité de chantier par satellite | 2 | A02 | non (décidée le 26/10 : option 3) | done | claude |
| [B07](B07.md) | B | Signal d'activité satellite sur la fiche projet | 2 | B06 | non | done | claude |
| [C01](C01.md) | C | Prix observés contre prix demandés | 2 | A01 | non (décidée le 28/10 : découpage vers C03) | done | claude |
| [C02](C02.md) | C | Simulateur d'échéancier et coût total | 2 | B02 | non (décidée le 28/10 : découpage vers C04, C05) | done | claude |
| [C03](C03.md) | C | Prix demandés d'annonces à permis Madhmoun vérifié | 2 | C01, A19 | si aucune source autorisée | todo | unassigned |
| [C04](C04.md) | C | Frais officiels d'enregistrement d'Abu Dhabi cités | 2 | C02, A19 | si aucun texte officiel trouvé | todo | unassigned |
| [C05](C05.md) | C | Plans de paiement des promoteurs sourcés | 2 | C02, A19 | non | todo | unassigned |
| [D01](D01.md) | D | Comptes utilisateurs | 2 | — | oui | todo | unassigned |
| [D02](D02.md) | D | Liste de suivi et alertes explicables | 2 | D01 | non | todo | unassigned |
| [E01](E01.md) | E | Index de recherche des preuves | 3 | A01 | non | todo | unassigned |
| [E02](E02.md) | E | Assistant IA qui cite ses preuves | 3 | E01 | oui | todo | unassigned |
| [F01](F01.md) | F | Parcelles de tout l'émirat d'Abu Dhabi | 3 | A06, B01 | non | done | claude |
| [F02](F02.md) | F | Qualifier les sources de Dubai | 3 | — | non | done | claude |
| [F03](F03.md) | F | Charge des parcelles de l'émirat sur les tuiles et l'index par zone | 3 | F01 | non | done | claude |
| [F04](F04.md) | F | Parcelles de l'émirat sur la carte et imports ADM et AAM | 3 | F03 | non | done | claude |
| [F05](F05.md) | F | Fin des imports de l'émirat : Madinat Al Riyad et AAM | 3 | F04 | non | done | claude |
| [F06](F06.md) | F | Réimports des derniers districts de l'émirat et mesures | 3 | F05 | non | done | claude |
| [F07](F07.md) | F | Index des identifiants officiels de parcelles pour les imports de district | 3 | F05 | non | done | claude |
| [F08](F08.md) | F | Couches AD-SDI depuis la plateforme ouverte data.abudhabi | 2 | A19 | non | todo | unassigned |
