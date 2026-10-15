import assert from "node:assert/strict";
import { mock, test } from "node:test";
import { GET, HEAD } from "../src/app/api/atlas/project-media/[id]/route.ts";

const id = "a20c7655-2490-4f5b-8cd9-83300642a594";
const params = { params: Promise.resolve({ id }) };
const request = (headers = {}, method = "GET") =>
  new Request(`http://localhost/api/atlas/project-media/${id}`, {
    headers,
    method,
  });

test("video relay streams the exact range from a fixed server path", async () => {
  const fetch = mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url.pathname, `/api/v1/preview/project-media/${id}`);
    assert.equal(options.headers.get("range"), "bytes=2-5");
    assert.equal(options.redirect, "error");
    return new Response(new Uint8Array([2, 3, 4, 5]), {
      status: 206,
      headers: {
        "Content-Type": "video/mp4",
        "Content-Length": "4",
        "Content-Range": "bytes 2-5/10",
        "Accept-Ranges": "bytes",
      },
    });
  });
  try {
    const response = await GET(request({ Range: "bytes=2-5" }), params);
    assert.equal(response.status, 206);
    assert.equal(response.headers.get("content-range"), "bytes 2-5/10");
    assert.equal(response.headers.get("cache-control"), "private, no-store");
    assert.deepEqual(
      new Uint8Array(await response.arrayBuffer()),
      new Uint8Array([2, 3, 4, 5]),
    );
  } finally {
    fetch.mock.restore();
  }
});

test("video HEAD forwards metadata without requesting a body", async () => {
  const fetch = mock.method(globalThis, "fetch", async (_url, options) => {
    assert.equal(options.method, "HEAD");
    return new Response(null, {
      headers: { "Content-Type": "video/mp4", "Content-Length": "512" },
    });
  });
  try {
    const response = await HEAD(request({}, "HEAD"), params);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("content-length"), "512");
    assert.equal(await response.text(), "");
  } finally {
    fetch.mock.restore();
  }
});

test("media relay refuses active HTML, oversized objects and inconsistent ranges", async () => {
  for (const headers of [
    { "Content-Type": "text/html", "Content-Length": "4" },
    {
      "Content-Type": "video/mp4",
      "Content-Length": String(128 * 1024 * 1024 + 1),
    },
    {
      "Content-Type": "video/mp4",
      "Content-Length": "4",
      "Content-Range": "bytes 9-12/10",
    },
  ]) {
    const fetch = mock.method(
      globalThis,
      "fetch",
      async () =>
        new Response("data", {
          status: headers["Content-Range"] ? 206 : 200,
          headers,
        }),
    );
    try {
      assert.equal((await GET(request(), params)).status, 503);
    } finally {
      fetch.mock.restore();
    }
  }
});

test("media relay detects truncated bodies and preserves valid 416 metadata", async () => {
  const fetch = mock.method(
    globalThis,
    "fetch",
    async () =>
      new Response("ab", {
        headers: { "Content-Type": "video/mp4", "Content-Length": "4" },
      }),
  );
  try {
    const response = await GET(request(), params);
    await assert.rejects(response.arrayBuffer(), /Media unavailable/);
  } finally {
    fetch.mock.restore();
  }
  const rangeFetch = mock.method(
    globalThis,
    "fetch",
    async () =>
      new Response(null, {
        status: 416,
        headers: { "Content-Range": "bytes */512" },
      }),
  );
  try {
    const response = await GET(request({ Range: "bytes=1000-" }), params);
    assert.equal(response.status, 416);
    assert.equal(response.headers.get("content-range"), "bytes */512");
  } finally {
    rangeFetch.mock.restore();
  }
});
