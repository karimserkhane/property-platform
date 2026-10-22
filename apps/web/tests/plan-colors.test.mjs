import assert from "node:assert/strict";
import { realpathSync } from "node:fs";
import { createRequire, registerHooks } from "node:module";
import test from "node:test";
import {
  HYDROGRAPHY_LAYERS,
  HYDROGRAPHY_SOURCE,
  PLAN_COLORS,
} from "../src/features/atlas/hydrography.ts";
import {
  COLORS,
  parcelFillColor,
  parcelFillOpacity,
} from "../src/features/atlas/presentation.ts";

// Production uses bundler resolution for extensionless TypeScript imports.
// Limit Node's equivalent resolution to the atlas module being tested here.
const atlasUrl = new URL("../src/features/atlas/", import.meta.url).href;
const resolution = registerHooks({
  resolve(specifier, context, nextResolve) {
    return nextResolve(
      context.parentURL?.startsWith(atlasUrl) && specifier.startsWith("./")
        ? `${specifier}.ts`
        : specifier,
      context,
    );
  },
});
const { mapLayers } = await import("../src/features/atlas/map-style.ts");
const { updateProjectClusters } = await import(
  "../src/features/atlas/project-clusters.ts"
);
resolution.deregister();

const require = createRequire(
  realpathSync(
    new URL("../node_modules/maplibre-gl/package.json", import.meta.url),
  ),
);
const {
  createExpression,
  validateStyleMin,
} = require("@maplibre/maplibre-gl-style-spec");
const evaluate = (value, property) => {
  const compiled = createExpression(value, `layers[0].paint.${property}`);
  assert.equal(compiled.result, "success", JSON.stringify(compiled.value));
  return (zoom, properties) =>
    compiled.value.evaluate({ zoom }, { properties });
};

test("parcel colours match the legend at distant and close-up zooms, including unknown uses", () => {
  const colour = evaluate(parcelFillColor(), "fill-color");
  for (const zoom of [10, 14, 16, 18, 20]) {
    for (const [category, expected] of Object.entries(COLORS))
      assert.equal(colour(zoom, { category }), expected);
    for (const category of [null, "unrecognised"])
      assert.equal(colour(zoom, { category }), COLORS.unknown);
  }
});

test("project and explorer maps share subdued overlay opacity without fading normal parcels on zoom", () => {
  const opacity = evaluate(parcelFillOpacity(false), "fill-opacity");
  for (const zoom of [10, 14, 16, 18, 20]) {
    assert.equal(opacity(zoom, { category: "overlay" }), 0.15);
    for (const category of Object.keys(COLORS).filter(
      (key) => key !== "overlay",
    ))
      assert.equal(opacity(zoom, { category }), 0.86);
  }
  assert.equal(parcelFillOpacity(true), 0.06);
});

test("water retains its colour and stays enabled beyond native tile zoom", () => {
  const water = HYDROGRAPHY_LAYERS.find((layer) => layer.id === "plan-water");
  assert.equal(water.maxzoom, undefined);
  assert.notEqual(water.layout?.visibility, "none");
  assert.equal(water.paint["fill-color"], PLAN_COLORS.water);
  assert.equal(water.paint["fill-opacity"] ?? 1, 1);
  assert.equal(HYDROGRAPHY_SOURCE.maxzoom, 14);
  const errors = validateStyleMin({
    version: 8,
    sources: { hydrography: HYDROGRAPHY_SOURCE },
    layers: HYDROGRAPHY_LAYERS,
  });
  assert.deepEqual(
    errors.map((error) => error.message),
    [],
  );
});

test("water renders over land-use parcels while streets, buildings and selection stay visible", () => {
  const ids = mapLayers("fr").map((layer) => layer.id);
  for (const id of ["land", "parcel-fill", "parcel-line"])
    assert.ok(ids.indexOf(id) < ids.indexOf("plan-water"));
  for (const id of ["streets", "buildings-3d", "selection"])
    assert.ok(ids.indexOf(id) > ids.indexOf("plan-water"));
});

test("all plan and point symbol layers validate against the installed MapLibre specification", () => {
  const layers = mapLayers("fr");
  const sources = Object.fromEntries(
    [...new Set(layers.map((layer) => layer.source))].map((source) => [
      source,
      source === "hydrography"
        ? HYDROGRAPHY_SOURCE
        : layers.some(
              (layer) => layer.source === source && layer.type === "raster",
            )
          ? { type: "raster", tiles: ["https://example.com/{z}/{x}/{y}.png"] }
          : {
              type: "geojson",
              data: { type: "FeatureCollection", features: [] },
            },
    ]),
  );
  const errors = validateStyleMin({ version: 8, sources, layers });
  assert.deepEqual(
    errors.map((error) => error.message),
    [],
  );
  const places = layers.find((layer) => layer.id === "places");
  assert.equal(places.type, "symbol");
  assert.equal(places.minzoom, 14.5);
  assert.notEqual(places.layout["icon-allow-overlap"], true);
});

test("project clusters retain counts and the individual project symbol at both zoom levels", () => {
  const sources = {
    place: {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    },
  };
  const layers = [];
  updateProjectClusters(
    {
      getSource: (id) => sources[id],
      addSource: (id, source) => {
        sources[id] = source;
      },
      addLayer: (layer) => {
        layers.push(layer);
      },
      getLayer: () => null,
      setFilter: () => {},
      setLayerZoomRange: () => {},
      setLayoutProperty: () => {},
    },
    null,
  );
  const errors = validateStyleMin({ version: 8, sources, layers });
  assert.deepEqual(
    errors.map((error) => error.message),
    [],
  );
  assert.equal(
    layers.find((layer) => layer.id === "cluster-projects").type,
    "circle",
  );
  for (const id of ["single-project", "close-project"]) {
    const marker = layers.find((layer) => layer.id === id);
    assert.equal(marker.type, "symbol");
    assert.equal(marker.layout["icon-image"], "map-marker-project");
    assert.equal(marker.layout["icon-allow-overlap"], true);
  }
});
