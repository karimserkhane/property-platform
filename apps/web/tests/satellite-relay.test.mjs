import assert from "node:assert/strict";
import { mock, test } from "node:test";
import { GET } from "../src/app/api/atlas/satellite/[provider]/[z]/[x]/[y]/route.ts";

const params = (overrides = {}) => ({
  params: Promise.resolve({
    provider: "sentinel-worldcover-2021",
    z: "13",
    x: "5334",
    y: "3520",
    ...overrides,
  }),
});
const request = (query = "") =>
  new Request(`http://localhost/api/atlas/satellite/tile${query}`);
function png() {
  const bytes = new Uint8Array(33);
  bytes.set([137, 80, 78, 71, 13, 10, 26, 10]);
  const view = new DataView(bytes.buffer);
  view.setUint32(12, 0x49484452);
  view.setUint32(16, 256);
  view.setUint32(20, 256);
  return bytes;
}

test("the raster relay accepts only registered annual RGB layers and XYZ ranges", async () => {
  const fetch = mock.method(globalThis, "fetch", () => {
    throw new Error("must not fetch");
  });
  try {
    for (const overrides of [
      { provider: "https://example.com" },
      { provider: "__proto__" },
    ])
      assert.equal((await GET(request(), params(overrides))).status, 404);
    for (const overrides of [
      { z: "7" },
      { z: "15" },
      { x: "8192" },
      { y: "-1" },
      { x: "1e2" },
    ])
      assert.equal((await GET(request(), params(overrides))).status, 400);
    assert.equal(
      (await GET(request("?url=https://example.com"), params())).status,
      400,
    );
    assert.equal(fetch.mock.callCount(), 0);
  } finally {
    fetch.mock.restore();
  }
});

test("the relay preserves the year and XYZ axes, caching public PNGs without forwarding user headers", async () => {
  const bytes = png();
  const fetch = mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url.origin, "http://127.0.0.1:8000");
    assert.equal(
      url.pathname,
      "/api/v1/preview/basemap/sentinel-worldcover-2021/13/5334/3520",
    );
    assert.equal(url.search, "");
    assert.deepEqual(options.headers, { Accept: "image/png" });
    assert.equal(options.redirect, "error");
    return new Response(bytes, { headers: { "Content-Type": "image/png" } });
  });
  try {
    const response = await GET(request(), params());
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("X-Imagery-Period"), "2021");
    assert.ok(response.headers.get("Cache-Control").includes("public"));
    assert.deepEqual(new Uint8Array(await response.arrayBuffer()), bytes);
  } finally {
    fetch.mock.restore();
  }
});

test("HTML, oversized streams, invalid PNGs and truncated bodies never become image tiles", async () => {
  for (const response of [
    new Response("<html>error</html>", {
      headers: { "Content-Type": "text/html" },
    }),
    new Response(new Uint8Array(4 * 1024 * 1024 + 1), {
      headers: { "Content-Type": "image/png" },
    }),
    new Response("not png", { headers: { "Content-Type": "image/png" } }),
    new Response(png(), {
      headers: { "Content-Type": "image/png", "Content-Length": "40" },
    }),
    new Response("denied", { status: 403 }),
  ]) {
    const fetch = mock.method(globalThis, "fetch", async () => response);
    try {
      const result = await GET(request(), params());
      assert.equal(result.status, 503);
      assert.equal(result.headers.get("Cache-Control"), "no-store");
    } finally {
      fetch.mock.restore();
    }
  }
});
