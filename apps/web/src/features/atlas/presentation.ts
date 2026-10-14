import type { MapContext, MapFeature, MapLabels } from "./types";

type PropertyIdentity = Pick<
  MapFeature["properties"],
  "name" | "name_ar" | "kind" | "presentation"
>;
export type ParcelProperty = PropertyIdentity & {
  id: string;
  feature: MapFeature | null;
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

export function parcelPropertyIndex(context: MapContext | null) {
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
  return index;
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
// Administrative sectors stay inert; project perimeters are the last fallback.
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
      hit.layer.id === "buildings"
        ? 0
        : ["places", "place-names"].includes(hit.layer.id) &&
            typeof hit.properties.kind === "string" &&
            hit.properties.kind.endsWith("_project_marker")
          ? 1
          : ["places", "place-names"].includes(hit.layer.id)
            ? 2
            : ["streets", "street-names"].includes(hit.layer.id)
              ? 3
              : hit.layer.id === "parcel-fill"
                ? hit.properties.category === "overlay"
                  ? 5
                  : 4
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
  mixed: "#d9bf95",
  residential: "#eedfae",
  green: "#bfdbb6",
  public: "#a9ccdf",
  tech: "#c7cdd3",
  rail: "#ac83bc",
  overlay: "#b9a5c3",
  unknown: "#e7e3d7",
} as const;
export type Category = keyof typeof COLORS;
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
