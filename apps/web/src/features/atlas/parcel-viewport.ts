import type { ParcelIndex } from "./types";

// The explorer reads the parcel index by fixed grid cells around the visible
// map instead of the whole territory: cells are cached, so panning back costs
// nothing and a national index never has to fit in one browser read.
export const CELL_DEGREES = 0.05;
// 16 cells cover 0.2° × 0.2°, the API's largest accepted bbox.
export const MAX_VIEW_CELLS = 16;
// Up to this many cells under the view, the cells nearest its centre are read
// within the budget and the list is partial; a wider view reads nothing.
export const MAX_PARTIAL_VIEW_CELLS = 4 * MAX_VIEW_CELLS;
const MAX_CACHED_CELLS = 48;

export type Bounds = readonly [number, number, number, number];

export type ViewportCells =
  | { kind: "cells"; cells: string[]; partial: boolean }
  | { kind: "outside" }
  | { kind: "too-large" };

const edge = (index: number) => Number((index * CELL_DEGREES).toFixed(6));

// Grid cells under `view`, clipped to the collected area, as `bbox` strings.
// A view slightly wider than the budget keeps the `maxCells` cells nearest its
// centre, so an emirate-wide collection still lists the framed area.
export function viewportCells(
  view: Bounds,
  collection: Bounds,
  maxCells = MAX_VIEW_CELLS,
  maxPartialCells = MAX_PARTIAL_VIEW_CELLS,
): ViewportCells {
  const west = Math.max(view[0], collection[0]);
  const south = Math.max(view[1], collection[1]);
  const east = Math.min(view[2], collection[2]);
  const north = Math.min(view[3], collection[3]);
  if (!(west < east && south < north)) return { kind: "outside" };
  const x0 = Math.floor(west / CELL_DEGREES);
  const x1 = Math.ceil(east / CELL_DEGREES);
  const y0 = Math.floor(south / CELL_DEGREES);
  const y1 = Math.ceil(north / CELL_DEGREES);
  if ((x1 - x0) * (y1 - y0) > maxPartialCells) return { kind: "too-large" };
  const centreX = (west + east) / 2;
  const centreY = (south + north) / 2;
  const cells: { bbox: string; distance: number; order: number }[] = [];
  for (let x = x0; x < x1; x++)
    for (let y = y0; y < y1; y++) {
      const cell = [
        Math.max(edge(x), collection[0]),
        Math.max(edge(y), collection[1]),
        Math.min(edge(x + 1), collection[2]),
        Math.min(edge(y + 1), collection[3]),
      ];
      if (cell[0] < cell[2] && cell[1] < cell[3])
        cells.push({
          bbox: cell.join(","),
          distance:
            ((cell[0] + cell[2]) / 2 - centreX) ** 2 +
            ((cell[1] + cell[3]) / 2 - centreY) ** 2,
          order: cells.length,
        });
    }
  const partial = cells.length > maxCells;
  const kept = partial
    ? [...cells]
        .sort((a, b) => a.distance - b.distance || a.order - b.order)
        .slice(0, maxCells)
        .sort((a, b) => a.order - b.order)
    : cells;
  return { kind: "cells", cells: kept.map((c) => c.bbox), partial };
}

type ReadCell = (bbox: string, signal: AbortSignal) => Promise<ParcelIndex>;

// Least recently used cells are evicted; failed reads are not kept.
export class ParcelCellCache {
  private readonly cells = new Map<string, Promise<ParcelIndex>>();
  private readonly read: ReadCell;
  private readonly limit: number;

  constructor(read: ReadCell, limit = MAX_CACHED_CELLS) {
    this.read = read;
    this.limit = limit;
  }

  get size() {
    return this.cells.size;
  }

  // Rows of all `cells`, deduplicated across cell borders; `onCell` sees each
  // partial merge so the map can draw cells as they arrive.
  async rows(
    cells: string[],
    signal: AbortSignal,
    onCell?: (rows: ParcelIndex) => void,
  ): Promise<ParcelIndex> {
    const loaded = new Map<string, ParcelIndex>();
    const merge = () => mergeCells(cells.flatMap((c) => loaded.get(c) ?? []));
    await Promise.all(
      cells.map(async (cell) => {
        loaded.set(cell, await this.cell(cell, signal));
        if (!signal.aborted) onCell?.(merge());
      }),
    );
    return merge();
  }

  private cell(bbox: string, signal: AbortSignal) {
    let entry = this.cells.get(bbox);
    if (entry) {
      this.cells.delete(bbox);
    } else {
      // A shared read must survive one caller's abort; only the cell budget stops it.
      entry = this.read(bbox, new AbortController().signal);
      entry.catch(() => {
        if (this.cells.get(bbox) === entry) this.cells.delete(bbox);
      });
    }
    this.cells.set(bbox, entry);
    while (this.cells.size > this.limit) {
      const oldest = this.cells.keys().next().value as string;
      this.cells.delete(oldest);
    }
    return abortable(entry, signal);
  }
}

function abortable<T>(promise: Promise<T>, signal: AbortSignal): Promise<T> {
  if (signal.aborted) return Promise.reject(signal.reason);
  return new Promise((resolve, reject) => {
    const stop = () => reject(signal.reason);
    signal.addEventListener("abort", stop, { once: true });
    promise.then(resolve, reject).finally(() => {
      signal.removeEventListener("abort", stop);
    });
  });
}

export function mergeCells(parts: ParcelIndex[]): ParcelIndex {
  const ids = new Set<string>();
  const features: ParcelIndex["features"] = [];
  for (const part of parts)
    for (const feature of part.features)
      if (!ids.has(feature.id)) {
        ids.add(feature.id);
        features.push(feature);
      }
  return {
    type: "FeatureCollection",
    features,
    truncated: parts.some((part) => part.truncated),
    classification_version: parts[0]?.classification_version ?? "",
  };
}
