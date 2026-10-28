import assert from "node:assert/strict";
import test from "node:test";
import {
  milestoneReached,
  monthlyRepayment,
  orderedReadings,
  progressOn,
  simulateSchedule,
} from "../src/features/projects/payment-schedule.ts";

const source = {
  label: "Test source",
  url: "https://example.test/fees",
  consultedOn: "2026-10-26",
};

const readings = [
  { inspectedOn: "2026-06-30", percent: 32 },
  { inspectedOn: "2025-12-31", percent: 8 },
  { inspectedOn: "2026-03-31", percent: 18 },
];

const byKind = (result, kind, key, value) =>
  result.payments.find(
    (payment) =>
      payment.installment.kind === kind &&
      (key === undefined || payment.installment[key] === value),
  );

test("readings are ordered by date and unreadable ones are dropped", () => {
  const ordered = orderedReadings([
    ...readings,
    { inspectedOn: "2026-13-40", percent: 50 },
    { inspectedOn: "2026-07-01", percent: 120 },
  ]);
  assert.deepEqual(
    ordered.map((reading) => reading.inspectedOn),
    ["2025-12-31", "2026-03-31", "2026-06-30"],
  );
});

test("progress at a date is the latest reading on or before it, never projected", () => {
  const ordered = orderedReadings(readings);
  assert.equal(progressOn("2025-12-30", ordered), null);
  assert.equal(progressOn("2026-03-31", ordered).percent, 18);
  assert.equal(progressOn("2026-05-01", ordered).percent, 18);
  // After the latest reading the last declared value is shown with its date.
  assert.equal(progressOn("2027-01-01", ordered).inspectedOn, "2026-06-30");
});

test("a milestone is reached by the first reading at or above it", () => {
  const ordered = orderedReadings(readings);
  assert.equal(milestoneReached(18, ordered).inspectedOn, "2026-03-31");
  assert.equal(milestoneReached(20, ordered).inspectedOn, "2026-06-30");
  assert.equal(milestoneReached(50, ordered), null);
});

test("milestones placed by readings give a single share paid", () => {
  const result = simulateSchedule({
    price: 2_000_000,
    installments: [
      { kind: "on_progress", percent: 20, progressPercent: 30 },
      { kind: "on_date", percent: 10, date: "2025-11-15" },
      { kind: "on_progress", percent: 10, progressPercent: 10 },
      { kind: "on_handover", percent: 60 },
    ],
    progress: readings,
  });
  assert.equal(result.status, "simulated");
  assert.deepEqual(result.issues, []);
  assert.deepEqual(
    result.payments.map((payment) => payment.paidPercent),
    [
      { from: 10, to: 10 },
      { from: 20, to: 20 },
      { from: 40, to: 40 },
      { from: 100, to: 100 },
    ],
  );
  const at30 = byKind(result, "on_progress", "progressPercent", 30);
  assert.equal(at30.amount, 400_000);
  assert.equal(at30.dueAfter, "2026-03-31");
  assert.equal(at30.dueBy, "2026-06-30");
  assert.equal(at30.declaredProgress.percent, 32);
  const handover = byKind(result, "on_handover");
  assert.equal(handover.dueBy, null);
  assert.equal(handover.dueAfter, "2026-06-30");
});

test("a future date against an unreached milestone is a range, not a guess", () => {
  const result = simulateSchedule({
    price: 1_000_000,
    installments: [
      { kind: "on_date", percent: 10, date: "2025-10-01" },
      { kind: "on_date", percent: 20, date: "2027-01-01" },
      { kind: "on_progress", percent: 30, progressPercent: 50 },
      { kind: "on_handover", percent: 40 },
    ],
    progress: readings,
  });
  const dated = byKind(result, "on_date", "date", "2027-01-01");
  const milestone = byKind(result, "on_progress", "progressPercent", 50);
  // Handover has no date: a payment set for 2027 may fall before or after it.
  assert.deepEqual(dated.paidPercent, { from: 30, to: 100 });
  assert.deepEqual(milestone.paidPercent, { from: 40, to: 60 });
  // The last declared progress is shown with its date, not extended to 2027.
  assert.equal(dated.declaredProgress.inspectedOn, "2026-06-30");
  assert.equal(milestone.declaredProgress, null);
  assert.equal(milestone.dueBy, null);
});

test("payments on the same date are paid together", () => {
  const result = simulateSchedule({
    price: 100,
    installments: [
      { kind: "on_date", percent: 50, date: "2026-01-01" },
      { kind: "on_date", percent: 50, date: "2026-01-01" },
    ],
  });
  for (const payment of result.payments)
    assert.deepEqual(payment.paidPercent, { from: 100, to: 100 });
});

test("without readings a milestone is ordered only against other milestones", () => {
  const result = simulateSchedule({
    price: 100,
    installments: [
      { kind: "on_date", percent: 40, date: "2026-01-01" },
      { kind: "on_progress", percent: 60, progressPercent: 20 },
    ],
  });
  const milestone = byKind(result, "on_progress");
  assert.deepEqual(milestone.paidPercent, { from: 60, to: 100 });
  assert.equal(milestone.dueAfter, null);
});

test("a plan that does not add up to 100 % is flagged, not corrected", () => {
  const result = simulateSchedule({
    price: 100,
    installments: [{ kind: "on_handover", percent: 90 }],
  });
  assert.deepEqual(result.issues, ["plan_not_100_percent"]);
  assert.equal(result.planPercent, 90);
  assert.deepEqual(result.payments[0].paidPercent, { from: 90, to: 90 });
});

test("invalid price or installment stops the simulation", () => {
  for (const input of [
    { price: 0, installments: [{ kind: "on_handover", percent: 100 }] },
    {
      price: Number.NaN,
      installments: [{ kind: "on_handover", percent: 100 }],
    },
    {
      price: 100,
      installments: [{ kind: "on_date", percent: 100, date: "soon" }],
    },
    {
      price: 100,
      installments: [
        { kind: "on_progress", percent: 100, progressPercent: 140 },
      ],
    },
    { price: 100, installments: [{ kind: "on_handover", percent: -5 }] },
  ]) {
    assert.equal(simulateSchedule(input).status, "invalid");
  }
});

test("an unknown fee is listed and the total is only a known lower bound", () => {
  const result = simulateSchedule({
    price: 1_000_000,
    installments: [{ kind: "on_handover", percent: 100 }],
    fees: [
      {
        id: "registration",
        status: "known",
        basis: "percent_of_price",
        percent: 2,
        source,
      },
      { id: "admin", status: "known", basis: "fixed", amount: 1_000, source },
      { id: "service_charge", status: "unknown" },
    ],
  });
  assert.equal(result.knownFeesTotal, 21_000);
  assert.deepEqual(
    result.unknownFees.map((fee) => fee.id),
    ["service_charge"],
  );
  assert.equal(result.knownTotalCost, 1_021_000);
  assert.equal(result.totalIsComplete, false);
});

test("a known fee without its source is rejected, never counted", () => {
  const result = simulateSchedule({
    price: 1_000,
    installments: [{ kind: "on_handover", percent: 100 }],
    fees: [{ id: "x", status: "known", basis: "fixed", amount: 50 }],
  });
  assert.deepEqual(result.issues, ["fee_invalid"]);
  assert.equal(result.knownFeesTotal, 0);
  assert.equal(result.totalIsComplete, false);
});

test("all fees known and sourced make the total complete", () => {
  const result = simulateSchedule({
    price: 1_000,
    installments: [{ kind: "on_handover", percent: 100 }],
    fees: [{ id: "x", status: "known", basis: "fixed", amount: 50, source }],
  });
  assert.equal(result.totalIsComplete, true);
  assert.equal(result.knownTotalCost, 1_050);
});

test("the loan repayment follows the annuity formula", () => {
  const monthly = monthlyRepayment({
    principal: 1_000_000,
    annualRatePercent: 4.5,
    years: 25,
  });
  assert.equal(Math.round(monthly * 100) / 100, 5558.32);
  assert.equal(
    monthlyRepayment({ principal: 120_000, annualRatePercent: 0, years: 10 }),
    1_000,
  );
});

test("the loan adds its interest to the known total cost", () => {
  const result = simulateSchedule({
    price: 1_000_000,
    installments: [{ kind: "on_handover", percent: 100 }],
    loan: { principal: 120_000, annualRatePercent: 0, years: 10 },
  });
  assert.equal(result.loan.totalInterest, 0);
  const withInterest = simulateSchedule({
    price: 1_000_000,
    installments: [{ kind: "on_handover", percent: 100 }],
    loan: { principal: 500_000, annualRatePercent: 5, years: 20 },
  });
  assert.ok(withInterest.loan.totalInterest > 0);
  assert.equal(
    withInterest.knownTotalCost,
    1_000_000 + withInterest.loan.totalInterest,
  );
});

test("a loan above the price or with impossible terms is not simulated", () => {
  const above = simulateSchedule({
    price: 100,
    installments: [{ kind: "on_handover", percent: 100 }],
    loan: { principal: 200, annualRatePercent: 3, years: 5 },
  });
  assert.deepEqual(above.issues, ["loan_above_price"]);
  assert.equal(above.loan, null);
  const impossible = simulateSchedule({
    price: 100,
    installments: [{ kind: "on_handover", percent: 100 }],
    loan: { principal: 50, annualRatePercent: -1, years: 2.5 },
  });
  assert.deepEqual(impossible.issues, ["loan_invalid"]);
  assert.equal(impossible.loan, null);
});
