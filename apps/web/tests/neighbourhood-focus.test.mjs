import assert from "node:assert/strict";
import test from "node:test";
import {
  neighbourhoodContextBounds,
  projectLocationBounds,
} from "../src/features/projects/neighbourhood-focus.ts";

const bounds = [54.385, 24.465, 54.445, 24.53];
const point = (coordinates) => ({ geometry: { type: "Point", coordinates } });

test("project framing uses its stored coordinates rather than the island extent", () => {
  const location = [54.399438, 24.497188];
  assert.deepEqual(projectLocationBounds([point(location)], bounds), [
    location,
    location,
  ]);
});

test("linked building footprints frame all buildings of a project", () => {
  const building = {
    geometry: {
      type: "MultiPolygon",
      coordinates: [
        [
          [
            [54.4, 24.5],
            [54.401, 24.5],
            [54.401, 24.501],
            [54.4, 24.5],
          ],
        ],
      ],
    },
  };
  assert.deepEqual(
    projectLocationBounds([building, point([54.402, 24.502])], bounds),
    [
      [54.4, 24.5],
      [54.402, 24.502],
    ],
  );
});

test("invalid and out-of-neighbourhood coordinates cannot move the camera", () => {
  for (const coordinates of [
    [NaN, 24.5],
    [54.4, Infinity],
    [55.4, 25.5],
    [54.4],
  ]) {
    assert.equal(projectLocationBounds([point(coordinates)], bounds), null);
  }
  assert.equal(projectLocationBounds([], bounds), null);
});

test("a focused project loads nearby context instead of all island geometry", () => {
  const focus = [
    [54.4, 24.5],
    [54.401, 24.501],
  ];
  const box = neighbourhoodContextBounds(focus, bounds);
  assert.ok(box[0] > bounds[0] && box[2] < bounds[2]);
  assert.ok(box[1] > bounds[1] && box[3] < bounds[3]);
  assert.deepEqual(neighbourhoodContextBounds(null, bounds), bounds);
  assert.deepEqual(
    neighbourhoodContextBounds(
      [
        [54.385, 24.465],
        [54.445, 24.53],
      ],
      bounds,
    ),
    bounds,
  );
});
