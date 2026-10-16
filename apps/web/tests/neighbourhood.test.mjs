import assert from "node:assert/strict";
import test from "node:test";
import { googleNeighbourhoodUrl } from "../src/features/projects/neighbourhood-config.ts";

const bounds = [54.385, 24.465, 54.445, 24.53];
const browserKey = "example-restricted-browser-key";

test("Google neighbourhood maps require an explicit provider and valid browser configuration", () => {
  for (const provider of [undefined, "local", "https://other.example/"]) {
    assert.equal(
      googleNeighbourhoodUrl(bounds, "en", provider, browserKey),
      null,
    );
  }
  for (const key of [
    undefined,
    "",
    "short",
    "key with spaces",
    "https://other.example/",
  ]) {
    assert.equal(googleNeighbourhoodUrl(bounds, "en", "google", key), null);
  }
  for (const extent of [
    [],
    [0, 0, 0, 1],
    [54, 25, 55, 24],
    [NaN, 24, 55, 25],
    [-181, 24, 55, 25],
    [54, 24, 55, 91],
  ]) {
    assert.equal(
      googleNeighbourhoodUrl(extent, "en", "google", browserKey),
      null,
    );
  }
});

test("Google uses a fixed view endpoint and neighbourhood centre without inventing a project pin", () => {
  const url = new URL(
    googleNeighbourhoodUrl(bounds, "vi", "google", browserKey),
  );
  assert.equal(url.origin, "https://www.google.com");
  assert.equal(url.pathname, "/maps/embed/v1/view");
  const [lat, lng] = url.searchParams.get("center").split(",").map(Number);
  assert.ok(lat > bounds[1] && lat < bounds[3]);
  assert.ok(lng > bounds[0] && lng < bounds[2]);
  assert.equal(url.searchParams.get("language"), "vi");
  assert.equal(url.searchParams.has("q"), false);
  assert.ok(Number(url.searchParams.get("zoom")) >= 10);
});
