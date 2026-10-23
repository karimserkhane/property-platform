import type { ParcelCollection, ParcelIndex, ParcelRows } from "./types";

// Small-area preview budget for full footprints (project neighbourhood maps).
const MAX_PAGES = 12;
const MAX_FEATURES = 12_000;
// Footprint-free index rows are small; the explorer draws shapes from tiles.
const INDEX_PAGE = 3000;
const MAX_INDEX_FEATURES = 36_000;

export function readParcelPages(
  bbox: string,
  territory: string,
  signal: AbortSignal,
): Promise<ParcelCollection> {
  return readPages("parcels", 1000, MAX_FEATURES, bbox, territory, signal);
}

export function readParcelIndex(
  bbox: string,
  territory: string,
  signal: AbortSignal,
): Promise<ParcelIndex> {
  return readPages(
    "parcel-index",
    INDEX_PAGE,
    MAX_INDEX_FEATURES,
    bbox,
    territory,
    signal,
  );
}

async function readPages<T extends ParcelRows>(
  endpoint: "parcels" | "parcel-index",
  limit: number,
  maxFeatures: number,
  bbox: string,
  territory: string,
  signal: AbortSignal,
): Promise<T> {
  let result: T | null = null;
  const ids = new Set<string>();
  const cursors = new Set<string>();
  let cursor: string | null = null;
  for (let page = 0; page < MAX_PAGES; page++) {
    const params = new URLSearchParams({ bbox, territory, limit: `${limit}` });
    if (cursor) params.set("after", cursor);
    const response = await fetch(`/api/atlas/${endpoint}?${params}`, {
      signal,
    });
    if (!response.ok) throw new Error("unavailable");
    const data = (await response.json()) as T;
    if (!Array.isArray(data.features)) throw new Error("invalid");
    result ??= { ...data, features: [] };
    for (const feature of data.features as T["features"]) {
      if (!ids.has(feature.id)) {
        ids.add(feature.id);
        (result.features as T["features"][number][]).push(feature);
      }
    }
    result.truncated = data.truncated;
    result.next_cursor = data.next_cursor;
    cursor = data.next_cursor ?? null;
    if (!data.truncated || !cursor || result.features.length >= maxFeatures)
      return result;
    if (cursors.has(cursor)) throw new Error("invalid cursor");
    cursors.add(cursor);
  }
  if (!result) throw new Error("invalid");
  return result;
}
