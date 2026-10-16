import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { setTimeout } from "node:timers/promises";
import { HOME_SCENES } from "../apps/web/src/features/atlas/home-scenes.ts";
import {
  getDirection,
  localeDefinitions,
  locales,
} from "../apps/web/src/i18n/locales.ts";
import { getFontPreloads } from "../apps/web/src/theme/fonts.ts";
import { brand } from "../packages/branding/src/brand.ts";

const escapedBrandName = brand.displayName.replace(
  /[&<>"']/g,
  (character) =>
    ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#x27;",
    })[character],
);
const origin = "http://127.0.0.1:3101";
const server = spawn(
  process.execPath,
  ["apps/web/.next/standalone/apps/web/server.js"],
  {
    env: {
      ...process.env,
      PROPERTY_PLATFORM_ENABLE_LOCAL_PREVIEW: "",
      PORT: "3101",
      HOSTNAME: "127.0.0.1",
    },
    stdio: "inherit",
  },
);
let startupError;
server.on("error", (error) => {
  startupError = error;
});

try {
  let ready = false;
  for (let attempt = 0; attempt < 40; attempt++) {
    if (startupError) throw startupError;
    if (server.exitCode !== null)
      throw new Error("Web server exited during startup");
    try {
      ready = (await fetch(`${origin}/en`)).ok;
      if (ready) break;
    } catch {
      // Wait for the child server to bind its local socket.
    }
    await setTimeout(250);
  }
  assert.ok(ready, "Web server must become ready within 10 seconds");

  const root = await fetch(`${origin}/`, {
    redirect: "manual",
    headers: { "Accept-Language": "ar,ru;q=0.9" },
  });
  assert.ok([307, 308].includes(root.status));
  assert.equal(new URL(root.headers.get("location"), origin).pathname, "/en");
  const mark = await fetch(new URL(brand.webMarkPath, origin));
  assert.equal(
    mark.status,
    200,
    "Brand mark must be part of the standalone artifact",
  );
  assert.ok(mark.headers.get("content-type").includes("image/svg+xml"));

  const photoCredits = JSON.parse(
    await readFile("apps/web/public/images/uae/credits.json", "utf8"),
  );
  for (const asset of photoCredits.assets) {
    const photo = await fetch(`${origin}/images/uae/${asset.file}`);
    assert.equal(photo.status, 200, asset.file);
    assert.ok(
      photo.headers.get("content-type").includes("image/webp"),
      asset.file,
    );
    assert.equal(
      (await photo.arrayBuffer()).byteLength,
      asset.byte_length,
      asset.file,
    );
  }
  const fontCredits = JSON.parse(
    await readFile("apps/web/public/fonts/credits.json", "utf8"),
  );
  for (const asset of fontCredits.assets) {
    const response = await fetch(`${origin}/fonts/${asset.file}`);
    assert.equal(response.status, 200, asset.file);
    assert.ok(
      response.headers.get("content-type").includes("font/woff2"),
      asset.file,
    );
    const bytes = Buffer.from(await response.arrayBuffer());
    assert.equal(bytes.byteLength, asset.bytes, asset.file);
    assert.equal(
      createHash("sha256").update(bytes).digest("hex"),
      asset.sha256,
      asset.file,
    );
  }

  for (const locale of locales) {
    const response = await fetch(`${origin}/${locale}`);
    assert.equal(response.status, 200, locale);
    assert.equal(response.headers.get("x-content-type-options"), "nosniff");
    assert.equal(response.headers.get("x-frame-options"), "DENY");
    const html = await response.text();
    const preloadedFonts = [
      ...html.matchAll(/href="(\/fonts\/[^"\s]+\.woff2)"/g),
    ].map((match) => match[1]);
    const fontBytes = [...new Set(preloadedFonts)].reduce((total, path) => {
      const asset = fontCredits.assets.find(
        (font) => `/fonts/${font.file}` === path,
      );
      assert.ok(asset, `${locale}: known font preload`);
      return total + asset.bytes;
    }, 0);
    assert.ok(
      fontBytes > 0 && fontBytes < 200000,
      `${locale}: bounded font preload budget`,
    );
    assert.deepEqual(
      [...new Set(preloadedFonts)].sort(),
      getFontPreloads(localeDefinitions[locale].fontProfile)
        .map((font) => font.href)
        .sort(),
      `${locale}: font preloads follow the shared locale registry`,
    );
    assert.ok(
      html.includes(`<title>${escapedBrandName}</title>`),
      `${locale}: configured brand title`,
    );
    assert.ok(
      html.includes(`aria-label="${escapedBrandName}"`),
      `${locale}: configured brand navigation`,
    );
    const messages = JSON.parse(
      await readFile(`apps/web/messages/${locale}.json`, "utf8"),
    );
    assert.ok(html.includes(`lang="${locale}"`), locale);
    assert.ok(html.includes(`dir="${getDirection(locale)}"`), locale);
    assert.ok(html.includes(messages.Home.title), locale);
    assert.ok(html.includes(`${HOME_SCENES[0].image}-1920.webp`), locale);
    assert.ok(html.includes(messages.Coverage.title), locale);
    for (const territory of [
      "dubai",
      "sharjah",
      "ajman",
      "umm-al-quwain",
      "ras-al-khaimah",
      "fujairah",
      "abu-dhabi",
    ]) {
      assert.ok(
        html.includes(`territory=${territory}`),
        `${locale}: regional navigation ${territory}`,
      );
    }
    assert.equal(
      (html.match(/<img\b/g) ?? []).length,
      3,
      `${locale}: one hero photograph and two lazy editorial photographs`,
    );
    assert.equal(
      (html.match(/fetchPriority="high"/g) ?? []).length,
      1,
      `${locale}: only the hero photograph is prioritized`,
    );
    assert.ok(
      html.includes('loading="lazy"'),
      `${locale}: editorial photograph defers loading`,
    );
    assert.ok(
      html.includes('href="#discovery"'),
      `${locale}: native discovery anchor`,
    );
    assert.ok(
      html.includes(messages.Home.scroll),
      `${locale}: translated discovery link`,
    );
    assert.ok(html.includes('href="#regions"'), `${locale}: regions anchor`);
    assert.ok(
      html.includes(messages.Home.invitationTitle),
      `${locale}: invitation`,
    );
    assert.ok(html.includes("<select"), locale);
    const cssPath = html.match(/href="([^"\s]+\.css[^"\s]*)"/)?.[1];
    assert.ok(cssPath, `${locale}: stylesheet missing`);
    assert.equal((await fetch(new URL(cssPath, origin))).status, 200, locale);
    const explore = await fetch(`${origin}/${locale}/explore`);
    assert.equal(explore.status, 200, locale);
    const exploreHtml = await explore.text();
    assert.ok(exploreHtml.includes(messages.Atlas.explore), locale);
    assert.ok(
      exploreHtml.includes(`<title>${escapedBrandName}</title>`),
      `${locale}: configured atlas title`,
    );
    const project = await fetch(`${origin}/${locale}/projects/the-district`);
    assert.equal(
      project.status,
      200,
      `${locale}: project route remains usable without a preview API`,
    );
    const projectHtml = await project.text();
    const directory = await fetch(`${origin}/${locale}/projects`);
    assert.equal(directory.status, 200, `${locale}: project directory`);
    const directoryHtml = await directory.text();
    assert.ok(directoryHtml.includes('data-page="project-directory"'));
    assert.ok(directoryHtml.includes(messages.Project.unavailable));
    assert.ok(directoryHtml.includes(`dir="${getDirection(locale)}"`));
    assert.ok(
      projectHtml.includes(messages.Project.unavailableTitle),
      `${locale}: translated project unavailable title`,
    );
    assert.ok(
      projectHtml.includes(messages.Project.unavailable),
      `${locale}: translated project unavailable state`,
    );
    assert.ok(
      projectHtml.includes(`dir="${getDirection(locale)}"`),
      `${locale}: project direction`,
    );
    assert.equal(
      projectHtml.includes("<iframe"),
      false,
      `${locale}: no arbitrary media embed`,
    );
  }
  for (const slug of ["the-district", "vista-3", "park-view"])
    assert.equal(
      (await fetch(`${origin}/en/projects/${slug}`)).status,
      200,
      `${slug}: unavailable state without API`,
    );
  assert.equal((await fetch(`${origin}/en/projects/INVALID`)).status, 404);
  for (const path of [
    "parcels?bbox=54.4,24.4,54.5,24.5",
    "map-context?bbox=54.4,24.4,54.5,24.5",
    "references",
    "imagery",
    "territories",
    "property-media/00000000-0000-0000-0000-000000000000",
    "project-media/00000000-0000-0000-0000-000000000000",
    "projects/the-district",
  ]) {
    assert.equal(
      (await fetch(`${origin}/api/atlas/${path}`)).status,
      403,
      path,
    );
    const endpoint = path.split("?")[0];
    assert.equal(
      (await fetch(`${origin}/api/atlas/${endpoint}?url=https://example.com`))
        .status,
      400,
      endpoint,
    );
    assert.equal(
      (await fetch(`${origin}/api/atlas/${endpoint}`, { method: "POST" }))
        .status,
      405,
      endpoint,
    );
  }
  assert.equal(
    (await fetch(`${origin}/api/atlas/parcels?url=https://example.com`)).status,
    400,
  );
  assert.equal(
    (await fetch(`${origin}/api/atlas/parcels/invalid-id`)).status,
    404,
  );
  assert.equal((await fetch(`${origin}/xx`)).status, 404);
  console.log(`Standalone smoke checks passed for ${locales.length} locales.`);
} finally {
  server.kill();
}
