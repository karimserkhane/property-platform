# Simulateur d'échéancier et coût total (C02)

Le simulateur montre l'effort réel de paiement d'un achat sur plan : quand chaque
échéance tombe, quelle part du prix est alors payée, et où en est l'avancement déclaré
à ce moment-là. Il n'a aucune donnée propre : le prix, le plan et le crédit sont saisis
par l'acheteur ou tirés d'un document cité ; les frais sont connus avec leur source, ou
inconnus.

## Calcul pur

`apps/web/src/features/projects/payment-schedule.ts`, testé par
`apps/web/tests/payment-schedule.test.mjs`. `simulateSchedule` reçoit :

| Entrée | Contenu |
| --- | --- |
| `price` | Prix de vente, strictement positif |
| `installments` | Échéances : à une date (`on_date`), à un avancement de chantier (`on_progress`), à la remise des clés (`on_handover`), chacune en pourcentage du prix |
| `fees` | Frais `known` (pourcentage du prix ou montant fixe, **toujours avec leur source**) ou `unknown` |
| `loan` | Crédit facultatif : capital, taux annuel, durée en années entières |
| `progress` | Lectures datées de l'avancement déclaré (registre ADREC) |

## Règles de lecture

- **Aucune extrapolation de chantier.** L'avancement affiché à une échéance datée est la
  dernière lecture à cette date ou avant, avec sa date ; une échéance future montre la
  dernière lecture connue, jamais une projection.
- **Jalons placés par les lectures.** Une échéance à X % est due quand l'avancement
  déclaré atteint X : la première lecture à X % ou plus borne sa date (`dueBy`), la
  dernière lecture en dessous ouvre la fenêtre (`dueAfter`). Sans lecture au-dessus, le
  jalon reste à venir. La remise des clés ne se lit pas dans un pourcentage : elle n'a
  jamais de borne haute.
- **Part payée en fourchette.** L'ordre entre une date future et un jalon non atteint
  (ou la remise des clés, qui peut précéder des paiements après livraison) est inconnu :
  la part du prix payée à chaque échéance est donnée de `from` à `to`. Elle n'est unique
  que lorsque l'ordre est établi par les dates et les lectures.
- **Plan à 100 %.** Un plan qui ne totalise pas 100 % est signalé
  (`plan_not_100_percent`), jamais corrigé.
- **Frais inconnus.** Un frais inconnu est listé, jamais compté comme zéro ; un frais
  « connu » sans source est rejeté (`fee_invalid`). Le total (`knownTotalCost` : prix,
  frais connus, intérêts du crédit) n'est complet (`totalIsComplete`) que si tous les
  frais sont connus et sourcés ; sinon c'est une borne basse.
- **Crédit.** Mensualité constante (annuité) ; taux nul : capital divisé par le nombre de
  mois. Aucun taux par défaut : un crédit supérieur au prix ou aux termes impossibles
  n'est pas simulé.
- Prix ou échéance illisible : aucune simulation (`status: invalid`). Pas de conseil
  financier ni juridique.

## Fiche projet

Le simulateur est une carte de la section « Commercial » de la fiche projet
(`payment-schedule-simulator.tsx`, composant client ; styles `schedule.module.css`).

- **Saisie par l'acheteur.** Prix, échéances (date, avancement déclaré ou remise des
  clés, chacune en pourcentage du prix) et crédit facultatif. Rien n'est prérempli : ni
  plan, ni taux, ni frais. Un champ vide est absent, jamais zéro (`enteredNumber`) ; un
  formulaire vierge invite à saisir le plan au lieu de lister les erreurs.
- **Lectures d'avancement citées.** `declaredReadings` (`schedule-form.ts`) reprend les
  lectures de registre du périmètre projet déjà exposées par la fiche
  (`verification.register_readings` et `latest_reading`) : seules celles qui ont un
  avancement **et** une date d'inspection, une fois par valeur, dans l'ordre des dates.
  La liste est rendue côté serveur avec la preuve de chaque lecture ; l'API n'a pas
  changé.
- **Frise.** Une ligne par échéance, dans l'ordre de la part payée : quand elle tombe
  (date, fenêtre `dueAfter`/`dueBy` tirée des lectures, ou remise des clés laissée
  ouverte), montant, avancement déclaré à ce moment avec sa date, part du prix payée
  (fourchette si l'ordre est inconnu) et une barre : plein = payé à coup sûr, hachuré =
  peut-être déjà payé, trait = avancement déclaré.
- **Frais.** Les frais officiels d'Abu Dhabi sont affichés « inconnus » tant qu'aucun
  texte officiel n'est cité (`SCHEDULE_FEES`) ; le coût total connu est alors une borne
  basse, et la carte le dit.
- Messages : espace `Schedule`, 16 langues ; montants en AED au format de la langue.

## Reste à faire

Frais officiels d'Abu Dhabi cités avec leur texte et leur date (source à qualifier),
plans de paiement des promoteurs sourcés quand un document les publie.
