import assert from "node:assert/strict";
import test from "node:test";
import { simulateSchedule } from "../src/features/projects/payment-schedule.ts";
import {
  declaredReadings,
  enteredNumber,
  SCHEDULE_FEES,
  scheduleInput,
} from "../src/features/projects/schedule-form.ts";

const source = (url) => ({ url, retrieved_at: "2026-10-01T00:00:00Z" });
const reading = (percent, inspectedOn, url = "https://example.test/r") => ({
  progress_percent: percent,
  progress_inspected_on: inspectedOn,
  source: source(url),
});

const form = (rows, extra = {}) => ({
  price: "1000000",
  rows,
  useLoan: false,
  principal: "",
  rate: "",
  years: "",
  ...extra,
});
const row = (id, kind, percent, more = {}) => ({
  id,
  kind,
  percent,
  date: "",
  progressPercent: "",
  ...more,
});

test("declared readings are dated, cited once and in date order", () => {
  const verification = {
    register_readings: [
      reading(40, "2026-06-30", "https://example.test/b"),
      reading(12, "2025-12-31"),
      reading(null, "2026-01-31"),
      reading(30, null),
    ],
    latest_reading: reading(40, "2026-06-30", "https://example.test/c"),
  };
  assert.deepEqual(
    declaredReadings(verification).map((item) => [
      item.inspectedOn,
      item.percent,
      item.source.url,
    ]),
    [
      ["2025-12-31", 12, "https://example.test/r"],
      ["2026-06-30", 40, "https://example.test/b"],
    ],
  );
  assert.deepEqual(declaredReadings(null), []);
});

test("an empty field is missing, never zero", () => {
  assert.ok(Number.isNaN(enteredNumber("")));
  assert.ok(Number.isNaN(enteredNumber("   ")));
  assert.equal(enteredNumber(" 12.5 "), 12.5);
  const result = simulateSchedule(
    scheduleInput(form([row("0", "on_date", "")], { price: "" }), []),
  );
  assert.equal(result.status, "invalid");
  assert.deepEqual(result.issues.sort(), [
    "installment_invalid",
    "price_invalid",
  ]);
});

test("official fees stay unknown, so the total is a lower bound", () => {
  const input = scheduleInput(
    form([
      row("0", "on_date", "20", { date: "2026-01-15" }),
      row("1", "on_progress", "30", { progressPercent: "40" }),
      row("2", "on_handover", "50"),
    ]),
    [
      { inspectedOn: "2025-12-31", percent: 12 },
      { inspectedOn: "2026-06-30", percent: 40 },
    ],
  );
  assert.deepEqual(input.fees, SCHEDULE_FEES);
  const result = simulateSchedule(input);
  assert.equal(result.status, "simulated");
  assert.deepEqual(result.issues, []);
  assert.equal(result.totalIsComplete, false);
  assert.equal(result.knownTotalCost, 1000000);
  const milestone = result.payments.find(
    (payment) => payment.installment.kind === "on_progress",
  );
  assert.equal(milestone.dueBy, "2026-06-30");
  assert.equal(milestone.dueAfter, "2025-12-31");
});

test("the loan is only read when the buyer includes it", () => {
  const rows = [row("0", "on_handover", "100")];
  assert.equal(scheduleInput(form(rows), []).loan, null);
  const input = scheduleInput(
    form(rows, { useLoan: true, principal: "600000", rate: "0", years: "10" }),
    [],
  );
  assert.deepEqual(input.loan, {
    principal: 600000,
    annualRatePercent: 0,
    years: 10,
  });
  assert.equal(simulateSchedule(input).loan.monthlyRepayment, 5000);
  const missing = scheduleInput(
    form(rows, { useLoan: true, principal: "600000", rate: "", years: "10" }),
    [],
  );
  assert.ok(simulateSchedule(missing).issues.includes("loan_invalid"));
});
