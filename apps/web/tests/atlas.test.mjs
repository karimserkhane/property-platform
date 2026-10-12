import assert from "node:assert/strict";
import test from "node:test";
import {
  csv,
  geometryBounds,
  normalized,
} from "../src/features/atlas/presentation.ts";

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
