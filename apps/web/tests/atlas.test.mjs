import assert from "node:assert/strict";
import test from "node:test";
import {
  csv,
  geometryBounds,
  normalized,
  selectMapHit,
} from "../src/features/atlas/presentation.ts";

const hit = (layer, id, properties = {}) => ({
  layer: { id: layer },
  properties: { id, ...properties },
});

test("a building under the pointer wins over its parcel and sector", () => {
  const building = hit("buildings", "building");
  const parcel = hit("parcel-fill", "parcel", { category: "mixed" });
  const sector = hit("area-hit", "RT4", { kind: "community" });
  for (const hits of [
    [sector, parcel, building],
    [building, sector, parcel],
  ])
    assert.equal(selectMapHit(hits), building);
});

test("RT4 ProjectLimits never hides the real parcel under the pointer", () => {
  const overlay = hit("parcel-fill", "RT4_TMP_PL2", { category: "overlay" });
  const parcel = hit("parcel-fill", "RT4_C1", { category: "mixed" });
  const sector = hit("area-hit", "RT4", { kind: "community" });
  assert.equal(selectMapHit([overlay, sector, parcel]), parcel);
  assert.equal(selectMapHit([parcel, overlay, sector]), parcel);
  assert.equal(selectMapHit([overlay, sector]), overlay);
});

test("specific map objects precede sector and island fallbacks", () => {
  const district = hit("area-hit", "island", { kind: "district" });
  const sector = hit("area-hit", "RT4", { kind: "community" });
  const overlay = hit("parcel-fill", "RT4_TMP_PL2", { category: "overlay" });
  const place = hit("places", "place");
  const street = hit("streets", "street");
  assert.equal(selectMapHit([district, sector]), sector);
  assert.equal(selectMapHit([district]), district);
  assert.equal(selectMapHit([district, overlay, street]), street);
  assert.equal(selectMapHit([overlay, street, place]), place);
  assert.equal(selectMapHit([]), null);
  assert.equal(selectMapHit([{ layer: { id: "buildings" } }]), null);
  assert.equal(selectMapHit([hit("unrelated-label", "unknown")]), null);
});

test("exports preserve original text and neutralize spreadsheet formulas", () => {
  const result = csv([["=1+1", 'name, "quoted"', "  +SUM(A1)", "normal"]]);
  assert.ok(result.includes("'=1+1"));
  assert.ok(result.includes("'  +SUM(A1)"));
  assert.ok(result.includes('"name, ""quoted"""'));
});

test("search handles accents and source names without translating evidence", () => {
  assert.equal(normalized("Île de Reem"), "ile de reem");
  assert.equal(normalized("الريم"), "الريم");
});

test("camera bounds preserve all polygon parts and holes", () => {
  assert.deepEqual(
    geometryBounds({
      type: "MultiPolygon",
      coordinates: [
        [
          [
            [54.4, 24.5],
            [54.42, 24.51],
            [54.4, 24.5],
          ],
          [
            [54.405, 24.503],
            [54.406, 24.504],
            [54.405, 24.503],
          ],
        ],
        [
          [
            [54.43, 24.49],
            [54.44, 24.495],
            [54.43, 24.49],
          ],
        ],
      ],
    }),
    [
      [54.4, 24.49],
      [54.44, 24.51],
    ],
  );
});
