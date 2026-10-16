import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { projectLocationBounds } from "../apps/web/src/features/projects/neighbourhood-focus.ts";
import { locales } from "../apps/web/src/i18n/locales.ts";

// Explicit live check: the compiled site and API must already be running and imported.
// CI's smoke-web.mjs separately checks the translated state when no API is available.
const origin = new URL(
  process.env.PROPERTY_PLATFORM_PROJECT_SMOKE_ORIGIN ?? "http://127.0.0.1:3102",
);
assert.ok(
  ["http:", "https:"].includes(origin.protocol) &&
    !origin.username &&
    !origin.password,
);
assert.equal(origin.pathname, "/", "Configure an origin without a path");
const projects = JSON.parse(
  await readFile(
    "apps/api/src/property_platform/modules/evidence/project_registry.json",
    "utf8",
  ),
);
const details = new Map();
const navigation = JSON.parse(
  await readFile("packages/contracts/territories.json", "utf8"),
);
for (const project of projects) {
  const response = await fetch(
    new URL(`/api/atlas/projects/${project.slug}`, origin),
  );
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
      `${project.slug}: stored project locations remain inside their own territory`,
    );
    for (const location of detail.map_locations) {
      assert.ok(["place", "building", "parcel"].includes(location.target));
      assert.equal(location.name, project.name);
      assert.ok(location.source.url.startsWith("https://"));
      assert.ok(location.source.retrieved_at);
    }
  }
  details.set(project.slug, detail);
}
for (const locale of locales) {
  const directory = await fetch(new URL(`/${locale}/projects`, origin));
  assert.equal(directory.status, 200);
  const directoryHtml = await directory.text();
  for (const project of projects) {
    assert.ok(
      directoryHtml.includes(`/projects/${project.slug}`),
      `${locale}: directory contains ${project.slug}`,
    );
    assert.ok(
      directoryHtml.includes(`project=${project.slug}`),
      `${locale}: directory opens ${project.slug} inside the map`,
    );
    const detail = details.get(project.slug);
    const response = await fetch(
      new URL(`/${locale}/projects/${project.slug}`, origin),
      { signal: AbortSignal.timeout(15000) },
    );
    assert.equal(response.status, 200, `${locale}/${project.slug}`);
    const html = await response.text();
    for (const id of [
      "project-overview",
      ...(detail.typologies.length ? ["project-homes"] : []),
      ...(detail.amenities.length ? ["project-amenities"] : []),
      ...(detail.media.some((item) =>
        ["brochure", "floor_plan", "factsheet"].includes(item.role),
      )
        ? ["project-documents"]
        : []),
      "project-location",
    ])
      assert.ok(
        html.includes(`id="${id}"`),
        `${locale}/${project.slug}: navigable property dossier section ${id}`,
      );
    assert.ok(
      html.includes('data-page="project"'),
      `${locale}/${project.slug}: populated project page, not unavailable state`,
    );
    assert.ok(
      html.includes(project.name),
      `${locale}/${project.slug}: original project identity`,
    );
    assert.ok(
      html.includes(project.developer.name),
      `${locale}/${project.slug}: developer`,
    );
    assert.ok(
      html.includes(`territory=${project.territory_id}`),
      `${locale}/${project.slug}: original territory navigation`,
    );
    assert.ok(
      html.includes(`lang="${locale}"`),
      `${locale}/${project.slug}: locale`,
    );
    assert.ok(
      html.includes(`data-neighbourhood="${detail.territory}"`),
      `${locale}/${project.slug}: neighbourhood follows the stored territory`,
    );
    assert.equal(
      html.includes('class="maplibregl-canvas"'),
      false,
      `${locale}/${project.slug}: map engine is deferred`,
    );
    assert.ok(
      html.includes(`dir="${locale === "ar" ? "rtl" : "ltr"}"`),
      `${locale}/${project.slug}: direction`,
    );
    assert.equal(
      html.includes("<iframe"),
      false,
      `${locale}/${project.slug}: no embedded source video`,
    );
    assert.equal(
      /<video[^>]*\bautoplay\b/i.test(html),
      false,
      `${locale}/${project.slug}: no autoplay`,
    );
    for (const video of html.matchAll(/<video\b[^>]*>/gi)) {
      assert.ok(
        video[0].includes('preload="none"') && /\bcontrols\b/.test(video[0]),
        `${locale}/${project.slug}: controlled, deferred video`,
      );
    }
    for (const reference of project.media_references) {
      assert.ok(
        html.includes(reference.source_url),
        `${locale}/${project.slug}: reviewed media source remains available`,
      );
      assert.equal(
        html.includes(`<iframe src="${reference.source_url}`),
        false,
      );
      assert.equal(html.includes(`<img src="${reference.source_url}`), false);
      assert.equal(
        html.includes(`<source src="${reference.source_url}`),
        false,
      );
    }
  }
}
assert.equal(
  (
    await fetch(
      new URL(
        "/api/atlas/projects/the-district?url=https://example.com",
        origin,
      ),
    )
  ).status,
  400,
);
assert.equal(
  (await fetch(new URL("/api/atlas/projects/INVALID", origin))).status,
  404,
);
assert.equal(
  (await fetch(new URL("/en/projects/project-that-does-not-exist", origin)))
    .status,
  404,
);
console.log(
  `Live project smoke checks passed for ${projects.length} projects in ${locales.length} configured languages.`,
);
