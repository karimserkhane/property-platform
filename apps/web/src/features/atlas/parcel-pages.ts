import type { ParcelCollection } from "./types";

// Small-area preview budget. A national map will need viewport/vector-tile reads.
const MAX_PAGES = 12;
const MAX_FEATURES = 12_000;

export async function readParcelPages(
  bbox: string,
  territory: string,
  signal: AbortSignal,
): Promise<ParcelCollection> {
  let result: ParcelCollection | null = null;
  const ids = new Set<string>();
  const cursors = new Set<string>();
  let cursor: string | null = null;
  for (let page = 0; page < MAX_PAGES; page++) {
    const params = new URLSearchParams({ bbox, territory, limit: "1000" });
    if (cursor) params.set("after", cursor);
    const response = await fetch(`/api/atlas/parcels?${params}`, { signal });
    if (!response.ok) throw new Error("unavailable");
    const data = (await response.json()) as ParcelCollection;
    if (!Array.isArray(data.features)) throw new Error("invalid");
    result ??= { ...data, features: [] };
    for (const feature of data.features) {
      if (!ids.has(feature.id)) {
        ids.add(feature.id);
        result.features.push(feature);
      }
    }
    result.truncated = data.truncated;
    result.next_cursor = data.next_cursor;
    cursor = data.next_cursor ?? null;
    if (!data.truncated || !cursor || result.features.length >= MAX_FEATURES)
      return result;
    if (cursors.has(cursor)) throw new Error("invalid cursor");
    cursors.add(cursor);
  }
  if (!result) throw new Error("invalid");
  return result;
}
