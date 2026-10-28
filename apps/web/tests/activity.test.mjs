import assert from "node:assert/strict";
import test from "node:test";
import {
  activityBasisKey,
  activityState,
  describedParcels,
  formatHectares,
} from "../src/features/projects/activity.ts";

const parcel = (latest, basis = {}) => ({
  source_namespace: "test:parcels",
  source_record_id: "1",
  official_plot_id: null,
  area_m2: 11_000,
  area_basis: "reviewed_parcel",
  position_method: "cadastral_parcel",
  ...basis,
  latest: {
    status: "measured",
    level: "high",
    parcel_pixels: 120,
    clear_pixels: 100,
    ...latest,
  },
});

test("a measured parcel shows a level, never a share", () => {
  const state = activityState(parcel({}));
  assert.equal(state.kind, "measured");
  assert.equal(state.level, "levelHigh");
  assert.equal("changed_share" in state.latest, false);
});

test("an unmeasurable pair is said, without a level", () => {
  const state = activityState(
    parcel({ status: "insufficient_clear_pixels", level: null }),
  );
  assert.equal(state.kind, "insufficient");
});

test("an unknown or inconsistent result is never shown", () => {
  for (const latest of [
    { level: "__proto__" },
    { level: "constructor" },
    { level: null },
    { status: "insufficient_clear_pixels" },
    { status: "progress" },
  ])
    assert.equal(activityState(parcel(latest)), null);
});

test("the basis matches how the parcel was chosen", () => {
  assert.equal(activityBasisKey(parcel({})), "basisReviewedParcel");
  const derived = { area_basis: "parcel_containing_position" };
  assert.equal(
    activityBasisKey(
      parcel({}, { ...derived, position_method: "authority_point" }),
    ),
    "basisAuthorityPoint",
  );
  assert.equal(
    activityBasisKey(
      parcel({}, { ...derived, position_method: "cadastral_parcel" }),
    ),
    null,
  );
  assert.equal(
    activityBasisKey(parcel({}, { position_method: "authority_point" })),
    null,
  );
  assert.equal(
    activityBasisKey(
      parcel({}, { ...derived, position_method: "broker_point" }),
    ),
    null,
  );
});

test("only describable parcels are listed", () => {
  const sheet = {
    source: { name: "Copernicus Sentinel-2 L2A", url: "https://example.test" },
    parcels: [parcel({}), parcel({ level: "unknown" })],
  };
  assert.equal(describedParcels(sheet).length, 1);
});

test("parcel area is given in hectares", () => {
  assert.equal(formatHectares(11_000, "en"), "1.1");
  assert.equal(formatHectares(2_500, "fr"), "0,25");
});
