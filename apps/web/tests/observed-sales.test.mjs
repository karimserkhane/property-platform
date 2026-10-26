import assert from "node:assert/strict";
import test from "node:test";
import {
  formatObservedRange,
  observedSalesCount,
  partialShareCount,
  saleApplicationKey,
  saleSequenceKey,
} from "../src/features/projects/observed-sales.ts";

const plain = (value) => String(value);

test("a range shows both recorded ends, or one value when they are equal", () => {
  assert.equal(
    formatObservedRange({ min: "900000.00", max: "1250000.00" }, plain),
    "900000 – 1250000",
  );
  assert.equal(
    formatObservedRange({ min: "1000000", max: "1000000.00" }, plain),
    "1000000",
  );
});

test("an unreadable or inverted range is never shown", () => {
  assert.equal(formatObservedRange({ min: "x", max: "1" }, plain), null);
  assert.equal(formatObservedRange({ min: "2", max: "1" }, plain), null);
});

test("closed ADREC values are translated, others keep their wording", () => {
  assert.equal(saleApplicationKey("off-plan"), "offPlan");
  assert.equal(saleApplicationKey("court-mandated"), "courtMandated");
  assert.equal(saleApplicationKey("__proto__"), null);
  assert.equal(saleApplicationKey("auction"), null);
  assert.equal(saleSequenceKey("secondary"), "secondary");
  assert.equal(saleSequenceKey("constructor"), null);
});

test("partial shares are the sales outside the ranges", () => {
  assert.equal(partialShareCount({ sales_count: 5, full_share_count: 3 }), 2);
  assert.equal(partialShareCount({ sales_count: 2, full_share_count: 2 }), 0);
});

test("sales are counted only inside a window", () => {
  const groups = [{ sales_count: 4 }, { sales_count: 1 }];
  assert.equal(observedSalesCount({ window: {}, groups }), 5);
  assert.equal(observedSalesCount({ window: null, groups: [] }), 0);
});
