import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import { setTimeout } from "node:timers/promises";
import { getDirection, locales } from "../apps/web/src/i18n/locales.ts";

const origin = "http://127.0.0.1:3101";
const server = spawn(
  process.execPath,
  ["apps/web/.next/standalone/apps/web/server.js"],
  {
    env: {
      ...process.env,
      LIWA_ENABLE_LOCAL_PREVIEW: "",
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

  for (const locale of locales) {
    const response = await fetch(`${origin}/${locale}`);
    assert.equal(response.status, 200, locale);
    assert.equal(response.headers.get("x-content-type-options"), "nosniff");
    assert.equal(response.headers.get("x-frame-options"), "DENY");
    const html = await response.text();
    const messages = JSON.parse(
      await readFile(`apps/web/messages/${locale}.json`, "utf8"),
    );
    assert.ok(html.includes(`lang="${locale}"`), locale);
    assert.ok(html.includes(`dir="${getDirection(locale)}"`), locale);
    assert.ok(html.includes(messages.Home.title), locale);
    assert.ok(html.includes("<select"), locale);
    const cssPath = html.match(/href="([^"\s]+\.css[^"\s]*)"/)?.[1];
    assert.ok(cssPath, `${locale}: stylesheet missing`);
    assert.equal((await fetch(new URL(cssPath, origin))).status, 200, locale);
    const explore = await fetch(`${origin}/${locale}/explore`);
    assert.equal(explore.status, 200, locale);
    assert.ok((await explore.text()).includes(messages.Atlas.explore), locale);
  }
  assert.equal(
    (await fetch(`${origin}/api/atlas/parcels?bbox=54.4,24.4,54.5,24.5`))
      .status,
    403,
  );
  assert.equal(
    (await fetch(`${origin}/api/atlas/parcels?url=https://example.com`)).status,
    400,
  );
  assert.equal(
    (await fetch(`${origin}/api/atlas/parcels/invalid-id`)).status,
    404,
  );
  assert.equal(
    (await fetch(`${origin}/api/atlas/parcels`, { method: "POST" })).status,
    405,
  );
  assert.equal((await fetch(`${origin}/xx`)).status, 404);
  console.log(`Standalone smoke checks passed for ${locales.length} locales.`);
} finally {
  server.kill();
}
