import assert from "node:assert/strict";
import test from "node:test";
import {
  applyBuildingView,
  building3DLayers,
} from "../src/features/atlas/building-3d.ts";
import {
  CONTEXT_SOURCE,
  contextTileSource,
  indexedContext,
  recordedBuildings,
  syncContextStates,
  tiledContextLayers,
  tiledFootprints,
} from "../src/features/atlas/context-tiles.ts";
import { frameGeometry } from "../src/features/atlas/map-analysis.ts";
import {
  featureBounds,
  featureShape,
} from "../src/features/atlas/presentation.ts";

const sharedLayers = () => [
  { id: "buildings", type: "fill", source: "building", paint: {} },
  ...building3DLayers(),
  { id: "streets", type: "line", source: "street", paint: {} },
  {
    id: "street-names",
    type: "symbol",
    source: "street",
    layout: { "text-field": ["get", "name"] },
  },
  {
    id: "building-selection",
    type: "line",
    source: "building",
    filter: ["==", ["get", "id"], ""],
  },
  { id: "places", type: "circle", source: "place" },
];

test("context tiles are requested per territory within served zooms", () => {
  const source = contextTileSource("https://site.test", "al reem");
  assert.deepEqual(source.tiles, [
    "https://site.test/api/atlas/context-tiles/{z}/{x}/{y}?territory=al%20reem",
  ]);
  assert.equal(source.minzoom, 11);
  assert.equal(source.maxzoom, 16);
  assert.equal(source.promoteId, "id");
});

test("building and street layers move to tiles; others stay", () => {
  const byId = Object.fromEntries(
    tiledContextLayers(sharedLayers()).map((layer) => [layer.id, layer]),
  );
  for (const [id, family] of [
    ["buildings", "building"],
    ["buildings-3d", "building"],
    ["building-selection", "building"],
    ["streets", "street"],
    ["street-names", "street"],
  ]) {
    assert.equal(byId[id].source, CONTEXT_SOURCE, id);
    assert.equal(byId[id]["source-layer"], family, id);
  }
  // Selection filters and street labels read tile properties.
  assert.deepEqual(byId["building-selection"].filter, [
    "==",
    ["get", "id"],
    "",
  ]);
  assert.deepEqual(byId["street-names"].layout["text-field"], ["get", "name"]);
  // OpenMapTiles buildings and places are untouched.
  assert.equal(byId["world-buildings-3d"].source, "hydrography");
  assert.equal(byId["world-buildings-3d"]["source-layer"], "building");
  assert.equal(byId.places.source, "place");
  assert.equal(byId.places["source-layer"], undefined);
  // Catalogue heights come from the index through feature state.
  const height = JSON.stringify(
    byId["buildings-3d"].paint["fill-extrusion-height"],
  );
  assert.match(height, /\["feature-state","height_m"\]/);
  assert.match(height, /\["feature-state","levels"\]/);
  assert.doesNotMatch(height, /"get"/);
});

test("index rows become feature state and stale rows are cleared", () => {
  const calls = [];
  const map = {
    setFeatureState: (target, state) => calls.push(["set", target, state]),
    removeFeatureState: (target) => calls.push(["remove", target]),
  };
  const row = (id, properties = {}) => ({ id, type: "Feature", properties });
  const first = syncContextStates(
    map,
    {
      building: { features: [row("b1", { height_m: 42, levels: 12 })] },
      street: { features: [row("s1")] },
    },
    new Map(),
  );
  assert.deepEqual(
    [...first],
    [
      ["b1", "building"],
      ["s1", "street"],
    ],
  );
  assert.deepEqual(calls[0], [
    "set",
    { source: CONTEXT_SOURCE, sourceLayer: "building", id: "b1" },
    { height_m: 42, levels: 12 },
  ]);
  assert.deepEqual(calls[1][2], { height_m: null, levels: null });
  calls.length = 0;
  const second = syncContextStates(
    map,
    { building: { features: [] }, street: { features: [row("s1")] } },
    first,
  );
  assert.deepEqual([...second.keys()], ["s1"]);
  assert.deepEqual(calls.at(-1), [
    "remove",
    { source: CONTEXT_SOURCE, sourceLayer: "building", id: "b1" },
  ]);
});

const indexRow = (id, properties = {}) => ({
  id,
  type: "Feature",
  properties: { id, bounds: [54.39, 24.49, 54.41, 24.5], ...properties },
});
const index = () => ({
  building: {
    type: "FeatureCollection",
    truncated: false,
    features: [
      indexRow("b1", { height_m: 42 }),
      indexRow("b2", { height_m: null, levels: 20 }),
      indexRow("b3", { height_m: 2000 }),
    ],
  },
  street: {
    type: "FeatureCollection",
    truncated: true,
    features: [indexRow("s1")],
  },
  place: { type: "FeatureCollection", truncated: false, features: [] },
  administrative_area: {
    type: "FeatureCollection",
    truncated: false,
    features: [],
  },
});

test("index rows keep their family; shape and frame never invent a footprint", () => {
  const context = indexedContext(index());
  const [building] = context.building.features;
  const [street] = context.street.features;
  assert.equal(building.family, "building");
  assert.equal(context.street.truncated, true);
  assert.equal("geometry" in building, false);
  assert.equal(featureShape(building), "MultiPolygon");
  assert.equal(featureShape(street), "MultiLineString");
  assert.deepEqual(featureBounds(street), [
    [54.39, 24.49],
    [54.41, 24.5],
  ]);
  // Bounds only frame the camera; drawing and hits use the tiles.
  assert.equal(frameGeometry(building).type, "Polygon");
  const point = {
    id: "p1",
    type: "Feature",
    geometry: { type: "Point", coordinates: [54.4, 24.5] },
    properties: {},
  };
  assert.equal(featureShape(point), "Point");
  assert.equal(frameGeometry(point), point.geometry);
});

test("recorded-only 3D keeps listed identities with a recorded height", () => {
  const recorded = recordedBuildings(indexedContext(index()));
  assert.deepEqual(recorded, ["b1"]);
  const calls = {};
  const map = {
    getLayer: () => true,
    setLayoutProperty: () => {},
    setFilter: (id, value) => {
      calls[id] = value;
    },
    setPaintProperty: (id, key, value) => {
      calls[`${id}:${key}`] = value;
    },
  };
  const view = {
    dimension: "3d",
    buildingSource: "catalogue",
    estimatedHeights: false,
  };
  applyBuildingView(map, view, true, "b1", { recorded });
  assert.deepEqual(calls["buildings-3d"], [
    "in",
    ["get", "id"],
    ["literal", ["b1"]],
  ]);
  const color = JSON.stringify(calls["buildings-3d:fill-extrusion-color"]);
  assert.match(color, /["feature-state","height_m"]/);
  applyBuildingView(map, { ...view, estimatedHeights: true }, true, null, {
    recorded,
  });
  assert.equal(calls["buildings-3d"], null);
});

test("shadow footprints come from loaded tiles with index heights", () => {
  const square = [
    [
      [54.4, 24.5],
      [54.401, 24.5],
      [54.401, 24.501],
      [54.4, 24.5],
    ],
  ];
  const map = {
    getSource: (id) => (id === CONTEXT_SOURCE ? {} : undefined),
    querySourceFeatures: (source, options) => {
      assert.equal(source, CONTEXT_SOURCE);
      assert.equal(options.sourceLayer, "building");
      return [
        {
          properties: { id: "b1" },
          geometry: { type: "Polygon", coordinates: square },
        },
        {
          properties: { id: "b9" },
          geometry: { type: "Polygon", coordinates: square },
        },
        {
          properties: { id: "b2" },
          geometry: { type: "MultiPolygon", coordinates: [square] },
        },
      ];
    },
  };
  const footprints = tiledFootprints(map, indexedContext(index()));
  assert.deepEqual(
    footprints.map((f) => [f.id, f.geometry.type, f.properties.height_m]),
    [
      ["b1", "MultiPolygon", 42],
      ["b2", "MultiPolygon", null],
    ],
  );
  assert.deepEqual(footprints[0].geometry.coordinates, [square]);
  assert.deepEqual(tiledFootprints({ getSource: () => undefined }, null), []);
});
