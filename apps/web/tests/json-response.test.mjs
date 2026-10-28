import assert from "node:assert/strict";
import test from "node:test";
import { brotliDecompressSync, gunzipSync } from "node:zlib";
import {
  acceptedEncoding,
  jsonResponse,
} from "../src/features/atlas/json-response.ts";

const large = {
  type: "FeatureCollection",
  features: Array.from({ length: 200 }, (_, index) => ({
    id: `parcel-${index}`,
    properties: { land_use: "Residential", name_ar: "جزيرة الريم" },
  })),
};
const request = (encoding) =>
  new Request("http://localhost/api/atlas/parcels", {
    headers: encoding === undefined ? {} : { "Accept-Encoding": encoding },
  });

test("the preferred accepted encoding honours quality weights and refusals", () => {
  assert.equal(acceptedEncoding("gzip, deflate, br, zstd"), "br");
  assert.equal(acceptedEncoding("gzip"), "gzip");
  assert.equal(acceptedEncoding("br;q=0, gzip"), "gzip");
  assert.equal(acceptedEncoding("br;q=0.5, gzip;q=0.8"), "gzip");
  assert.equal(acceptedEncoding("*"), "br");
  assert.equal(acceptedEncoding("identity"), null);
  assert.equal(acceptedEncoding("gzip;q=0, br;q=0"), null);
  assert.equal(acceptedEncoding(null), null);
});

test("large JSON is encoded for the client without changing its contents", async () => {
  for (const [header, decode] of [
    ["br", brotliDecompressSync],
    ["gzip", gunzipSync],
  ]) {
    const response = await jsonResponse(request(header), large, {
      status: 200,
      headers: { "Cache-Control": "no-store" },
    });
    assert.equal(response.headers.get("Content-Encoding"), header);
    assert.equal(response.headers.get("Vary"), "Accept-Encoding");
    assert.equal(response.headers.get("Cache-Control"), "no-store");
    assert.equal(response.headers.get("Content-Type"), "application/json");
    const bytes = Buffer.from(await response.arrayBuffer());
    assert.ok(bytes.byteLength < JSON.stringify(large).length / 4);
    assert.deepEqual(JSON.parse(decode(bytes).toString("utf8")), large);
  }
});

test("small bodies and clients without encodings receive plain JSON", async () => {
  for (const [input, body] of [
    [request("br"), { code: "not_found" }],
    [request(), large],
    [request("identity"), large],
  ]) {
    const response = await jsonResponse(input, body, { status: 404 });
    assert.equal(response.status, 404);
    assert.equal(response.headers.get("Content-Encoding"), null);
    assert.deepEqual(await response.json(), body);
  }
});
