import { area } from "@turf/area";
import { booleanPointInPolygon } from "@turf/boolean-point-in-polygon";
import { length } from "@turf/length";
import type {
  Feature,
  FeatureCollection,
  LineString,
  Point,
  Polygon,
} from "geojson";
import type { Map as LibreMap } from "maplibre-gl";
import type { MapContext, MapFeature, ParcelRows } from "./types";

// Parcel footprints are not on the explorer client: frame them by published bounds.
export function boundsGeometry([west, south, east, north]: readonly number[]) {
  return {
    type: "Polygon" as const,
    coordinates: [
      [
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
      ],
    ],
  };
}

export type Coordinate = [number, number];
export type AnalysisMode = "browse" | "distance" | "zone" | "walk";
const activeTools = new WeakMap<LibreMap, AnalysisMode>();
export const mapToolActive = (map: LibreMap) =>
  (activeTools.get(map) ?? "browse") !== "browse";
export const setMapTool = (map: LibreMap, mode: AnalysisMode) =>
  activeTools.set(map, mode);
export const emptyAnalysis = (): FeatureCollection => ({
  type: "FeatureCollection",
  features: [],
});

export function measurement(points: Coordinate[], closed: boolean) {
  const features: Feature[] = points.map((coordinates, index) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates },
    properties: { index },
  }));
  let metres = 0,
    squareMetres = 0;
  if (points.length >= 2) {
    const line: Feature<LineString> = {
      type: "Feature",
      properties: {},
      geometry: {
        type: "LineString",
        coordinates:
          closed && points.length >= 3 ? [...points, points[0]] : points,
      },
    };
    metres = length(line, { units: "meters" });
    features.unshift(line);
  }
  let polygon: Feature<Polygon> | null = null;
  if (closed && points.length >= 3) {
    polygon = {
      type: "Feature",
      properties: {},
      geometry: { type: "Polygon", coordinates: [[...points, points[0]]] },
    };
    squareMetres = area(polygon);
    features.unshift(polygon);
  }
  return {
    data: { type: "FeatureCollection" as const, features },
    metres,
    squareMetres,
    polygon,
  };
}

export type SearchItem = {
  key: string;
  name: string;
  kind: "project" | "place" | "parcel";
  geometry: MapFeature["geometry"];
  feature?: MapFeature;
  parcelId?: string;
};
const normalise = (value: string) =>
  value.normalize("NFKD").replace(/\p{M}/gu, "").toLocaleLowerCase().trim();
export function searchItems(
  context: MapContext | null,
  parcels: ParcelRows | null,
  locale: string,
): SearchItem[] {
  const items: SearchItem[] = [],
    seen = new Set<string>();
  for (const feature of [
    ...(context?.place.features ?? []),
    ...(context?.building.features ?? []),
    ...(context?.street.features ?? []),
    ...(context?.administrative_area.features ?? []),
  ]) {
    const p = feature.properties;
    const slug = p.presentation?.project?.slug;
    const key = slug ? `project:${slug}` : p.source.url || feature.id;
    const name =
      (locale === "ar" && p.name_ar) ||
      p.presentation?.name ||
      p.name ||
      p.name_ar;
    if (!name || seen.has(key)) continue;
    seen.add(key);
    items.push({
      key,
      name,
      kind: p.kind.endsWith("_project_marker") ? "project" : "place",
      geometry: feature.geometry,
      feature,
    });
  }
  for (const parcel of parcels?.features ?? []) items.push(parcelItem(parcel));
  return items;
}
function parcelItem(parcel: ParcelRows["features"][number]): SearchItem {
  return {
    key: `parcel:${parcel.id}`,
    name: parcel.properties.code,
    kind: "parcel",
    geometry:
      "geometry" in parcel
        ? parcel.geometry
        : boundsGeometry(parcel.properties.bounds),
    parcelId: parcel.id,
  };
}
// The map holds only its visible parcels; the server finds codes elsewhere in the
// territory. Visible matches keep their rank and server rows fill the free slots.
export function withParcelMatches(
  results: SearchItem[],
  matches: ParcelRows | null,
) {
  const merged = [...results];
  const seen = new Set(merged.map((item) => item.key));
  for (const parcel of matches?.features ?? []) {
    if (merged.length >= 12) break;
    const item = parcelItem(parcel);
    if (seen.has(item.key)) continue;
    seen.add(item.key);
    merged.push(item);
  }
  return merged;
}
export function searchMap(items: SearchItem[], query: string) {
  const needle = normalise(query);
  if (needle.length < 2) return [];
  return items
    .filter((item) =>
      normalise(
        `${item.name} ${item.feature?.properties.name_ar ?? ""} ${item.feature?.properties.name ?? ""}`,
      ).includes(needle),
    )
    .sort(
      (a, b) =>
        Number(b.kind === "project") - Number(a.kind === "project") ||
        Number(normalise(b.name).startsWith(needle)) -
          Number(normalise(a.name).startsWith(needle)) ||
        a.name.localeCompare(b.name),
    )
    .slice(0, 12);
}

export function projectsInZone(
  items: SearchItem[],
  polygon: Feature<Polygon> | null,
) {
  if (!polygon) return [];
  return items.filter(
    (item) =>
      item.kind === "project" &&
      item.geometry.type === "Point" &&
      booleanPointInPolygon(item.geometry.coordinates as Coordinate, polygon),
  );
}

export function clusteredProjects(
  context: MapContext | null,
): FeatureCollection<Point> {
  const seen = new Set<string>();
  return {
    type: "FeatureCollection",
    features: (context?.place.features ?? [])
      .filter((feature) => {
        if (
          feature.geometry.type !== "Point" ||
          !feature.properties.kind.endsWith("_project_marker")
        )
          return false;
        const key =
          feature.properties.presentation?.project?.slug ?? feature.id;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .map((feature) => ({
        ...feature,
        type: "Feature" as const,
        geometry: {
          type: "Point",
          coordinates: feature.geometry.coordinates as number[],
        },
      })),
  };
}
