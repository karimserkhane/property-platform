import type { ExpressionSpecification, Map as LibreMap } from "maplibre-gl";
import type { AtlasContext, MapFeature } from "./types";

const circle = "M12 1a11 11 0 1 0 0 22 11 11 0 0 0 0-22Z";
const square =
  "M6 1h12a5 5 0 0 1 5 5v12a5 5 0 0 1-5 5H6a5 5 0 0 1-5-5V6a5 5 0 0 1 5-5Z";
const diamond = "M12 1 23 12 12 23 1 12Z";

// Presentation of recorded semantics only. Names and proximity never set a role.
// Paths are shared by the in-map images and the accessible HTML legend.
export const MAP_MARKERS = {
  project: {
    color: "#c65a28",
    frame: diamond,
    paths: ["M8 16V9h5v7M13 11h3v5M10.5 11v1M10.5 14v1"],
    label: "projectReference",
  },
  education: {
    color: "#6554a4",
    frame: square,
    paths: ["m5 9 7-3 7 3-7 3-7-3Zm3 2v5c3 2 5 2 8 0v-5M19 9v6"],
    label: "nearbyEducation",
  },
  health: {
    color: "#b74460",
    frame: circle,
    paths: ["M12 6v12M6 12h12"],
    label: "nearbyHealth",
  },
  shopping: {
    color: "#946a27",
    frame: square,
    paths: ["M6 9h12l1 9H5l1-9ZM9 9V7a3 3 0 0 1 6 0v2"],
    label: "nearbyShopping",
  },
  transport: {
    color: "#31679d",
    frame: square,
    paths: ["M7 6h10v11H7V6ZM7 12h10M9 17v2M15 17v2M9 15h.1M15 15h.1"],
    label: "nearbyTransport",
  },
  leisure: {
    color: "#347654",
    frame: circle,
    paths: ["m12 5-5 6h3l-4 5h12l-4-5h3l-5-6ZM12 16v3"],
    label: "nearbyLeisure",
  },
  dining: {
    color: "#a65033",
    frame: circle,
    paths: ["M6 6v5a2 2 0 0 0 4 0V6M8 6v13M17 6v13M17 6c-4 2-4 7 0 7"],
    label: "nearbyDining",
  },
  worship: {
    color: "#79528d",
    frame: diamond,
    paths: ["M7 17v-5c0-3 5-5 5-6 0 1 5 3 5 6v5H7ZM12 13v4"],
    label: "nearbyWorship",
  },
  hotel: {
    color: "#48657f",
    frame: square,
    paths: ["M5 8v10M19 12v6M5 15h14M9 10h7a3 3 0 0 1 3 3v2M6 10h3v4H6"],
    label: "nearbyHotels",
  },
  other: {
    color: "#547775",
    frame: circle,
    paths: ["M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"],
    label: "otherPlaces",
  },
} as const;
export type MapMarkerCategory = keyof typeof MAP_MARKERS;
type Role = Exclude<MapMarkerCategory, "project" | "other">;
const USE_ROLES: Record<Role, readonly string[]> = {
  education: ["school", "nursery", "university"],
  health: ["hospital", "healthcare"],
  shopping: ["retail"],
  transport: ["rail_station", "bus_station", "bus_stop"],
  leisure: ["park", "open_space", "beach", "sports"],
  dining: ["restaurant", "cafe"],
  worship: ["mosque", "worship"],
  hotel: ["hotel"],
};
const KIND_ROLES: Record<Role, readonly string[]> = {
  education: ["school", "nursery", "kindergarten", "college", "university"],
  health: [
    "hospital",
    "clinic",
    "doctors",
    "dentist",
    "pharmacy",
    "healthcare",
  ],
  shopping: [
    "retail",
    "shop",
    "supermarket",
    "convenience",
    "mall",
    "marketplace",
  ],
  transport: [
    "bus_stop",
    "bus_station",
    "halt",
    "tram_stop",
    "platform",
    "stop_position",
  ],
  leisure: [
    "park",
    "garden",
    "beach",
    "playground",
    "sports_centre",
    "fitness_centre",
    "swimming_pool",
    "pitch",
  ],
  dining: ["restaurant", "cafe", "fast_food", "food_court", "bar"],
  worship: ["place_of_worship", "mosque", "church", "temple"],
  hotel: ["hotel", "resort", "motel", "guest_house"],
};
const PROJECT_MARKER_SUFFIX = "_project_marker";
export const PROJECT_MARKER_FILTER: ExpressionSpecification = [
  "==",
  [
    "slice",
    ["to-string", ["get", "kind"]],
    [
      "max",
      0,
      [
        "-",
        ["length", ["to-string", ["get", "kind"]]],
        PROJECT_MARKER_SUFFIX.length,
      ],
    ],
  ],
  PROJECT_MARKER_SUFFIX,
];
const markerId = (category: MapMarkerCategory) => `map-marker-${category}`;
export const PROJECT_MARKER_IMAGE = markerId("project");

export function mapMarkerCategory(
  properties: Pick<MapFeature["properties"], "kind"> & {
    use_types?: readonly string[];
  },
): MapMarkerCategory {
  if (properties.kind.endsWith(PROJECT_MARKER_SUFFIX)) return "project";
  for (const [role, values] of Object.entries(USE_ROLES))
    if (values.some((value) => properties.use_types?.includes(value)))
      return role as Role;
  for (const [role, values] of Object.entries(KIND_ROLES))
    if (values.includes(properties.kind)) return role as Role;
  return "other";
}

export function mapMarkerCategoryExpression(): ExpressionSpecification {
  const expression: (ExpressionSpecification | string)[] = [
    "case",
    PROJECT_MARKER_FILTER,
    "project",
  ];
  for (const [role, values] of Object.entries(USE_ROLES))
    expression.push(
      [
        "any",
        ...values.map((value) => [
          "in",
          value,
          ["coalesce", ["get", "use_types"], ["literal", []]],
        ]),
      ] as ExpressionSpecification,
      role,
    );
  for (const [role, values] of Object.entries(KIND_ROLES))
    expression.push(["in", ["get", "kind"], ["literal", [...values]]], role);
  expression.push("other");
  return expression as ExpressionSpecification;
}

export function mapMarkerImage(): ExpressionSpecification {
  return ["concat", "map-marker-", mapMarkerCategoryExpression()];
}

const SECONDARY_CATEGORIES = new Set<MapMarkerCategory>([
  "shopping",
  "dining",
  "other",
]);

export function mapPlaceFilter(
  commerce = false,
  places = true,
): ExpressionSpecification {
  return [
    "all",
    ["!", PROJECT_MARKER_FILTER],
    [
      "case",
      [
        "in",
        mapMarkerCategoryExpression(),
        ["literal", [...SECONDARY_CATEGORIES]],
      ],
      commerce,
      places,
    ],
  ];
}

export function presentMarkerCategories(
  context: AtlasContext | null,
  options?: { places?: boolean; commerce?: boolean },
): MapMarkerCategory[] {
  const present = new Set(
    (context?.place.features ?? []).map((item) =>
      mapMarkerCategory(item.properties),
    ),
  );
  return (Object.keys(MAP_MARKERS) as MapMarkerCategory[]).filter(
    (key) =>
      present.has(key) &&
      (key === "project" ||
        !options ||
        (SECONDARY_CATEGORIES.has(key)
          ? options.commerce
          : options.places !== false)),
  );
}

// Local vectors: no icon CDN, remote image fetch or external font dependency.
export function registerMapMarkers(map: LibreMap) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 48;
  const drawing = canvas.getContext("2d");
  if (!drawing) throw new Error("Map marker canvas unavailable");
  drawing.scale(2, 2);
  drawing.lineJoin = drawing.lineCap = "round";
  for (const [category, marker] of Object.entries(MAP_MARKERS)) {
    const id = markerId(category as MapMarkerCategory);
    if (map.hasImage(id)) continue;
    drawing.clearRect(0, 0, 24, 24);
    drawing.fillStyle = marker.color;
    drawing.strokeStyle = "#ffffff";
    drawing.lineWidth = 1.8;
    const frame = new Path2D(marker.frame);
    drawing.fill(frame);
    drawing.stroke(frame);
    drawing.lineWidth = category === "health" ? 3 : 1.5;
    for (const path of marker.paths) drawing.stroke(new Path2D(path));
    const image = drawing.getImageData(0, 0, 48, 48);
    map.addImage(id, image, { pixelRatio: 2 });
  }
}
