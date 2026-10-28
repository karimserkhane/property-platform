import type {
  ExpressionSpecification,
  LayerSpecification,
  Map as LibreMap,
} from "maplibre-gl";

export type BuildingView = {
  dimension: "2d" | "3d";
  buildingSource: "catalogue" | "openstreetmap";
  estimatedHeights: boolean;
};

export function buildingViewSelection(
  search: URLSearchParams | null,
): BuildingView {
  return {
    dimension: search?.get("view") === "3d" ? "3d" : "2d",
    buildingSource:
      search?.get("buildings3d") === "catalogue"
        ? "catalogue"
        : "openstreetmap",
    estimatedHeights: search?.get("estimates") !== "off",
  };
}

// Display-only estimates. Never write these values into the building catalogue.
export function displayHeight(
  height: unknown,
  levels: unknown,
  estimates: boolean,
) {
  if (
    typeof height === "number" &&
    Number.isFinite(height) &&
    height > 0 &&
    height <= 1500
  )
    return { metres: height, basis: "recorded" as const };
  if (!estimates) return null;
  if (
    typeof levels === "number" &&
    Number.isFinite(levels) &&
    levels > 0 &&
    levels <= 300
  )
    return { metres: levels * 3, basis: "levels" as const };
  return { metres: 3, basis: "footprint" as const };
}

// GeoJSON rows carry heights as properties; context tiles as feature state.
type Read = "get" | "feature-state";
const height = (read: Read): ExpressionSpecification => [
  "to-number",
  [read, "height_m"],
  0,
];
const levels: ExpressionSpecification = ["to-number", ["get", "levels"], 0];
const recorded = (read: Read): ExpressionSpecification => [
  "all",
  [">", height(read), 0],
  ["<=", height(read), 1500],
];
const heightExpression: ExpressionSpecification = [
  "case",
  recorded("get"),
  height("get"),
  ["all", [">", levels, 0], ["<=", levels, 300]],
  ["*", levels, 3],
  3,
];
export const BUILDING_3D_COLORS = {
  recorded: "#8aa99a",
  estimated: "#d8c6a2",
  selected: "#eb7939",
} as const;

export function building3DLayers(): LayerSpecification[] {
  return [
    {
      id: "buildings-3d",
      type: "fill-extrusion",
      source: "building",
      minzoom: 13,
      layout: { visibility: "none" },
      paint: {
        "fill-extrusion-height": heightExpression,
        "fill-extrusion-color": catalogueColor(null, "get"),
        "fill-extrusion-opacity": 0.94,
        "fill-extrusion-vertical-gradient": true,
      },
    },
    {
      id: "world-buildings-3d",
      type: "fill-extrusion",
      source: "hydrography",
      "source-layer": "building",
      minzoom: 13,
      layout: { visibility: "none" },
      filter: [
        "all",
        ["!=", ["get", "hide_3d"], true],
        [">", ["to-number", ["get", "render_height"], 0], 0],
      ],
      paint: {
        "fill-extrusion-height": [
          "min",
          1500,
          ["to-number", ["get", "render_height"], 3],
        ],
        "fill-extrusion-base": [
          "max",
          0,
          ["to-number", ["get", "render_min_height"], 0],
        ],
        "fill-extrusion-color": BUILDING_3D_COLORS.estimated,
        "fill-extrusion-opacity": 0.94,
        "fill-extrusion-vertical-gradient": true,
      },
    },
  ];
}

function catalogueColor(
  selected: string | null,
  read: Read,
): ExpressionSpecification {
  return [
    "case",
    ["==", ["get", "id"], selected ?? ""],
    BUILDING_3D_COLORS.selected,
    recorded(read),
    BUILDING_3D_COLORS.recorded,
    BUILDING_3D_COLORS.estimated,
  ];
}

export function applyBuildingView(
  map: LibreMap,
  view: BuildingView,
  buildings = true,
  selected: string | null = null,
  // Tiled buildings: heights are feature state, which a filter cannot read,
  // so "recorded only" keeps the listed identities with a recorded height.
  tiled: { recorded: readonly string[] } | null = null,
) {
  const enabled = view.dimension === "3d" && buildings;
  for (const [id, visible] of [
    ["buildings", buildings && !enabled],
    ["buildings-3d", enabled && view.buildingSource === "catalogue"],
    ["world-buildings-3d", enabled && view.buildingSource === "openstreetmap"],
  ] as const) {
    if (map.getLayer(id))
      map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
  }
  if (map.getLayer("buildings-3d")) {
    map.setFilter(
      "buildings-3d",
      view.estimatedHeights
        ? null
        : tiled
          ? ["in", ["get", "id"], ["literal", [...tiled.recorded]]]
          : recorded("get"),
    );
    map.setPaintProperty(
      "buildings-3d",
      "fill-extrusion-color",
      catalogueColor(selected, tiled ? "feature-state" : "get"),
    );
  }
}

export function setBuildingCamera(
  map: LibreMap,
  dimension: BuildingView["dimension"],
  reducedMotion: boolean,
) {
  map.easeTo({
    pitch: dimension === "3d" ? 55 : 0,
    ...(dimension === "3d"
      ? { zoom: Math.max(map.getZoom(), 15) }
      : { bearing: 0 }),
    duration: reducedMotion ? 0 : 600,
  });
}
