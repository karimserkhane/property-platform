import assert from "node:assert/strict";
import test from "node:test";
import {
  MAX_VIEW_CELLS,
  mergeCells,
  ParcelCellCache,
  viewportCells,
} from "../src/features/atlas/parcel-viewport.ts";

const COLLECTION = [54.383, 24.465, 54.483, 24.603];
const rows = (...ids) => ({
  type: "FeatureCollection",
  features: ids.map((id) => ({ id })),
  truncated: false,
  classification_version: "v1",
});

test("visible cells snap to the grid and stay inside the collected area", () => {
  const result = viewportCells([54.39, 24.48, 54.43, 24.51], COLLECTION);
  assert.equal(result.kind, "cells");
  assert.deepEqual(result.cells, [
    "54.383,24.465,54.4,24.5",
    "54.383,24.5,54.4,24.55",
    "54.4,24.465,54.45,24.5",
    "54.4,24.5,54.45,24.55",
  ]);
  for (const cell of result.cells) {
    const [w, s, e, n] = cell.split(",").map(Number);
    assert.ok(w >= COLLECTION[0] && e <= COLLECTION[2] && w < e);
    assert.ok(s >= COLLECTION[1] && n <= COLLECTION[3] && s < n);
    assert.ok(e - w <= 0.05 + 1e-9 && n - s <= 0.05 + 1e-9);
  }
  // Panning inside the same cells requests the same cells.
  assert.deepEqual(
    viewportCells([54.391, 24.481, 54.431, 24.511], COLLECTION),
    result,
  );
});

test("a view outside the collection or too large reads nothing", () => {
  assert.deepEqual(viewportCells([55, 25, 55.1, 25.1], COLLECTION), {
    kind: "outside",
  });
  assert.deepEqual(
    viewportCells([54, 24, 55, 25], [54, 24, 55, 25], MAX_VIEW_CELLS),
    { kind: "too-large" },
  );
  // The whole current collection fits in the cell budget.
  const whole = viewportCells(COLLECTION, COLLECTION);
  assert.equal(whole.kind, "cells");
  assert.equal(whole.partial, false);
});

test("a view slightly over the budget reads the cells nearest its centre", () => {
  // 6 × 4 cells inside an emirate-wide collection, centred on 54.4, 24.5.
  const result = viewportCells([54.25, 24.4, 54.55, 24.6], [52, 22, 56, 25], 4);
  assert.equal(result.kind, "cells");
  assert.equal(result.partial, true);
  assert.deepEqual(result.cells, [
    "54.35,24.45,54.4,24.5",
    "54.35,24.5,54.4,24.55",
    "54.4,24.45,54.45,24.5",
    "54.4,24.5,54.45,24.55",
  ]);
  // Beyond four times the budget nothing is read.
  assert.deepEqual(viewportCells([54, 24, 55, 25], [52, 22, 56, 25], 4, 16), {
    kind: "too-large",
  });
});

test("cells are read once, merged without border duplicates and evicted LRU", async () => {
  const reads = [];
  const data = { a: rows("1", "2"), b: rows("2", "3"), c: rows("4") };
  const cache = new ParcelCellCache(async (bbox) => {
    reads.push(bbox);
    return data[bbox];
  }, 2);
  const signal = new AbortController().signal;
  const partial = [];
  const merged = await cache.rows(["a", "b"], signal, (r) =>
    partial.push(r.features.length),
  );
  assert.deepEqual(
    merged.features.map((f) => f.id),
    ["1", "2", "3"],
  );
  assert.equal(partial.at(-1), 3);
  await cache.rows(["a", "b"], signal);
  assert.deepEqual(reads, ["a", "b"]);
  // "a" was used last, so reading "c" evicts "b".
  await cache.rows(["a"], signal);
  await cache.rows(["c"], signal);
  await cache.rows(["b"], signal);
  assert.deepEqual(reads, ["a", "b", "c", "b"]);
  assert.equal(cache.size, 2);
});

test("a failed cell is retried and an abort leaves the shared read cached", async () => {
  let calls = 0;
  let release;
  const cache = new ParcelCellCache((bbox) => {
    calls++;
    if (bbox === "bad" && calls === 1) return Promise.reject(new Error("x"));
    return new Promise((resolve) => {
      release = () => resolve(rows("1"));
    });
  });
  await assert.rejects(cache.rows(["bad"], new AbortController().signal));
  const controller = new AbortController();
  const aborted = cache.rows(["bad"], controller.signal);
  controller.abort();
  await assert.rejects(aborted);
  release();
  const again = await cache.rows(["bad"], new AbortController().signal);
  assert.equal(again.features.length, 1);
  assert.equal(calls, 2);
});

test("merging keeps truncation from any cell", () => {
  const merged = mergeCells([
    rows("1"),
    { ...rows("1", "2"), truncated: true },
  ]);
  assert.equal(merged.truncated, true);
  assert.equal(merged.features.length, 2);
});
