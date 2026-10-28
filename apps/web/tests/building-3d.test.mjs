import assert from "node:assert/strict";
import { realpathSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import {
  applyBuildingView,
  building3DLayers,
  buildingViewSelection,
  displayHeight,
  setBuildingCamera,
} from "../src/features/atlas/building-3d.ts";
import { selectMapHit } from "../src/features/atlas/presentation.ts";

const require = createRequire(
  realpathSync(
    new URL("../node_modules/maplibre-gl/package.json", import.meta.url),
  ),
);
const {
  createExpression,
  validateStyleMin,
} = require("@maplibre/maplibre-gl-style-spec");
const layers = building3DLayers();
const expression = (value) => {
  const result = createExpression(
    value,
    "layers[0].paint.fill-extrusion-height",
  );
  assert.equal(result.result, "success", JSON.stringify(result.value));
  return (properties) => result.value.evaluate({ zoom: 16 }, { properties });
};

test("3D style validates against MapLibre and uses only existing archived sources", () => {
  const errors = validateStyleMin({
    version: 8,
    sources: {
      building: {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      },
      hydrography: {
        type: "vector",
        tiles: ["archive://openfreemap/{z}/{x}/{y}"],
        maxzoom: 14,
      },
    },
    layers,
  });
  assert.deepEqual(
    errors.map((error) => error.message),
    [],
  );
});

test("recorded heights take precedence; floor and footprint estimates are reversible display values", () => {
  const metres = expression(layers[0].paint["fill-extrusion-height"]);
  for (const [height, levels, expected, basis] of [
    [123.5, 12, 123.5, "recorded"],
    [null, 20, 60, "levels"],
    [null, null, 3, "footprint"],
    [-10, 2, 6, "levels"],
    [2000, 301, 3, "footprint"],
  ]) {
    const original = { height_m: height, levels };
    assert.equal(metres(original), expected);
    assert.deepEqual(displayHeight(height, levels, true), {
      metres: expected,
      basis,
    });
    assert.deepEqual(original, { height_m: height, levels });
  }
  assert.equal(displayHeight(null, 20, false), null);
  assert.equal(displayHeight(null, null, false), null);
});

test("only one 3D building source can be visible, and returning to 2D restores footprints", () => {
  const shown = {};
  let filter;
  const map = {
    getLayer: () => true,
    setLayoutProperty: (id, _key, value) => {
      shown[id] = value;
    },
    setFilter: (_id, value) => {
      filter = value;
    },
    setPaintProperty: () => {},
  };
  for (const source of ["catalogue", "openstreetmap"]) {
    applyBuildingView(map, {
      dimension: "3d",
      buildingSource: source,
      estimatedHeights: false,
    });
    assert.deepEqual(
      Object.keys(shown).filter((id) => shown[id] === "visible"),
      [source === "catalogue" ? "buildings-3d" : "world-buildings-3d"],
    );
  }
  const accepts = expression(filter);
  assert.equal(accepts({ height_m: null, levels: 40 }), false);
  assert.equal(accepts({ height_m: 120 }), true);
  applyBuildingView(map, buildingViewSelection(null));
  assert.deepEqual(
    Object.keys(shown).filter((id) => shown[id] === "visible"),
    ["buildings"],
  );
  applyBuildingView(
    map,
    { dimension: "3d", buildingSource: "catalogue", estimatedHeights: true },
    false,
  );
  assert.ok(Object.values(shown).every((visibility) => visibility === "none"));
});

test("shared URLs preserve 3D choices across territory and locale changes without accepting arbitrary providers", () => {
  const url = new URL(
    "https://example.com/fr/explore?view=3d&buildings3d=catalogue&estimates=off&basemap=sentinel-worldcover-2021",
  );
  url.pathname = "/ar/explore";
  url.searchParams.set("territory", "saadiyat-island");
  assert.deepEqual(buildingViewSelection(url.searchParams), {
    dimension: "3d",
    buildingSource: "catalogue",
    estimatedHeights: false,
  });
  assert.deepEqual(
    buildingViewSelection(
      new URLSearchParams("view=bad&buildings3d=https://evil.example"),
    ),
    buildingViewSelection(null),
  );
});

test("3D camera reveals buildings without zooming out a selected project and respects reduced motion", () => {
  let result;
  const map = {
    getZoom: () => 17.2,
    easeTo: (options) => {
      result = options;
    },
  };
  setBuildingCamera(map, "3d", true);
  assert.equal(result.pitch, 55);
  assert.equal(result.zoom, 17.2);
  assert.equal(result.duration, 0);
  setBuildingCamera(map, "2d", false);
  assert.equal(result.pitch, 0);
  assert.equal(result.bearing, 0);
  assert.equal(result.zoom, undefined);
});

test("a rendered building roof opens its catalogue identity while project markers retain priority", () => {
  const roof = {
    layer: { id: "buildings-3d" },
    properties: { id: "building" },
  };
  const parcel = { layer: { id: "parcel-fill" }, properties: { id: "parcel" } };
  const project = {
    layer: { id: "places" },
    properties: { id: "project", kind: "publisher_project_marker" },
  };
  assert.equal(selectMapHit([parcel, roof]), roof);
  assert.equal(selectMapHit([roof, project, parcel]), project);
});
