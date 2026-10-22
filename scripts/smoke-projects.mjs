import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { PROJECT_DIRECTORY_PAGE_SIZE } from "../apps/web/src/features/projects/directory-navigation.ts";
import { projectLocationBounds } from "../apps/web/src/features/projects/neighbourhood-focus.ts";
import {
  groupProjectTypologies,
  projectAmenityKey,
  projectEvidenceSources,
  projectMedia,
} from "../apps/web/src/features/projects/presentation.ts";
import { getDirection, locales } from "../apps/web/src/i18n/locales.ts";

// Opt-in integration checks against the compiled web and its real, imported API.
// This includes disclosure contents, unlike a check limited to first-screen text.
const origin = new URL(
  process.env.PROPERTY_PLATFORM_PROJECT_SMOKE_ORIGIN ?? "http://127.0.0.1:3102",
);
assert.ok(
  ["http:", "https:"].includes(origin.protocol) &&
    !origin.username &&
    !origin.password,
);
assert.equal(origin.pathname, "/", "Configure an origin without a path");
const selectedLocales =
  process.env.PROPERTY_PLATFORM_PROJECT_SMOKE_LOCALES?.split(",") ?? locales;
assert.ok(
  selectedLocales.length &&
    selectedLocales.every((locale) => locales.includes(locale)),
);
const projects = JSON.parse(
  await readFile(
    "apps/api/src/property_platform/modules/evidence/project_registry.json",
    "utf8",
  ),
);
const navigation = JSON.parse(
  await readFile("packages/contracts/territories.json", "utf8"),
);
const details = new Map();

async function get(path) {
  return fetch(new URL(path, origin), { signal: AbortSignal.timeout(30000) });
}
async function bounded(items, run) {
  let next = 0;
  const results = await Promise.allSettled(
    Array.from({ length: Math.min(3, items.length) }, async () => {
      while (next < items.length) await run(items[next++]);
    }),
  );
  const failures = results
    .filter((result) => result.status === "rejected")
    .map((result) => result.reason);
  if (failures.length)
    throw new AggregateError(failures, "Live project checks failed");
}
function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#x27;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
function renderedMarkup(html) {
  // Flight scripts can contain API props. They are not rendered document text.
  return html
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, "");
}
function expectedCitations(detail) {
  return (
    Number(!!detail.handover) +
    Number(!!detail.programme_total) +
    detail.amenities.length +
    [...projectMedia(detail).documents, ...projectMedia(detail).visuals]
      .length +
    groupProjectTypologies(detail.typologies).reduce(
      (sum, group) =>
        sum +
        projectEvidenceSources(group.claims.map((claim) => claim.source))
          .length,
      0,
    )
  );
}

let loaded = 0;
await bounded(projects, async (project) => {
  const response = await get(`/api/atlas/projects/${project.slug}`);
  assert.equal(response.status, 200, `${project.slug}: map preview relay`);
  assert.equal(response.headers.get("cache-control"), "no-store");
  const detail = await response.json();
  assert.equal(detail.slug, project.slug);
  assert.equal(detail.developer.name, project.developer.name);
  assert.ok(
    Array.isArray(detail.map_locations),
    `${project.slug}: typed map locations`,
  );
  const area = navigation.territories.find(
    (item) => item.id === detail.territory,
  );
  if (detail.map_locations.length) {
    assert.ok(
      area && projectLocationBounds(detail.map_locations, area.bounds),
      `${project.slug}: map locations inside their territory`,
    );
    for (const location of detail.map_locations) {
      assert.ok(["place", "building", "parcel"].includes(location.target));
      assert.equal(location.name, project.name);
      assert.ok(
        location.source.url.startsWith("https://") &&
          location.source.retrieved_at,
      );
    }
  }
  details.set(project.slug, detail);
  if (++loaded % 48 === 0)
    console.log(`API: ${loaded}/${projects.length} projects checked`);
});
console.log(`API: ${projects.length} project contracts checked`);

let checked = 0;
for (const locale of selectedLocales) {
  const messages = JSON.parse(
    await readFile(`apps/web/messages/${locale}.json`, "utf8"),
  );
  const directorySlugs = new Set();
  for (
    let offset = 0;
    offset < projects.length;
    offset += PROJECT_DIRECTORY_PAGE_SIZE
  ) {
    const response = await get(`/${locale}/projects?offset=${offset}`);
    assert.equal(response.status, 200, `${locale}: directory page ${offset}`);
    const markup = renderedMarkup(await response.text());
    const slugs = [
      ...markup.matchAll(
        new RegExp(`href="/${locale}/projects/([a-z0-9-]+)"`, "g"),
      ),
    ].map((match) => match[1]);
    assert.equal(
      slugs.length,
      Math.min(PROJECT_DIRECTORY_PAGE_SIZE, projects.length - offset),
      `${locale}: bounded directory results`,
    );
    for (const slug of slugs) {
      assert.ok(
        !directorySlugs.has(slug),
        `${locale}: no duplicate directory entries across pages`,
      );
      directorySlugs.add(slug);
      const detail = details.get(slug);
      assert.ok(detail, `${locale}: registered directory identity ${slug}`);
      assert.equal(
        markup.includes(`project=${slug}`),
        detail.map_locations.length > 0,
        `${locale}/${slug}: map link requires a usable identity`,
      );
    }
  }
  assert.deepEqual(
    [...directorySlugs].sort(),
    projects.map((project) => project.slug).sort(),
    `${locale}: all projects reachable through pagination`,
  );

  await bounded(projects, async (project) => {
    const detail = details.get(project.slug);
    const context = `${locale}/${project.slug}`;
    const response = await get(`/${locale}/projects/${project.slug}`);
    assert.equal(response.status, 200, context);
    const markup = renderedMarkup(await response.text());
    assert.ok(
      markup.includes('data-page="project"'),
      `${context}: populated dossier`,
    );
    for (const id of [
      "project-overview",
      ...(detail.typologies.length ? ["project-homes"] : []),
      ...(detail.amenities.length ? ["project-amenities"] : []),
      "project-documents",
      "project-location",
      "project-purchase",
    ])
      assert.ok(markup.includes(`id="${id}"`), `${context}: navigable ${id}`);
    for (const original of [project.name, project.developer.name])
      assert.ok(
        markup.includes(escapeHtml(original)),
        `${context}: original identity ${original}`,
      );
    assert.ok(
      markup.includes(`territory=${project.territory_id}`),
      `${context}: original territory navigation`,
    );
    assert.ok(
      markup.includes(`lang="${locale}"`) &&
        markup.includes(`dir="${getDirection(locale)}"`),
      `${context}: locale and direction`,
    );
    assert.ok(
      markup.includes(`data-neighbourhood="${detail.territory}"`),
      `${context}: correct neighbourhood`,
    );
    assert.ok(
      !markup.includes('class="maplibregl-canvas"') &&
        !markup.includes("<iframe"),
      `${context}: map and external embeds remain deferred`,
    );
    assert.equal(
      /<video[^>]*\bautoplay\b/i.test(markup),
      false,
      `${context}: no autoplay`,
    );
    for (const video of markup.matchAll(/<video\b[^>]*>/gi))
      assert.ok(
        video[0].includes('preload="none"') && /\bcontrols\b/.test(video[0]),
        `${context}: controlled deferred video`,
      );
    for (const reference of detail.media.filter(
      (item) => item.rights_status !== "blocked",
    )) {
      assert.ok(
        markup.includes(escapeHtml(reference.source_url)),
        `${context}: accepted media reference`,
      );
      if (reference.rights_status !== "approved") {
        const sourceUrl = escapeHtml(reference.source_url);
        assert.ok(
          !markup.includes(`<img src="${sourceUrl}`) &&
            !markup.includes(`<source src="${sourceUrl}`),
          `${context}: reference does not grant media publication`,
        );
      }
    }
    const citationCount = [
      ...markup.matchAll(/\bdata-project-evidence-source[=\s>]/g),
    ].length;
    assert.equal(
      citationCount,
      expectedCitations(detail),
      `${context}: one citation per source capture, not per extractor note`,
    );
    assert.ok(
      !/<(?:pre|code|blockquote)\b/i.test(markup),
      `${context}: no raw source payload or extractor quotation in public markup`,
    );
    const text = markup.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ");
    for (const token of [
      "availableBedrooms",
      "unitTypes",
      "bedrooms=",
      "PSI public page",
      "data[propertyId=",
      "JSON-LD",
      "OneBedroom=",
      "Studio=",
    ])
      assert.ok(
        !text.includes(token),
        `${context}: technical token leaked: ${token}`,
      );
    for (const source of [
      ...detail.typologies,
      ...detail.amenities,
      ...detail.media,
      detail.handover,
      detail.programme_total,
    ]
      .filter(Boolean)
      .map((item) => item.source)) {
      if (source.evidence_pointer)
        assert.ok(
          !text.includes(
            escapeHtml(source.evidence_pointer).replace(/\s+/g, " "),
          ),
          `${context}: extractor locator hidden from public disclosures`,
        );
    }
    for (const { code } of detail.amenities) {
      // The actual multilingual headings must be present, not only dictionary keys.
      const key = projectAmenityKey(code);
      if (key)
        assert.ok(
          markup.includes(escapeHtml(messages.Project[key])),
          `${context}: translated amenity ${code}`,
        );
    }
    if (++checked % 48 === 0)
      console.log(
        `Dossiers: ${checked}/${projects.length * selectedLocales.length} checked`,
      );
  });
  console.log(
    `${locale}: ${projects.length} dossiers and all directory pages passed`,
  );
}
assert.equal(
  (await get("/api/atlas/projects/the-district?url=https://example.com"))
    .status,
  400,
);
assert.equal((await get("/api/atlas/projects/INVALID")).status, 404);
assert.equal(
  (await get("/en/projects/project-that-does-not-exist")).status,
  404,
);
console.log(
  `Live project smoke checks passed for ${projects.length} projects in ${selectedLocales.length} languages (${checked} dossier pages).`,
);
