import assert from "node:assert/strict";
import test from "node:test";
import { building3DLayers } from "../src/features/atlas/building-3d.ts";
import {
  CONTEXT_SOURCE,
  contextTileSource,
  syncContextStates,
  tiledContextLayers,
} from "../src/features/atlas/context-tiles.ts";

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
