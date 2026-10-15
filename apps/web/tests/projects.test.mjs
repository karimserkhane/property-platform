import assert from "node:assert/strict";
import test from "node:test";
import { readProjectData } from "../src/features/projects/data.ts";
import {
  approvedDelivery,
  formatHandover,
  playableMedia,
  safeSourceUrl,
} from "../src/features/projects/presentation.ts";

test("project references accept HTTPS without credentials and reject active or relative URLs", () => {
  assert.equal(
    safeSourceUrl("https://vimeo.com/1038853770"),
    "https://vimeo.com/1038853770",
  );
  assert.equal(
    safeSourceUrl("https://example.com/brochure.pdf#page=2"),
    "https://example.com/brochure.pdf#page=2",
  );
  for (const value of [
    "javascript:alert(1)",
    "data:text/html,<script>",
    "file:///etc/passwd",
    "http://example.com/video.mp4",
    "//example.com/video.mp4",
    "/api/atlas/property-media/id",
    "https://user:password@example.com",
    " https://example.com",
    "https://example.com\n/path",
    null,
  ])
    assert.equal(safeSourceUrl(value), null, String(value));
});

test("a reference-only source never becomes an embedded image or video", () => {
  const video = {
    kind: "video",
    mime_type: "video/mp4",
    delivery_url: "https://cdn.example.com/video.mp4",
  };
  for (const rights_status of ["reference_only", "blocked", "unknown", ""]) {
    assert.equal(approvedDelivery({ ...video, rights_status }), null);
    assert.equal(playableMedia({ ...video, rights_status }), null);
  }
  assert.equal(playableMedia({ ...video, rights_status: "approved" }), "video");
  assert.equal(
    playableMedia({
      ...video,
      rights_status: "approved",
      mime_type: "text/html",
    }),
    null,
  );
  assert.equal(
    playableMedia({ ...video, rights_status: "approved", kind: "document" }),
    null,
  );
});

test("approved files use the fixed guarded media route or HTTPS delivery", () => {
  const id = "a20c7655-2490-4f5b-8cd9-83300642a594";
  const media = {
    rights_status: "approved",
    delivery_url: `/api/atlas/project-media/${id}`,
  };
  assert.equal(approvedDelivery(media), media.delivery_url);
  for (const delivery_url of [
    `/api/atlas/project-media/${id}?url=https://example.com`,
    "/api/atlas/project-media/../../secrets",
    "//example.com",
    "javascript:alert(1)",
    null,
  ])
    assert.equal(approvedDelivery({ ...media, delivery_url }), null);
  assert.equal(
    playableMedia({ ...media, kind: "image", mime_type: "image/webp" }),
    "image",
  );
  assert.equal(
    playableMedia({ ...media, kind: "image", mime_type: "image/svg+xml" }),
    null,
  );
  assert.equal(
    playableMedia({ ...media, kind: "model", mime_type: "model/gltf-binary" }),
    null,
  );
});

test("handover formatting preserves year, quarter, month and day precision", () => {
  assert.equal(
    formatHandover({ precision: "year", year: 2029 }, "en", "Quarter"),
    "2029",
  );
  assert.equal(
    formatHandover(
      { precision: "quarter", year: 2029, quarter: 2 },
      "en",
      "Quarter",
    ),
    "Quarter 2 · 2029",
  );
  assert.equal(
    formatHandover(
      { precision: "quarter", year: 2029, quarter: 2 },
      "fr",
      "Trimestre",
    ),
    "Trimestre 2 · 2029",
  );
  assert.equal(
    formatHandover(
      { precision: "month", year: 2029, month: 6 },
      "en",
      "Quarter",
    ),
    "June 2029",
  );
  assert.equal(
    formatHandover(
      { precision: "day", year: 2028, month: 2, day: 29 },
      "en",
      "Quarter",
    ),
    "February 29, 2028",
  );
  for (const value of [
    { precision: "quarter", year: 2029, quarter: 0 },
    { precision: "quarter", year: 2029, quarter: 1.5 },
    { precision: "month", year: 2029, month: 13 },
    { precision: "month", year: 2029, month: 1.5 },
    { precision: "day", year: 2029, month: 2, day: 29 },
    { precision: "day", year: 2029, month: 6, day: 0 },
    { precision: "unknown", year: 2029 },
    { precision: "year", year: 2029.5 },
  ])
    assert.equal(formatHandover(value, "en", "Quarter"), null);
});

const project = {
  slug: "park-view",
  name: "Park View",
  developer: { name: "Bloom Holding" },
  sources: [],
  media: [],
  typologies: [],
  amenities: [],
};

test("project route reads a fixed API path and rejects invalid slugs before any request", async () => {
  const paths = [];
  const read = async (path) => {
    paths.push(path);
    return { status: 200, data: project };
  };
  assert.deepEqual(await readProjectData("park-view", read), {
    status: 200,
    project,
  });
  assert.deepEqual(paths, ["projects/park-view"]);
  for (const slug of [
    "../secrets",
    "https://example.com",
    "park-view?url=https://example.com",
    "Park-View",
    "-park",
    "park--view",
    "x".repeat(101),
    "",
  ]) {
    assert.deepEqual(await readProjectData(slug, read), {
      status: 404,
      project: null,
    });
  }
  assert.equal(paths.length, 1);
});

test("project route preserves unavailable, disabled and missing states without leaking transport errors", async () => {
  for (const status of [403, 404, 503])
    assert.deepEqual(
      await readProjectData("park-view", async () => ({ status, data: null })),
      { status, project: null },
    );
  assert.deepEqual(
    await readProjectData("park-view", async () => {
      throw new Error("private upstream details");
    }),
    { status: 503, project: null },
  );
  for (const data of [
    null,
    {},
    { ...project, slug: "wrong-project" },
    { ...project, developer: null },
    { ...project, amenities: null },
    { ...project, typologies: "invalid" },
  ])
    assert.deepEqual(
      await readProjectData("park-view", async () => ({ status: 200, data })),
      { status: 503, project: null },
    );
});
