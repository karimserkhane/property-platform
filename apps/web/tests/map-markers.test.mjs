import assert from "node:assert/strict";
import { realpathSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import {
  MAP_MARKERS,
  mapMarkerCategory,
  mapMarkerImage,
  mapPlaceFilter,
  PROJECT_MARKER_FILTER,
  presentMarkerCategories,
} from "../src/features/atlas/map-markers.ts";

const require = createRequire(
  realpathSync(
    new URL("../node_modules/maplibre-gl/package.json", import.meta.url),
  ),
);
const { createExpression } = require("@maplibre/maplibre-gl-style-spec");
const compiled = (expression) => {
  const result = createExpression(expression, "layers[0].layout.icon-image");
  assert.equal(result.result, "success", JSON.stringify(result.value));
  return (properties) => result.value.evaluate({ zoom: 16 }, { properties });
};

test("map symbols and legend use the same recorded categories without guessing from names", () => {
  const image = compiled(mapMarkerImage());
  for (const [properties, expected] of [
    [{ kind: "publisher_project_marker", use_types: ["housing"] }, "project"],
    [{ kind: "broker_project_marker", use_types: [] }, "project"],
    [{ kind: "school" }, "education"],
    [{ kind: "kindergarten" }, "education"],
    [{ kind: "pharmacy" }, "health"],
    [{ kind: "station", use_types: ["rail_station"] }, "transport"],
    [{ kind: "bus_stop" }, "transport"],
    [{ kind: "supermarket" }, "shopping"],
    [{ kind: "restaurant" }, "dining"],
    [{ kind: "garden" }, "leisure"],
    [{ kind: "place_of_worship" }, "worship"],
    [{ kind: "resort" }, "hotel"],
    [{ kind: "school", use_types: ["retail"] }, "shopping"],
    [{ kind: "unknown", name: "Marina School Hospital Mall" }, "other"],
    [{ kind: "station", use_types: ["infrastructure"] }, "other"],
    [{ kind: "publisher_project_marker_archived" }, "other"],
  ]) {
    assert.equal(mapMarkerCategory(properties), expected);
    assert.equal(image(properties), `map-marker-${expected}`);
  }
});

test("legend only lists recorded types, in a stable order and without duplicate entrances", () => {
  const context = {
    place: {
      features: [
        { properties: { kind: "cafe" } },
        { properties: { kind: "clinic" } },
        { properties: { kind: "hospital" } },
        { properties: { kind: "publisher_project_marker" } },
      ],
    },
  };
  assert.deepEqual(presentMarkerCategories(context), [
    "project",
    "health",
    "dining",
  ]);
  assert.deepEqual(presentMarkerCategories(null), []);
  assert.equal(
    new Set(Object.values(MAP_MARKERS).map((marker) => marker.paths.join("|")))
      .size,
    Object.keys(MAP_MARKERS).length,
  );
});

test("project symbol filters preserve the same strict identity suffix used by selection", () => {
  const project = compiled(PROJECT_MARKER_FILTER);
  for (const kind of [
    "publisher_project_marker",
    "broker_project_marker",
    "catalogue_project_marker",
  ])
    assert.equal(project({ kind }), true);
  for (const kind of [
    "project",
    "place",
    "publisher_project_marker_archived",
    "",
  ])
    assert.equal(project({ kind }), false);
});

test("useful amenities and shops switch independently without hiding projects from the legend", () => {
  const defaults = compiled(mapPlaceFilter());
  const shopsOnly = compiled(mapPlaceFilter(true, false));
  for (const kind of ["school", "hospital", "park", "bus_stop"])
    assert.equal(defaults({ kind }), true);
  for (const kind of [
    "shop",
    "cafe",
    "restaurant",
    "office",
    "publisher_project_marker",
  ])
    assert.equal(defaults({ kind }), false);
  assert.equal(shopsOnly({ kind: "school" }), false);
  assert.equal(shopsOnly({ kind: "cafe" }), true);
  const context = {
    place: {
      features: [
        { properties: { kind: "publisher_project_marker" } },
        { properties: { kind: "shop" } },
        { properties: { kind: "school" } },
      ],
    },
  };
  assert.deepEqual(
    presentMarkerCategories(context, { places: false, commerce: false }),
    ["project"],
  );
  assert.deepEqual(
    presentMarkerCategories(context, { places: true, commerce: false }),
    ["project", "education"],
  );
});
