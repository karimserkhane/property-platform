# Audit de la structure et du plan — 8 novembre 2026

Fait par Claude Code à la demande de Karim, sur `main` (`6affd08`) et sur la pile locale en service. Les mesures viennent du dépôt, de PostgreSQL, de l'API Prefect, de Docker et de GitHub, en lecture seule. **Non couvert** : relecture ligne à ligne du code, temps de réponse réels, poids des pages web.

> **Mise à jour du même jour, décision de Karim.** Le site reste à lui seul pour le moment : la collecte n'est plus limitée aux sources autorisées, tant que chaque donnée garde sa licence et son autorisation en base ([A22](../tasks/A22.md)). B13 et B14 attendent donc qu'il veuille ouvrir le site à d'autres.

## Verdict

- **La technologie reste la bonne.** Monolithe modulaire, PostGIS, Prefect, Next.js : aucune mesure ne justifie d'en changer ni de découper en services.
- **Le plan reste juste, mais son ordre doit changer.** Les fondations de fiabilité passent avant la largeur fonctionnelle ; les essais à cinq utilisateurs et les comptes attendent que le site s'ouvre à d'autres.
- **Le travail en parallèle est possible à 2 ou 3 agents sur ce PC**, à condition de lever le blocage du tableau partagé. Le vrai goulot n'est pas technique : chaque fusion attend Karim.
- **Il manquait un cycle de mises à jour complet.** Dependabot couvre ce qu'il sait lire ; le reste n'a aucun rappel.

## Mesures

| Élément | Mesure |
| --- | --- |
| Code API | 19 295 lignes de Python hors migrations, dont `evidence` 17 102 (89 %) ; `publication` 1 313 ; `catalog` 880 |
| Migrations | `evidence` 42, `catalog` 7 |
| Base métier | 3,6 Go ; 51 tables dans `evidence` |
| Plus grosse table | `evidence.row_revision` : 1 437 716 lignes, 1,9 Go (52 % de la base), dont 1,26 million la semaine de l'import F06 ; rythme normal environ 39 000 par semaine |
| Prefect | 65 déploiements, 38 horaires actifs, un seul processus `serve` qui exécute une course à la fois ; base de 1,5 Go, 79 230 courses conservées |
| Fiabilité Prefect | Sur un échantillon de 12 000 courses : 23 échecs, 4 plantages, 365 annulations |
| CI GitHub | 15 jobs, environ 6 minutes |
| Tâches | 51 faites sur 80 ; phases A 33/40, B 8/13, C 2/6, D 0/3, E 1/3, F 7/15 |
| Disque | 19 Go libres sur `C:` (97 % plein) ; disque Docker de 77,6 Go, dont cache de construction 32,8 Go (20,9 récupérables), images 10,9 Go récupérables |
| Mémoire Docker | 7,7 Go alloués ; la pile en utilise 1,7 Go au repos |

## Ce qui est bien en place

- **Le module `evidence` est gros mais déjà découpé à l'intérieur** ([A09](../tasks/A09.md)). Le séparer en plusieurs applications Django imposerait de déplacer 51 tables et 42 migrations sans gain mesuré. À garder.
- **Les contrôles** sont isolés par worktree depuis [A39](../tasks/A39.md), et la CI est rapide.
- **La reconstruction** depuis les pipelines est prouvée sur `main` ([A28](../tasks/A28.md)).

## Ce qui ne va pas

1. **Des échecs passent inaperçus.** `saadiyat-project-details` a échoué à chacune de ses 4 dernières exécutions depuis le 23/10, `reem-project-discovery` à 3 sur 4. Une seule page injoignable marque tout le lot en échec, et rien ne prévient. [A32](../tasks/A32.md) passe en priorité 1.
2. **Des files tournent à vide.** Quatre files passent toutes les deux minutes, soit 2 880 courses par jour. `walking-areas` : 8 430 exécutions en 14 jours, **zéro zone enregistrée**. Chacune écrit une ligne `ingestion_run` et son journal ; `ingestion_run` est la première source de lignes du journal depuis l'import F06. Voir [A44](../tasks/A44.md).
3. **Une seule identité PostgreSQL, super-utilisateur**, pour l'API, l'ingestion et les agents. Un agent peut donc écrire dans la base partagée par erreur. Voir [A45](../tasks/A45.md).
4. **PostgreSQL garde ses réglages par défaut** (`shared_buffers` 128 Mo pour une base de 3,6 Go), et environ 470 Mo morts restent dans `evidence.capture` depuis le déplacement [A29](../tasks/A29.md) (851 Mo stockés pour 375 Mo de contenu). Voir [A46](../tasks/A46.md).
5. **Le déploiement est une suite de commandes à la main**, sans version étiquetée ni retour arrière, et il interrompt les courses Prefect en cours. Voir [A43](../tasks/A43.md).
6. **Le disque est la limite la plus proche.** Avec 19 Go libres, deux worktrees de plus suffisent à le saturer.
7. **Réglages GitHub** : 82 branches distantes, car elles ne sont pas supprimées après fusion ; `main` n'exige aucun contrôle vert avant fusion. À changer par Karim ou avec son accord.

## Corrections du plan

- **B13 attend une ouverture du site.** Le critère de la phase B (« statut, avancement et séquestre retrouvés en moins de 2 minutes, avec la preuve ») n'a jamais été mesuré ; il le sera quand Karim voudra montrer le site. D01 et D03 descendent en priorité 3 : des comptes et des canaux d'envoi ne servent pas à un seul utilisateur.
- **Nouvelle tâche [B14](../tasks/B14.md), pour plus tard.** 103 projets sur 183 tirent leurs faits uniquement de sites qui interdisent la collecte ; le jour d'une ouverture, l'interrupteur de publication les masquerait.
- **[A30](../tasks/A30.md) reste la première priorité technique** : un seul disque, aucune copie hors du PC.

## Plusieurs IA en parallèle

**Ce qui les fait se gêner aujourd'hui, par ordre d'effet mesuré.**

| Blocage | Mesure ou fait | Réponse |
| --- | --- | --- |
| `BOARD.md` modifié à la main dans chaque PR | 108 modifications depuis le 23/10, le fichier le plus touché | [A41](../tasks/A41.md) : tableau généré depuis les fichiers de tâches |
| Deux agents peuvent prendre la même tâche | La réservation n'existe que dans une PR brouillon | [A41](../tasks/A41.md) : verrou atomique par référence Git |
| Base partagée en écriture pour tous | Super-utilisateur unique | [A45](../tasks/A45.md) : rôle en lecture et base d'essai par agent |
| Chaîne unique de 42 migrations dans `evidence` | Deux PR peuvent être vertes séparément et se contredire | Exiger une branche à jour avant fusion (réglage GitHub) |
| Fichiers générés et 16 langues | `openapi.json` et `generated.ts` touchés 17 fois, chaque langue 9 fois | Les regénérer après fusion de `main`, sans résolution à la main |
| Prefect à processus unique | Un agent ne peut pas essayer un flow sans redéployer | Essais dans un conteneur à part, déjà la règle ; pas de changement avant une gêne mesurée |

**Capacité réelle.** Sur ce PC : 2 ou 3 agents qui lancent des contrôles Docker, limités par les 8 Go de Docker et le disque. Les agents qui n'ont besoin que de la CI peuvent être plus nombreux. Au-delà, chaque PR supplémentaire attend la fusion par Karim : la limite de trois PR en attente reste le bon garde-fou.

## Cycle de mises à jour

Voir [A42](../tasks/A42.md). Déjà couvert : Dependabot chaque lundi, délai de 7 jours, analyse Grype. Sans rappel aujourd'hui : les versions exclues de Dependabot (Playwright, Valhalla, modèle d'embeddings, versions majeures de PostgreSQL), celles qui vivent à plusieurs endroits (`uv`, Node, pnpm), et les outils du PC (Node, Docker Desktop, Git, GitHub CLI).
