import assert from "node:assert/strict";
import test from "node:test";
import {
  contradictionKeysFor,
  hasVerification,
  knownContradictions,
} from "../src/features/projects/verification.ts";

const empty = {
  latest_reading: null,
  register_readings: [],
  completion: null,
  official_links: [],
  contradictions: [],
};
const source = (url) => ({ url });
const contradiction = (code, url = "https://example.test/a") => ({
  code,
  late_by_at_least_days: null,
  announcements: [{ source: source(url), first_observed_at: "2026-10-01" }],
  register_readings: [],
});

test("each contradiction code has its own title and explanation", () => {
  assert.deepEqual(contradictionKeysFor("sources_disagree"), {
    title: "sourcesDisagree",
    note: "sourcesDisagreeNote",
  });
  assert.deepEqual(contradictionKeysFor("announced_period_passed"), {
    title: "announcedPeriodPassed",
    note: "announcedPeriodPassedNote",
  });
});

test("an unknown or inherited code is never shown under another name", () => {
  for (const code of ["late", "constructor", "__proto__", ""])
    assert.equal(contradictionKeysFor(code), null);
  const sheet = {
    ...empty,
    contradictions: [
      contradiction("future_code"),
      contradiction("sources_disagree"),
    ],
  };
  assert.deepEqual(
    knownContradictions(sheet).map((item) => item.code),
    ["sources_disagree"],
  );
});

test("the same cited disagreement is listed once", () => {
  const sheet = {
    ...empty,
    contradictions: [
      contradiction("sources_disagree"),
      contradiction("sources_disagree"),
      contradiction("sources_disagree", "https://example.test/b"),
    ],
  };
  assert.equal(knownContradictions(sheet).length, 2);
});

test("a sheet without register reading, link or contradiction says nothing is known", () => {
  assert.equal(hasVerification(null), false);
  assert.equal(hasVerification(empty), false);
  assert.equal(
    hasVerification({ ...empty, official_links: [{ url: "https://x.test" }] }),
    true,
  );
  assert.equal(hasVerification({ ...empty, latest_reading: {} }), true);
});
