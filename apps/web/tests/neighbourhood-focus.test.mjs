import assert from "node:assert/strict";
import test from "node:test";
import {
  projectMapPoints,
  projectPointBounds,
} from "../src/features/projects/neighbourhood-focus.ts";

const bounds = [54.385, 24.465, 54.445, 24.53];
const point = (slug, coordinates, name = "The District") => ({
  type: "Feature",
  geometry: { type: "Point", coordinates },
  properties: { name, presentation: { project: { slug } } },
});
const context = (...features) => ({ place: { features } });

test("project framing uses its stored coordinates rather than the island extent", () => {
  const location = [54.399438, 24.497188];
  const points = projectMapPoints(
    context(point("the-district", location)),
    "the-district",
    bounds,
  );
  assert.deepEqual(projectPointBounds(points), [location, location]);
});

test("a matching name or nearby geometry cannot create a project location", () => {
  const points = projectMapPoints(
    context(
      point("other-project", [54.4, 24.5]),
      {
        ...point("the-district", [54.4, 24.5]),
        properties: { name: "The District" },
      },
      {
        ...point("the-district", [54.4, 24.5]),
        geometry: { type: "Polygon", coordinates: [] },
      },
    ),
    "the-district",
    bounds,
  );
  assert.equal(projectPointBounds(points), null);
});

test("invalid and out-of-neighbourhood coordinates cannot move the camera", () => {
  const points = projectMapPoints(
    context(
      point("the-district", [NaN, 24.5]),
      point("the-district", [54.4, Infinity]),
      point("the-district", [55.4, 25.5]),
    ),
    "the-district",
    bounds,
  );
  assert.equal(projectPointBounds(points), null);
});

test("a project with several stored points keeps all its locations in view", () => {
  const points = projectMapPoints(
    context(
      point("the-district", [54.4, 24.5]),
      point("the-district", [54.401, 24.501]),
      point("other-project", [54.44, 24.52]),
    ),
    "the-district",
    bounds,
  );
  assert.deepEqual(projectPointBounds(points), [
    [54.4, 24.5],
    [54.401, 24.501],
  ]);
});
