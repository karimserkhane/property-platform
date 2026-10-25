import assert from "node:assert/strict";
import test from "node:test";
import {
  formatPercent,
  retentionRates,
} from "../src/features/projects/retention.ts";

const retention = (status, rates) => ({ status, rates });

test("the declared stage shows one rate, or both on an open band limit", () => {
  assert.deepEqual(retentionRates(retention("rate", [15]), "en"), ["15%"]);
  assert.deepEqual(retentionRates(retention("boundary", [15, 25]), "en"), [
    "15%",
    "25%",
  ]);
});

test("an unreadable declared progress never shows a rate", () => {
  assert.deepEqual(retentionRates(retention("unknown", []), "en"), []);
  assert.deepEqual(retentionRates(retention("out_of_range", [10]), "en"), []);
});

test("declared progress keeps its precision in the reader's locale", () => {
  assert.equal(formatPercent(12.5, "en"), "12.5%");
  assert.equal(formatPercent(12.5, "fr"), "12,5 %");
});
