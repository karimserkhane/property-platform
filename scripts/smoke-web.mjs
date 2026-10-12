import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import { setTimeout } from "node:timers/promises";
import { getDirection, locales } from "../apps/web/src/i18n/locales.ts";
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

  for (const locale of locales) {
    const response = await fetch(`${origin}/${locale}`);
    assert.equal(response.status, 200, locale);
    assert.equal(response.headers.get("x-content-type-options"), "nosniff");
    assert.equal(response.headers.get("x-frame-options"), "DENY");
    const html = await response.text();
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
    assert.ok(html.includes("abu-dhabi-night-1920.webp"), locale);
    assert.equal(
      (html.match(/<img\b/g) ?? []).length,
      1,
      `${locale}: only the first photograph is mounted`,
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
  }
  for (const path of [
    "parcels?bbox=54.4,24.4,54.5,24.5",
    "map-context?bbox=54.4,24.4,54.5,24.5",
    "references",
    "imagery",
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
