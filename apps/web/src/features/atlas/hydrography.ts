import type {
  LayerSpecification,
  VectorSourceSpecification,
} from "maplibre-gl";

// Basemap context only: these OSM geometries never establish parcel boundaries.
export const PLAN_COLORS = { land: "#f5f3ec", water: "#afd5df" } as const;
export const HYDROGRAPHY_CREDIT =
  "OpenFreeMap · © OpenMapTiles · © OpenStreetMap";
export const HYDROGRAPHY_SOURCE: VectorSourceSpecification = {
  type: "vector",
  tiles: ["archive://openfreemap/{z}/{x}/{y}"],
  minzoom: 0,
  maxzoom: 14,
  attribution: HYDROGRAPHY_CREDIT,
};
export const HYDROGRAPHY_LAYERS: LayerSpecification[] = [
  {
    id: "plan-water",
    type: "fill",
    source: "hydrography",
    "source-layer": "water",
    filter: ["!=", ["get", "brunnel"], "tunnel"],
    paint: { "fill-color": PLAN_COLORS.water },
  },
  {
    id: "plan-waterways",
    type: "line",
    source: "hydrography",
    "source-layer": "waterway",
    filter: [
      "all",
      ["!=", ["get", "brunnel"], "tunnel"],
      ["!=", ["get", "intermittent"], 1],
    ],
    paint: {
      "line-color": PLAN_COLORS.water,
      "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.6, 16, 3],
    },
  },
];
