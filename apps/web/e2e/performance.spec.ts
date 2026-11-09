import { expect, type Page, test } from "@playwright/test";
import { budgets } from "./performance-budgets";

// Budgets hold for the demonstration package only: its data is fixed. Elsewhere the
// journeys are skipped, because the size of the local database decides the result.
test.skip(
  process.env.E2E_PERFORMANCE_BUDGETS !== "1",
  "performance budgets only apply to the demonstration package",
);

const EXPLORER = "/en/explore?territory=al-reem-island";
const QUIET_MS = 2000;
// Chrome DevTools "Fast 4G" and the 4x slowdown Lighthouse applies to a phone.
const FOUR_G = {
  offline: false,
  latency: 165,
  downloadThroughput: (9 * 1024 * 1024) / 8,
  uploadThroughput: (1.5 * 1024 * 1024) / 8,
};
const CPU_SLOWDOWN = 4;
const TIME_SAMPLES = 3;

type Transfer = { url: URL; type: string; bytes: number };

// `requestfinished` also reports the tiles MapLibre fetches from its web workers.
function recordTransfers(page: Page) {
  const transfers: Transfer[] = [];
  const reading: Promise<void>[] = [];
  page.on("requestfinished", (request) => {
    reading.push(
      request.sizes().then((sizes) => {
        transfers.push({
          url: new URL(request.url()),
          type: request.resourceType(),
          bytes: sizes.responseBodySize,
        });
      }),
    );
  });
  return async () => {
    await page.waitForLoadState("networkidle");
    await Promise.all(reading);
    return transfers.filter(
      (item) => item.url.origin === new URL(page.url()).origin,
    );
  };
}

// The explorer keeps a reveal animation running, so MapLibre's "idle" never fires. The map
// counts as usable once its canvas is shown and its first reads are over: at least one
// parcel tile received, then no read in flight for QUIET_MS (not counted in the time).
function trackAtlasReads(page: Page) {
  let inFlight = 0;
  let tiles = 0;
  let lastDone = 0;
  const isRead = (url: string) =>
    new URL(url).pathname.startsWith("/api/atlas/");
  page.on("request", (request) => {
    if (isRead(request.url())) inFlight += 1;
  });
  const done = (url: string) => {
    if (!isRead(url)) return;
    inFlight -= 1;
    lastDone = Date.now();
  };
  page.on("requestfailed", (request) => done(request.url()));
  page.on("requestfinished", (request) => {
    if (request.url().includes("/api/atlas/parcel-tiles/")) tiles += 1;
    done(request.url());
  });
  return async () => {
    await expect(page.locator("canvas.maplibregl-canvas")).toBeVisible({
      timeout: 90_000,
    });
    await expect
      .poll(
        () => tiles > 0 && inFlight === 0 && Date.now() - lastDone >= QUIET_MS,
        { timeout: 120_000, intervals: [100] },
      )
      .toBe(true);
    return lastDone;
  };
}

function checkBudget(label: string, measured: number, budget: number) {
  console.log(`${label}: measured ${measured}, budget ${budget}`);
  expect
    .soft(measured, `${label}: measured ${measured}, budget ${budget}`)
    .toBeLessThanOrEqual(budget);
}

const total = (items: Transfer[]) =>
  items.reduce((sum, item) => sum + item.bytes, 0);

for (const [name, path] of [
  ["home", "/en"],
  ["directory", "/en/projects"],
  ["project", ""],
  ["market", "/en/market"],
  ["sources", "/en/sources"],
  ["explorer", EXPLORER],
] as const) {
  test(`JavaScript budget of the ${name} page`, async ({ page, request }) => {
    let target: string = path;
    if (name === "project") {
      const directory = await (await request.get("/en/projects")).text();
      const slug = /href="(\/en\/projects\/[^"?#]+)"/.exec(directory);
      expect(slug, "the package must list a project").not.toBeNull();
      target = slug?.[1] ?? "";
    }
    const finished = recordTransfers(page);
    const mapReads = trackAtlasReads(page);
    await page.goto(target);
    if (name === "explorer") await mapReads();
    const scripts = (await finished()).filter((item) => item.type === "script");
    const budget = budgets.pages[name];
    checkBudget(`${name} script bytes`, total(scripts), budget.scriptBytes);
    checkBudget(
      `${name} script requests`,
      scripts.length,
      budget.scriptRequests,
    );
  });
}

test("reads of the first map display stay within budget", async ({ page }) => {
  const finished = recordTransfers(page);
  const mapReads = trackAtlasReads(page);
  await page.goto(EXPLORER);
  await mapReads();
  const reads = (await finished()).filter((item) =>
    item.url.pathname.startsWith("/api/atlas/"),
  );
  for (const family of new Set(
    reads.map((item) => item.url.pathname.split("/")[3]),
  )) {
    const items = reads.filter(
      (item) => item.url.pathname.split("/")[3] === family,
    );
    console.log(
      `map family ${family}: ${items.length} requests, ${total(items)} bytes`,
    );
  }
  checkBudget("map load bytes", total(reads), budgets.mapLoad.bytes);
  checkBudget("map load requests", reads.length, budgets.mapLoad.requests);
});

test("the map settles within budget on a phone over 4G @mobile", async ({
  browser,
}, testInfo) => {
  test.setTimeout(300_000);
  const samples: number[] = [];
  for (let run = 0; run < TIME_SAMPLES; run += 1) {
    const context = await browser.newContext(testInfo.project.use);
    const page = await context.newPage();
    const cdp = await context.newCDPSession(page);
    await cdp.send("Network.enable");
    await cdp.send("Network.emulateNetworkConditions", FOUR_G);
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: CPU_SLOWDOWN });
    const mapReads = trackAtlasReads(page);
    const started = Date.now();
    await page.goto(EXPLORER, { waitUntil: "commit" });
    samples.push((await mapReads()) - started);
    await context.close();
  }
  samples.sort((a, b) => a - b);
  console.log(`map settled samples (ms): ${samples.join(", ")}`);
  checkBudget(
    "map settled ms (median)",
    samples[Math.floor(samples.length / 2)],
    budgets.mapSettledMs,
  );
});
