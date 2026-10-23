import assert from "node:assert/strict";
import test from "node:test";
import { readProjectData } from "../src/features/projects/data.ts";
import {
  approvedDelivery,
  formatHandover,
  formatProjectDate,
  groupProjectTypologies,
  mediaLabel,
  playableMedia,
  projectAmenityKey,
  projectEvidenceSources,
  projectMedia,
  projectRelations,
  projectWebsite,
  safeSourceUrl,
} from "../src/features/projects/presentation.ts";

test("field-specific notes share one capture citation while separate versions retain their provenance", () => {
  const source = Object.freeze({
    url: "https://aldar.example/project",
    name: "Aldar Properties",
    kind: "developer",
    language: "en",
    retrieved_at: "2026-10-17T12:00:00Z",
    content_sha256: "version-1",
  });
  const sources = ["Studio", 1, 2].map((bedrooms) =>
    Object.freeze({
      ...source,
      evidence_pointer: `bedrooms[${bedrooms}]`,
    }),
  );
  const evidence = projectEvidenceSources(sources);
  assert.equal(evidence.length, 1);
  assert.equal(evidence[0].source, sources[0]);
  assert.equal(
    projectEvidenceSources([...sources].reverse())[0].key,
    evidence[0].key,
  );
  for (const variation of [
    { retrieved_at: "2026-10-20T12:00:00Z", historical: true },
    { content_sha256: "version-2" },
    { url: "https://agency.example/project", kind: "broker" },
    { ingested_at: "2026-10-21T12:00:00Z" },
  ])
    assert.equal(
      projectEvidenceSources([...sources, { ...source, ...variation }]).length,
      2,
    );
  assert.equal(sources.length, 3);
  assert.equal(sources[0].evidence_pointer, "bedrooms[Studio]");
  assert.deepEqual(projectEvidenceSources([]), []);
});

test("source dates use the active locale and malformed metadata cannot break a dossier", () => {
  assert.equal(formatProjectDate("not-a-date", "fr"), null);
  assert.equal(formatProjectDate("", "en"), null);
  assert.equal(formatProjectDate("2026-10-17T22:30:00Z", "fr"), "18 oct. 2026");
  assert.notEqual(
    formatProjectDate("2026-10-17T12:00:00Z", "en"),
    formatProjectDate("2026-10-17T12:00:00Z", "fr"),
  );
});

test("amenity codes select translated interface labels without rewriting unknown original evidence", () => {
  assert.equal(projectAmenityKey("gym"), "amenityGym");
  assert.equal(projectAmenityKey("swimming_pool"), "amenityPool");
  for (const code of ["unknown_future_facility", "constructor", "toString"])
    assert.equal(projectAmenityKey(code), null);
});

test("a project website needs exact first-party evidence before it is called official", () => {
  const website_url = "https://agency.example/project";
  const project = {
    website_url,
    sources: [{ url: website_url, kind: "broker" }],
  };
  assert.equal(projectWebsite(project).official, false);
  assert.equal(projectWebsite({ ...project, sources: [] }).official, false);
  assert.equal(
    projectWebsite({
      ...project,
      sources: [
        { url: "https://agency.example/another-project", kind: "developer" },
      ],
    }).official,
    false,
  );
  for (const kind of ["developer", "publisher"])
    assert.equal(
      projectWebsite({ ...project, sources: [{ url: website_url, kind }] })
        .official,
      true,
    );
  assert.equal(
    projectWebsite({ ...project, website_url: "javascript:alert(1)" }).url,
    null,
  );
});

test("home types group recorded bedroom variants without losing generic or corroborating claims", () => {
  const claim = (property_type, bedrooms, origin) =>
    Object.freeze({
      property_type,
      bedrooms,
      original_text: `${origin}: ${property_type} ${bedrooms ?? "unspecified"}`,
      source: Object.freeze({
        url: `https://${origin}.example/project`,
        historical: origin === "archived",
      }),
    });
  const generic = claim("apartment", null, "developer");
  const duplex = claim("duplex", 4, "developer");
  const two = claim("apartment", 2, "agency");
  const one = claim("apartment", 1, "developer");
  const historicalTwo = claim("apartment", 2, "archived");
  const rows = Object.freeze([generic, duplex, two, one, historicalTwo]);
  const groups = groupProjectTypologies(rows);
  assert.deepEqual(groups, [
    {
      property_type: "apartment",
      bedrooms: [1, 2],
      claims: [generic, two, one, historicalTwo],
    },
    { property_type: "duplex", bedrooms: [4], claims: [duplex] },
  ]);
  assert.equal(groups[0].claims[0], generic);
  assert.equal(groups[0].claims[3].source, historicalTwo.source);
  assert.deepEqual(rows, [generic, duplex, two, one, historicalTwo]);
});

test("unknown-only home types stay unknown and bedroom claims never cross property types", () => {
  const rows = [
    {
      property_type: "apartment",
      bedrooms: null,
      original_text: "Apartments",
      source: {},
    },
    {
      property_type: "studio",
      bedrooms: 0,
      original_text: "Studios",
      source: {},
    },
    {
      property_type: "townhouse",
      bedrooms: 3,
      original_text: "Three-bedroom townhouses",
      source: {},
    },
    {
      property_type: "villa",
      bedrooms: -1,
      original_text: "Invalid source count",
      source: {},
    },
  ];
  assert.deepEqual(
    groupProjectTypologies(rows).map(({ property_type, bedrooms }) => ({
      property_type,
      bedrooms,
    })),
    [
      { property_type: "apartment", bedrooms: [] },
      { property_type: "studio", bedrooms: [0] },
      { property_type: "townhouse", bedrooms: [3] },
      { property_type: "villa", bedrooms: [] },
    ],
  );
  assert.equal(groupProjectTypologies(rows)[3].claims[0], rows[3]);
  assert.deepEqual(groupProjectTypologies([]), []);
});

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

test("map and dossier select a licensed hero without promoting document or external references", () => {
  const image = {
    id: "photo",
    kind: "image",
    role: "gallery",
    mime_type: "image/webp",
    rights_status: "approved",
    delivery_url: "https://cdn.example.com/photo.webp",
  };
  const hero = { ...image, id: "hero", role: "hero" };
  const reference = {
    ...hero,
    id: "reference",
    rights_status: "reference_only",
  };
  const blocked = { ...hero, id: "blocked", rights_status: "blocked" };
  const document = {
    ...hero,
    id: "document",
    kind: "document",
    mime_type: "application/pdf",
  };
  assert.deepEqual(
    projectMedia({ media: [reference, blocked, image, document, hero] }),
    {
      hero,
      documents: [document],
      visuals: [reference, image, hero],
    },
  );
  assert.equal(
    projectMedia({ media: [reference, blocked, document] }).hero,
    null,
  );
  assert.equal(projectMedia({ media: [image] }).hero, image);
  assert.deepEqual(projectMedia({ media: [] }), {
    hero: null,
    documents: [],
    visuals: [],
  });
});

test("floor plan images stay with documents and never become a cropped cover photograph", () => {
  const plan = {
    id: "plan-image",
    kind: "image",
    role: "floor_plan",
    mime_type: "image/webp",
    rights_status: "approved",
    delivery_url: "https://cdn.example.com/floor-plan.webp",
  };
  const photo = { ...plan, id: "exterior", role: "gallery" };
  const blockedPlan = { ...plan, id: "withdrawn", rights_status: "blocked" };
  assert.deepEqual(projectMedia({ media: [plan, photo, blockedPlan] }), {
    hero: photo,
    documents: [plan],
    visuals: [photo],
  });
  assert.deepEqual(projectMedia({ media: [plan] }), {
    hero: null,
    documents: [plan],
    visuals: [],
  });
  for (const role of ["brochure", "factsheet"]) {
    const documentImage = { ...plan, role };
    assert.deepEqual(projectMedia({ media: [documentImage, photo] }), {
      hero: photo,
      documents: [documentImage],
      visuals: [photo],
    });
  }
});

test("media labels use the reviewed document role and preserve other media kinds", () => {
  assert.equal(mediaLabel({ kind: "image", role: "floor_plan" }), "floorPlans");
  assert.equal(mediaLabel({ kind: "document", role: "brochure" }), "brochure");
  assert.equal(
    mediaLabel({ kind: "document", role: "factsheet" }),
    "factsheet",
  );
  assert.equal(mediaLabel({ kind: "document", role: "unknown" }), "document");
  assert.equal(mediaLabel({ kind: "video", role: "tour" }), "video");
});

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

test("component links need a routable slug and keep only safe source references", () => {
  const relation = (slug, source_url = `https://aldar.example/${slug}`) => ({
    slug,
    name: slug,
    component: "Tower 1",
    basis: "Named by the source.",
    source_url,
    retrieved_at: "2026-10-23T08:00:00Z",
  });
  const { parent, components } = projectRelations({
    parent: relation("gate-arc", "javascript:alert(1)"),
    components: [
      relation("the-gate-tower-1"),
      relation("../admin"),
      relation("Tower-2"),
    ],
  });
  assert.equal(parent.slug, "gate-arc");
  assert.equal(parent.source_url, null);
  assert.deepEqual(
    components.map((item) => [item.slug, item.source_url]),
    [["the-gate-tower-1", "https://aldar.example/the-gate-tower-1"]],
  );
  assert.deepEqual(projectRelations({}), { parent: null, components: [] });
});
