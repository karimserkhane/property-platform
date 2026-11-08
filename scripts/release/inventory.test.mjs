import assert from "node:assert/strict";
import test from "node:test";
import { classify, compareVersions, renderReport } from "./inventory.mjs";

const NOW = new Date("2026-11-08T12:00:00Z");

test("compares versions numerically", () => {
  assert.ok(compareVersions("26.9.0", "26.12.1") < 0);
  assert.ok(compareVersions("v1.104.4", "1.104.4") === 0);
  assert.ok(compareVersions("18", "17") > 0);
  assert.equal(compareVersions("2.56.0", "2.56.0.windows.4"), 0);
});

test("applies the seven-day delay", () => {
  assert.deepEqual(classify("1.0.0", "1.0.0", "2026-11-07", NOW), {
    state: "current",
  });
  assert.deepEqual(classify("1.0.0", "1.1.0", "2026-10-30", NOW), {
    state: "available",
  });
  assert.deepEqual(classify("1.0.0", "1.1.0", "2026-11-05", NOW), {
    state: "cooling",
    allowedAt: "2026-11-12",
  });
});

test("a pin by digest and a failed lookup stay visible", () => {
  assert.equal(classify(undefined, "3.0.0", "2026-10-01", NOW).state, "manual");
  assert.equal(classify("1.0.0", undefined, undefined, NOW).state, "unknown");
});

test("separates what needs a person from what Dependabot handles", () => {
  const report = renderReport(
    [
      {
        name: "Hand",
        by: "hand",
        state: "available",
        pinned: "1",
        latest: "2",
      },
      {
        name: "Bot",
        by: "dependabot",
        state: "available",
        pinned: "1",
        latest: "2",
      },
      { name: "Fine", by: "hand", state: "current", pinned: "2", latest: "2" },
    ],
    [],
    NOW,
  );
  assert.ok(report.indexOf("Hand") < report.indexOf("Dependabot"));
  assert.ok(report.indexOf("Bot") < report.indexOf("Fine"));
});
