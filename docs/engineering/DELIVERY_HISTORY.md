# Historique de livraison des promoteurs (B03)

Pour un promoteur, la plateforme montre ce que chaque source a annoncé comme date de livraison au fil du temps, ce que le registre ADREC a publié lors de chaque lecture, et les retards que ces lectures prouvent. C'est un calcul en lecture sur les lectures déjà stockées (`evidence.project_snapshot`, `evidence.project_verification`) : pas de table, pas de migration, pas de pipeline.

Code : `apps/api/src/property_platform/modules/evidence/delivery_history.py`. API : `GET /api/v1/preview/developers/{key}/delivery-history` (aperçu local, mêmes gardes que les fiches projet).

## Règles

- **Projets** : les fiches publiées du promoteur, avec les mêmes règles que l'annuaire (lectures acceptées, relecture d'un même reçu, exclusions). Une annonce retirée (`<url>#handover` dans `history_exclusion`) ne compte plus.
- **Annonces** : une suite par source (URL de capture). Deux lectures successives identiques sont regroupées (première et dernière observation, nombre de lectures). Chaque point garde le texte d'origine, sa précision (année, trimestre, mois, jour) et la période qu'elle désigne, du premier au dernier jour. Les annonces de sources différentes ne sont jamais comparées entre elles : un courtier qui diffère du promoteur n'est pas un report.
- **Changement** entre deux annonces d'une même source : `later` si la nouvelle période commence après la fin de l'ancienne, `earlier` dans le cas inverse, `refined` si elles se chevauchent (« 2026 » devenu « T4 2026 »), `first` pour la première.
- **Registre** : les lectures ADREC dont la portée est le projet lui-même (`fact_scope=project`) ; une fiche qui n'identifie qu'une composante ne décrit pas le projet. Seul le statut `Completed` vaut achèvement. Le registre ne publie pas de date d'achèvement : l'achèvement est situé entre la dernière lecture non achevée et la première lecture achevée.
- **Résultat de chaque annonce** :
  - `met` : une lecture du registre indique l'achèvement au plus tard le dernier jour de la période annoncée ;
  - `late` : une lecture postérieure à ce jour indique encore un projet non achevé ; `late_by_at_least_days` compte les jours entre la fin de la période et la dernière lecture de ce type. C'est une borne inférieure, jamais une estimation du retard réel ;
  - `undetermined` : aucune lecture ne permet de conclure (par exemple achèvement vu pour la première fois après la période, sans lecture intermédiaire).
- Les jours sont lus en heure des Émirats. Chaque point et chaque résultat renvoie à la lecture qui le prouve (URL, empreinte, date de capture, pointeur).
- **Résumé** : des comptes de projets (avec annonces, avec registre, achèvement observé, retard observé, annonce repoussée par sa source). Aucun taux ni score : les échantillons sont trop petits et la couverture inégale.

## Limites

- Les captures datent d'octobre 2026 ; les changements d'annonce observés restent rares tant que les sources ne sont pas relues dans la durée.
- Un projet sans source ADREC n'a aucune livraison constatée ; ses annonces restent `undetermined`.
- L'affichage (page promoteur, fiche « Vérification ») relève de l'étape suivante de B03 et de [B05](../tasks/B05.md).
