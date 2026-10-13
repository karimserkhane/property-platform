import assert from "node:assert/strict";
import test from "node:test";
import { readParcelPages } from "../src/features/atlas/parcel-pages.ts";

test("parcel pages retain the territory, advance the cursor and deduplicate overlap", async () => {
  const original = globalThis.fetch;
  const requests = [];
  const pages = [
    { features: [{ id: "a" }, { id: "b" }], truncated: true, next_cursor: "b" },
    {
      features: [{ id: "b" }, { id: "c" }],
      truncated: false,
      next_cursor: null,
    },
  ];
  globalThis.fetch = async (url) => {
    requests.push(new URL(url, "http://localhost"));
    return { ok: true, json: async () => pages.shift() };
  };
  try {
    const result = await readParcelPages(
      "54.4,24.5,54.48,24.6",
      "saadiyat-island",
      new AbortController().signal,
    );
    assert.deepEqual(
      result.features.map((row) => row.id),
      ["a", "b", "c"],
    );
    assert.equal(result.truncated, false);
    assert.equal(requests[1].searchParams.get("after"), "b");
    assert.ok(
      requests.every(
        (url) => url.searchParams.get("territory") === "saadiyat-island",
      ),
    );
  } finally {
    globalThis.fetch = original;
  }
});

test("a partial acquisition is rejected when a later page fails", async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () =>
    ++calls === 1
      ? {
          ok: true,
          json: async () => ({
            features: [{ id: "a" }],
            truncated: true,
            next_cursor: "a",
          }),
        }
      : { ok: false };
  try {
    await assert.rejects(
      readParcelPages(
        "54.4,24.5,54.48,24.6",
        "saadiyat-island",
        new AbortController().signal,
      ),
    );
  } finally {
    globalThis.fetch = original;
  }
});
