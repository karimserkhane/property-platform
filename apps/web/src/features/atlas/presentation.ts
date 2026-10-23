import type { ExpressionSpecification } from "maplibre-gl";
import type {
  MapContext,
  MapFeature,
  MapLabels,
  ParcelCollection,
  ParcelRows,
} from "./types";

type PropertyIdentity = Pick<
  MapFeature["properties"],
  "name" | "name_ar" | "kind" | "presentation"
>;
export type ParcelProperty = PropertyIdentity & {
  id: string;
  feature: MapFeature | null;
  spatial_match?: {
    method: "boundary-proximity-v1";
    distance_m: number;
    source_feature_id: string;
  };
};

// A display preference never accepts a commercial/cadastral identity link.
export function propertyName(p: PropertyIdentity, locale: string): string {
  return (
    (locale === "ar" && p.name_ar.trim()) ||
    p.presentation?.name.trim() ||
    p.name.trim() ||
    p.name_ar.trim() ||
    p.presentation?.developer.trim() ||
    p.presentation?.publisher.trim() ||
    ""
  );
}

const buildingKinds = new Set([
  "yes",
  "apartments",
  "residential",
  "commercial",
  "retail",
  "office",
  "hotel",
  "industrial",
  "house",
  "detached",
  "terrace",
]);
const isProperty = (p: ParcelProperty) =>
  p.kind.endsWith("_project_marker") ||
  p.feature?.geometry.type === "MultiPolygon" ||
  buildingKinds.has(p.kind);

export function preferredParcelProperty(
  candidates: readonly ParcelProperty[],
  locale: string,
): ParcelProperty | null {
  const named = (p: ParcelProperty) =>
    Boolean(p.name.trim() || p.name_ar.trim() || p.presentation?.name.trim());
  return (
    candidates
      .filter((p) => isProperty(p) && propertyName(p, locale))
      .sort(
        (a, b) =>
          Number(Boolean(a.spatial_match)) - Number(Boolean(b.spatial_match)) ||
          Number(named(b)) - Number(named(a)) ||
          Number(Boolean(b.presentation)) - Number(Boolean(a.presentation)) ||
          Number(b.kind.endsWith("_project_marker")) -
            Number(a.kind.endsWith("_project_marker")) ||
          propertyName(a, locale).localeCompare(
            propertyName(b, locale),
            locale,
          ) ||
          a.id.localeCompare(b.id),
      )[0] ?? null
  );
}

export function parcelPropertyIndex(
  context: MapContext | null,
  parcels?: ParcelRows | null,
) {
  const index = new Map<string, ParcelProperty[]>();
  // OSM exposes the same way as footprint and point. Enrich by exact source
  // identity only, never by a similar name or nearest building.
  const buildings = new Map(
    (context?.building.features ?? [])
      .filter((f) => f.properties.source.url)
      .map((f) => [f.properties.source.url, f]),
  );
  for (const f of [
    ...(context?.building.features ?? []),
    ...(context?.place.features ?? []),
  ]) {
    const building = buildings.get(f.properties.source.url);
    const original = building ?? f;
    const candidate = {
      ...original.properties,
      id: original.id,
      feature: original,
    };
    for (const id of f.properties.parcel_ids) {
      const candidates = index.get(id) ?? [];
      if (!candidates.some((p) => p.id === candidate.id))
        candidates.push(candidate);
      index.set(id, candidates);
    }
  }
  const projects = (context?.place.features ?? []).filter(
    (f) =>
      f.geometry.type === "Point" &&
      f.properties.kind.endsWith("_project_marker") &&
      Boolean(
        f.properties.name.trim() ||
          f.properties.name_ar.trim() ||
          f.properties.presentation?.name.trim(),
      ),
  );
  for (const parcel of parcels?.features ?? []) {
    if (
      !["mixed", "residential"].includes(parcel.properties.category) ||
      preferredParcelProperty(index.get(parcel.id) ?? [], "en")
    )
      continue;
    const match =
      "geometry" in parcel
        ? nearbyProject(parcel.geometry, projects)
        : nearbyProjectFromDistances(
            parcel.properties.nearby_projects ?? [],
            projects,
          );
    if (!match) continue;
    const f = match.feature;
    index.set(parcel.id, [
      ...(index.get(parcel.id) ?? []),
      {
        ...f.properties,
        id: f.id,
        feature: f,
        spatial_match: {
          method: "boundary-proximity-v1",
          distance_m: match.distance_m,
          source_feature_id: f.id,
        },
      },
    ]);
  }
  return index;
}

// Local metric approximation for display suggestions only; never cadastral evidence.
// A point in a hole is outside the parcel. Distances are to the actual footprint.
export function pointParcelDistance(
  geometry: MapFeature["geometry"],
  point: readonly [number, number],
): number {
  if (geometry.type !== "MultiPolygon") return Infinity;
  const [lng, lat] = point;
  const sy = (6371008.8 * Math.PI) / 180,
    sx = sy * Math.cos((lat * Math.PI) / 180);
  let distance = Infinity;
  for (const rings of geometry.coordinates as number[][][][]) {
    const inside: boolean[] = [];
    for (const ring of rings) {
      let contains = false;
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const ax = (ring[j][0] - lng) * sx,
          ay = (ring[j][1] - lat) * sy;
        const bx = (ring[i][0] - lng) * sx,
          by = (ring[i][1] - lat) * sy;
        const dx = bx - ax,
          dy = by - ay;
        const t = Math.max(
          0,
          Math.min(1, -(ax * dx + ay * dy) / (dx * dx + dy * dy || 1)),
        );
        distance = Math.min(distance, Math.hypot(ax + t * dx, ay + t * dy));
        if (ay > 0 !== by > 0 && 0 < ax - (ay * dx) / (by - ay))
          contains = !contains;
      }
      inside.push(contains);
    }
    if (inside[0] && !inside.slice(1).some(Boolean)) return 0;
  }
  return distance;
}

export function nearbyProject(
  geometry: MapFeature["geometry"],
  projects: readonly MapFeature[],
): { feature: MapFeature; distance_m: number } | null {
  const bounds = geometryBounds(geometry);
  if (!bounds || geometry.type !== "MultiPolygon") return null;
  const candidates = new Map<
    string,
    { feature: MapFeature; distance_m: number }
  >();
  for (const feature of projects) {
    if (feature.geometry.type !== "Point") continue;
    const point = feature.geometry.coordinates as [number, number];
    // Broad bounding prefilter before inspecting the rings (50 m at UAE latitude).
    if (
      point[0] < bounds[0][0] - 0.0006 ||
      point[0] > bounds[1][0] + 0.0006 ||
      point[1] < bounds[0][1] - 0.0005 ||
      point[1] > bounds[1][1] + 0.0005
    )
      continue;
    addNearbyCandidate(
      candidates,
      feature,
      pointParcelDistance(geometry, point),
    );
  }
  return chooseNearbyProject(candidates);
}

// Same choice rules from boundary distances measured in PostGIS (`parcel-index`),
// for maps that draw parcel footprints from vector tiles.
export function nearbyProjectFromDistances(
  nearby: readonly { place_id: string; distance_m: number }[],
  projects: readonly MapFeature[],
): { feature: MapFeature; distance_m: number } | null {
  const distances = new Map(nearby.map((item) => [item.place_id, item]));
  const candidates = new Map<
    string,
    { feature: MapFeature; distance_m: number }
  >();
  for (const feature of projects) {
    const item = distances.get(feature.id);
    if (item && feature.geometry.type === "Point")
      addNearbyCandidate(candidates, feature, item.distance_m);
  }
  return chooseNearbyProject(candidates);
}

function addNearbyCandidate(
  candidates: Map<string, { feature: MapFeature; distance_m: number }>,
  feature: MapFeature,
  distance_m: number,
) {
  if (!Number.isFinite(distance_m) || distance_m > 50) return;
  // Only an explicit project identity can group separate source observations.
  // Equal names alone never reconcile two project identities.
  const slug = feature.properties.presentation?.project?.slug;
  const key = slug ? `project:${slug}` : `feature:${feature.id}`;
  const previous = candidates.get(key);
  if (
    !previous ||
    distance_m < previous.distance_m ||
    (distance_m === previous.distance_m && feature.id < previous.feature.id)
  )
    candidates.set(key, { feature, distance_m });
}

function chooseNearbyProject(
  candidates: Map<string, { feature: MapFeature; distance_m: number }>,
): { feature: MapFeature; distance_m: number } | null {
  const matches = [...candidates.values()].sort(
    (a, b) =>
      a.distance_m - b.distance_m || a.feature.id.localeCompare(b.feature.id),
  );
  // Do not choose automatically between almost equally close, distinct projects.
  if (matches[1] && matches[1].distance_m - matches[0].distance_m < 10)
    return null;
  return matches[0] ?? null;
}

export function parcelMapLabels<T extends ParcelRows>(
  data: T,
  candidates: Map<string, ParcelProperty[]>,
  locale: string,
  formatUse: (
    type: NonNullable<
      ParcelCollection["features"][number]["properties"]["use_types"]
    >[number],
  ) => string,
): T {
  return {
    ...data,
    features: data.features.map((feature: T["features"][number]) => {
      const candidate = preferredParcelProperty(
        candidates.get(feature.id) ?? [],
        locale,
      );
      const name = candidate ? propertyName(candidate, locale) : "";
      const p = feature.properties;
      // Spatial candidates are suggestions, never a cadastral project identity.
      return {
        ...feature,
        properties: {
          ...p,
          display_name:
            p.category === "overlay"
              ? ""
              : name
                ? `≈ ${name}`
                : p.use_types?.[0]
                  ? formatUse(p.use_types[0])
                  : p.land_use,
          potential_name: Boolean(name),
        },
      };
    }),
  };
}

// Presentation only: source codes, searches and exports keep their exact text.
export function readableParcelCode(code: string): string {
  return code.replace(/_to_/gi, "–").replaceAll("_", " · ");
}

export function propertyFeatures(context: MapContext | null): MapFeature[] {
  return [
    ...(context?.building.features ?? []),
    ...(context?.place.features.filter((feature) =>
      feature.properties.kind.endsWith("_project_marker"),
    ) ?? []),
  ].sort(
    (a, b) =>
      Number(Boolean(b.properties.presentation)) -
        Number(Boolean(a.properties.presentation)) ||
      Number(Boolean(b.properties.presentation?.media?.length)) -
        Number(Boolean(a.properties.presentation?.media?.length)) ||
      Number(Boolean(b.properties.name || b.properties.name_ar)) -
        Number(Boolean(a.properties.name || a.properties.name_ar)) ||
      a.properties.name.localeCompare(b.properties.name),
  );
}

type MapHit = {
  layer: { id: string };
  properties?: Record<string, unknown> | null;
};

// Rendering order is visual, not the specificity of the object under the pointer.
// Projects win over footprints, then parcels; administrative areas are last.
export function selectMapHit<T extends MapHit>(
  hits: readonly T[],
  parcelAreas: ReadonlyMap<string, number> = new Map(),
): T | null {
  let selected: T | null = null;
  let priority = Infinity;
  let selectedArea = Infinity;
  for (const hit of hits) {
    if (!hit.properties?.id) continue;
    const rank =
      [
        "places",
        "place-names",
        "project-names",
        "single-project",
        "close-project",
      ].includes(hit.layer.id) &&
      typeof hit.properties.kind === "string" &&
      hit.properties.kind.endsWith("_project_marker")
        ? 0
        : ["buildings", "buildings-3d"].includes(hit.layer.id)
          ? 1
          : [
                "places",
                "place-names",
                "project-names",
                "single-project",
                "close-project",
              ].includes(hit.layer.id)
            ? 2
            : ["streets", "street-names"].includes(hit.layer.id)
              ? 3
              : [
                    "parcel-fill",
                    "parcel-project-names",
                    "parcel-use-names",
                  ].includes(hit.layer.id)
                ? hit.properties.category === "overlay"
                  ? 5
                  : 4
                : ["area-hit", "areas", "area-names"].includes(hit.layer.id)
                  ? 6
                  : Infinity;
    const area = parcelAreas.get(String(hit.properties.id)) ?? Infinity;
    if (
      rank < priority ||
      ((rank === 4 || rank === 5) && priority === rank && area < selectedArea)
    ) {
      selected = hit;
      priority = rank;
      selectedArea = area;
    }
  }
  return selected;
}

// Relative surface for click specificity only, never a cadastral measurement.
// Work relative to each ring origin to retain precision for small UAE plots.
export function geometryClickArea(geometry: MapFeature["geometry"]): number {
  if (geometry.type !== "MultiPolygon") return Infinity;
  function ringArea(ring: number[][]) {
    if (ring.length < 3) return 0;
    const [ox, oy] = ring[0];
    let sum = 0;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++)
      sum +=
        (ring[j][0] - ox) * (ring[i][1] - oy) -
        (ring[i][0] - ox) * (ring[j][1] - oy);
    return Math.abs(sum) / 2;
  }
  const area = (geometry.coordinates as number[][][][]).reduce(
    (sum, rings) =>
      sum +
      Math.max(
        0,
        ringArea(rings[0] ?? []) -
          rings.slice(1).reduce((holes, ring) => holes + ringArea(ring), 0),
      ),
    0,
  );
  return area > 0 ? area : Infinity;
}

// Test the actual footprint, even below its rendering minzoom. No nearest-name
// match: holes remain empty land and a boundary counts as part of the building.
export function buildingAtPoint(
  features: readonly MapFeature[],
  point: readonly [number, number],
): MapFeature | null {
  function ringContains(ring: number[][]): boolean {
    let inside = false;
    const [x, y] = point;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [ax, ay] = ring[j];
      const [bx, by] = ring[i];
      const cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax);
      if (
        Math.abs(cross) < 1e-14 &&
        x >= Math.min(ax, bx) &&
        x <= Math.max(ax, bx) &&
        y >= Math.min(ay, by) &&
        y <= Math.max(ay, by)
      )
        return true;
      if (ay > y !== by > y && x < ((bx - ax) * (y - ay)) / (by - ay) + ax)
        inside = !inside;
    }
    return inside;
  }
  return (
    features.find((feature) => {
      if (feature.geometry.type !== "MultiPolygon") return false;
      return (feature.geometry.coordinates as number[][][][]).some(
        (rings) =>
          Boolean(rings[0]) &&
          ringContains(rings[0]) &&
          !rings.slice(1).some(ringContains),
      );
    }) ?? null
  );
}

export function geometryBounds(
  geometry: MapFeature["geometry"],
): [[number, number], [number, number]] | null {
  const numbers = geometry.coordinates.flat(Infinity) as number[];
  if (numbers.length < 2) return null;
  let west = Infinity,
    south = Infinity,
    east = -Infinity,
    north = -Infinity;
  for (let i = 0; i < numbers.length; i += 2) {
    west = Math.min(west, numbers[i]);
    east = Math.max(east, numbers[i]);
    south = Math.min(south, numbers[i + 1]);
    north = Math.max(north, numbers[i + 1]);
  }
  return [
    [west, south],
    [east, north],
  ];
}

// Frame every mapped island, irrespective of which district the API returns first.
export function districtBounds(
  features: MapFeature[],
): [[number, number], [number, number]] | null {
  const bounds = features
    .filter((feature) => feature.properties.kind === "district")
    .map((feature) => geometryBounds(feature.geometry))
    .filter((value) => value !== null);
  if (bounds.length === 0) return null;
  return [
    [
      Math.min(...bounds.map((b) => b[0][0])),
      Math.min(...bounds.map((b) => b[0][1])),
    ],
    [
      Math.max(...bounds.map((b) => b[1][0])),
      Math.max(...bounds.map((b) => b[1][1])),
    ],
  ];
}

export function sourceLabel(reliability: string, labels: MapLabels) {
  return reliability === "official"
    ? labels.official
    : reliability === "publisher"
      ? labels.developer
      : reliability === "broker"
        ? labels.broker
        : labels.community;
}

export const COLORS = {
  mixed: "#d6b17b",
  residential: "#f0dfaa",
  green: "#a9c99c",
  public: "#dbaaa1",
  tech: "#b9bec2",
  rail: "#aa8abb",
  overlay: "#c3b9ad",
  unknown: "#e5e0d6",
} as const;
export type Category = keyof typeof COLORS;
export function parcelFillColor(): ExpressionSpecification {
  return [
    "match",
    ["get", "category"],
    "mixed",
    COLORS.mixed,
    "residential",
    COLORS.residential,
    "green",
    COLORS.green,
    "public",
    COLORS.public,
    "tech",
    COLORS.tech,
    "rail",
    COLORS.rail,
    "overlay",
    COLORS.overlay,
    COLORS.unknown,
  ];
}

export function parcelFillOpacity(
  satellite: boolean,
): number | ExpressionSpecification {
  return satellite
    ? 0.06
    : ["case", ["==", ["get", "category"], "overlay"], 0.15, 0.86];
}
export function normalized(value: string) {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}
export function csv(rows: (string | number | null | undefined)[][]) {
  return rows
    .map((row) =>
      row
        .map((value) => {
          let text = String(value ?? "");
          if (/^[\s]*[=+@-]/u.test(text)) text = `'${text}`;
          return `"${text.replaceAll('"', '""')}"`;
        })
        .join(","),
    )
    .join("\r\n");
}
export function download(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
