import assert from "node:assert/strict";
import test from "node:test";
import { boundsGeometry } from "../src/features/atlas/map-analysis.ts";
import {
  PARCEL_LABEL_SOURCE,
  parcelLabelPoints,
  parcelTileSource,
  syncParcelStates,
  tiledParcelLayers,
} from "../src/features/atlas/parcel-tiles.ts";
import {
  nearbyProject,
  nearbyProjectFromDistances,
  parcelFillColor,
  parcelFillOpacity,
  parcelPropertyIndex,
  pointParcelDistance,
} from "../src/features/atlas/presentation.ts";

// The parcel layers of the shared style (map-style.ts), as GeoJSON maps use them.
const sharedLayers = () => [
  {
    id: "parcel-fill",
    type: "fill",
    source: "parcels",
    paint: {
      "fill-color": parcelFillColor(),
      "fill-opacity": parcelFillOpacity(false),
    },
  },
  { id: "parcel-line", type: "line", source: "parcels", paint: {} },
  { id: "selection", type: "line", source: "parcels" },
  { id: "parcel-project-names", type: "symbol", source: "parcels" },
  { id: "parcel-use-names", type: "symbol", source: "parcels" },
  { id: "parcel-codes", type: "symbol", source: "parcels" },
  { id: "streets", type: "line", source: "street" },
];

const ring = (x, y, w) => [
  [x, y],
  [x + w, y],
  [x + w, y + w],
  [x, y + w],
  [x, y],
];
const geometry = {
  type: "MultiPolygon",
  coordinates: [[ring(54.4, 24.5, 0.001)]],
};
const project = (id, x, y, slug) => ({
  id,
  geometry: { type: "Point", coordinates: [x, y] },
  properties: {
    id,
    name: id,
    name_ar: "",
    kind: "publisher_project_marker",
    parcel_ids: [],
    source: { url: `https://example.com/${id}` },
    ...(slug ? { presentation: { project: { slug } } } : {}),
  },
});
// What `parcel-index` reports: PostGIS boundary distances within 50 m.
const distances = (projects) =>
  projects
    .map((item) => ({
      place_id: item.id,
      distance_m: pointParcelDistance(geometry, item.geometry.coordinates),
    }))
    .filter((item) => item.distance_m <= 50);

test("server distances reproduce the footprint choice rules", () => {
  const near = project("near", 54.4012, 24.5005);
  const far = project("far", 54.4016, 24.5005);
  const rival = project("rival", 54.40125, 24.5005);
  const same = project("same", 54.4012, 24.5005, "shared");
  const sibling = project("sibling", 54.40121, 24.5005, "shared");
  for (const projects of [
    [far],
    [far, near],
    [near, rival],
    [same, sibling],
    [sibling, same, far],
  ])
    assert.deepEqual(
      nearbyProjectFromDistances(distances(projects), projects),
      nearbyProject(geometry, projects),
    );
  // A reported marker absent from the published context is never suggested.
  assert.equal(nearbyProjectFromDistances(distances([near]), []), null);
});

test("index rows and footprint rows give the same potential names", () => {
  const near = project("near", 54.4012, 24.5005);
  const context = { place: { features: [near] }, building: { features: [] } };
  const footprints = {
    features: [{ id: "p", geometry, properties: { category: "residential" } }],
  };
  const rows = {
    features: [
      {
        id: "p",
        properties: {
          category: "residential",
          nearby_projects: distances([near]),
        },
      },
    ],
  };
  assert.deepEqual(
    parcelPropertyIndex(context, rows),
    parcelPropertyIndex(context, footprints),
  );
});

test("explorer layers draw tiled footprints and point labels", () => {
  const shared = sharedLayers();
  const tiled = tiledParcelLayers(shared);
  const byId = Object.fromEntries(tiled.map((layer) => [layer.id, layer]));
  for (const id of ["parcel-fill", "parcel-line", "selection"]) {
    assert.equal(byId[id].source, "parcels");
    assert.equal(byId[id]["source-layer"], "parcels");
  }
  for (const id of ["parcel-project-names", "parcel-use-names", "parcel-codes"])
    assert.equal(byId[id].source, PARCEL_LABEL_SOURCE);
  // Unlisted tile features stay invisible; colour comes from published rows.
  const paint = JSON.stringify(byId["parcel-fill"].paint);
  assert.match(paint, /"feature-state","category"/);
  assert.match(paint, /"feature-state","shown"/);
  assert.doesNotMatch(paint, /"get","category"/);
  assert.match(JSON.stringify(byId["parcel-line"].paint), /shown/);
  assert.match(JSON.stringify(byId.selection.paint), /shown/);
  assert.deepEqual(byId.streets, shared.at(-1));
  // The shared style used by project neighbourhood maps is unchanged.
  assert.deepEqual(shared, sharedLayers());
});

test("tile source, label points and bounds stay within the published row", () => {
  const source = parcelTileSource("https://preview.example", "al-reem-island");
  assert.deepEqual(source.tiles, [
    "https://preview.example/api/atlas/parcel-tiles/{z}/{x}/{y}?territory=al-reem-island",
  ]);
  assert.equal(source.promoteId, "id");
  const rows = {
    features: [
      {
        id: "p",
        properties: { code: "RT1", label_point: [54.4005, 24.5005] },
      },
    ],
  };
  const [point] = parcelLabelPoints(rows).features;
  assert.deepEqual(point.geometry.coordinates, [54.4005, 24.5005]);
  assert.equal(point.properties.code, "RT1");
  assert.deepEqual(boundsGeometry([1, 2, 3, 4]).coordinates[0][2], [3, 4]);
});

test("feature state shows listed parcels and hides those no longer listed", () => {
  const calls = [];
  const map = {
    setFeatureState: (target, state) => calls.push([target.id, state]),
  };
  const rows = (...ids) => ({
    features: ids.map((id) => ({ id, properties: { category: "mixed" } })),
  });
  const first = syncParcelStates(map, rows("a", "b"), new Set());
  assert.deepEqual([...first], ["a", "b"]);
  calls.length = 0;
  const second = syncParcelStates(map, rows("b"), first);
  assert.deepEqual([...second], ["b"]);
  assert.deepEqual(calls, [
    ["b", { shown: true, category: "mixed" }],
    ["a", { shown: false }],
  ]);
});
