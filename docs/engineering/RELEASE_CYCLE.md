# Cycle de mises à jour

Comment chaque application et chaque outil du projet reste à jour, et qui décide quoi ([A42](../tasks/A42.md)). Les versions et leurs raisons sont dans [TOOLCHAIN.md](TOOLCHAIN.md).

## Le rythme

| Quand | Quoi | Qui |
| --- | --- | --- |
| Chaque lundi, 06:00 (Dubaï) | Dependabot ouvre des PR groupées : actions, images, Python, npm | Automatique |
| Chaque lundi, 07:30 | Le workflow `Release cycle` réécrit l'issue « Cycle de mises à jour » : tout ce qui est figé comparé à ce qui est publié | Automatique |
| Après le rapport | Un agent aligne ce que Dependabot ne fait pas et ouvre une PR par groupe | Agent |
| Dès que la CI est verte | Fusion, puis mise à jour de la prévisualisation ([AGENT_WORKFLOW.md](AGENT_WORKFLOW.md), section 7) | Karim donne son accord |
| Chaque mois | Lecture du rapport avec `--host` : outils du PC | Agent, puis Karim pour les installations |
| Une version majeure | Une seule à la fois, dans sa propre PR, avec un plan de retour arrière | Karim donne son accord |

## Les règles

- **Délai de 7 jours.** Une version n'est prise que 7 jours après sa publication, pour qu'une version retirée ou compromise n'arrive jamais ici. C'est le réglage de Dependabot, et le rapport l'applique au reste. Quand le registre ne donne pas de date, comme pour certaines images `ghcr.io`, vérifier la date de publication avant d'accepter.
- **Exception : faille critique activement exploitée.** Le délai saute ; la correction part dans sa propre PR ([A40](../tasks/A40.md)).
- **Aucune fusion sans CI verte.** Aucune fusion ni déploiement automatique : chacun attend l'accord de Karim.
- **Tout aligné dans la même PR.** Manifestes, lockfiles, CI, Docker et documentation ensemble ([TOOLCHAIN.md](TOOLCHAIN.md)). `check-supply-chain-pins.mjs` refuse une image alignée à moitié.

## Ce que Dependabot ne couvre pas

| Composant | Pourquoi | Comment le mettre à jour |
| --- | --- | --- |
| Node.js, Python, pnpm | Version écrite à plusieurs endroits | PR unique : `.node-version` ou `.python-version`, CI, images, documentation |
| `uv` | Dependabot ne change que les images | Aligner `setup-uv` dans la CI, TOOLCHAIN, DEVELOPMENT, INGESTION |
| Playwright | Le paquet et l'image doivent rester à la même version | Les deux dans la même PR ([E2E.md](E2E.md)) |
| Valhalla, modèle d'embeddings | Figés par empreinte, sans étiquette | Avec la reconstruction du graphe ou le gel du modèle ([MAP_ANALYSIS.md](MAP_ANALYSIS.md), [EVIDENCE_SEARCH.md](EVIDENCE_SEARCH.md)) |
| PostgreSQL (majeure) | Le volume partagé doit être sauvegardé puis restauré | Tâche dédiée, avec `restore-check` |
| Grype | Version passée en paramètre de l'action | PR avec lecture des exceptions de `.grype.yaml` |
| Node, Git, GitHub CLI, Docker du PC | Hors du dépôt | Karim installe ; un agent ne change pas les réglages du PC |

## Consulter l'état

```bash
node --use-system-ca scripts/release/inventory.mjs --host
```

`--use-system-ca` est utile sur le PC, à cause de l'inspection HTTPS d'Avast ; il ne désactive aucune vérification. Le script ne fait que lire : il ne change aucune version.

## Revenir en arrière

En urgence, `node scripts/deploy/preview.mjs rollback --yes` remet les images d'avant le dernier déploiement, ou celles d'une version précise avec `--to <étiquette>` ([AGENT_WORKFLOW.md](AGENT_WORKFLOW.md), section 7). Ensuite, annuler la PR fautive (`git revert`) et redéployer, sinon le déploiement suivant remettra le même code. Une migration n'est jamais annulée sur la base partagée : le script la signale, l'ancien code tourne sur le schéma récent et la correction part vers l'avant.
