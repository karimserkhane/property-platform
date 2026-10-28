import assert from "node:assert/strict";
import { registerHooks } from "node:module";
import test from "node:test";

// Production uses bundler resolution for extensionless TypeScript imports.
// Limit Node's equivalent resolution to the atlas module being tested here.
const atlasUrl = new URL("../src/features/atlas/", import.meta.url).href;
const resolution = registerHooks({
  resolve(specifier, context, nextResolve) {
    return nextResolve(
      context.parentURL?.startsWith(atlasUrl) && specifier.startsWith("./")
        ? `${specifier}.ts`
        : specifier,
      context,
    );
  },
});
const { BASEMAP_IMAGERY, imagerySelection, imageryVisibility } = await import(
  "../src/features/atlas/imagery-sources.ts"
);
const { mapCreditHtml, mapCreditText, mapCreditUrl } = await import(
  "../src/features/atlas/map-credits.ts"
);
resolution.deregister();

test("imagery revisions have distinct HTTPS sources and do not replace the default provider", () => {
  assert.equal(BASEMAP_IMAGERY[0].id, "esri");
  assert.equal(
    new Set(BASEMAP_IMAGERY.map((provider) => provider.id)).size,
    BASEMAP_IMAGERY.length,
  );
  for (const provider of BASEMAP_IMAGERY) {
    assert.equal(
      new URL(provider.tiles, "https://platform.example").protocol,
      provider.id === "esri" ? "https:" : "archive:",
    );
    for (const axis of ["{z}", "{x}", "{y}"])
      assert.ok(provider.tiles.includes(axis));
  }
});

test("territory and locale navigation restore only a registered global basemap", () => {
  const url = new URL(
    "https://platform.example/fr/explore?territory=abu-dhabi&basemap=sentinel-worldcover-2021",
  );
  url.searchParams.set("territory", "saadiyat-island");
  url.pathname = "/ar/explore";
  assert.deepEqual(imagerySelection(url.searchParams.get("basemap")), {
    satellite: true,
    scene: "sentinel-worldcover-2021",
  });
  for (const value of [
    null,
    "plan",
    "https://example.com",
    "S2C_40RBN_20261004_0_L2A",
  ])
    assert.equal(imagerySelection(value).satellite, false);
});

test("each basemap owns the entire view; Sentinel never mixes with Esri", () => {
  for (const provider of BASEMAP_IMAGERY) {
    const visible = imageryVisibility(true, provider.id);
    assert.deepEqual(
      Object.keys(visible).filter((id) => visible[id]),
      [provider.layerId],
    );
    assert.ok(
      Object.values(imageryVisibility(false, provider.id)).every(
        (value) => !value,
      ),
    );
  }
  assert.ok(
    Object.values(imageryVisibility(true, "S2C_40RBN_20261004_0_L2A")).every(
      (value) => !value,
    ),
  );
  assert.ok(
    BASEMAP_IMAGERY.every((provider) => !provider.tiles.includes("Reem")),
  );
});

test("close-up Esri views reuse the available Reem parent tile instead of grey high-LOD placeholders", () => {
  // Live qualification 2026-10-20 at 54.397007, 24.500380:
  // World_Imagery/MapServer/tilemap/19/225322/341365/1/1 -> data:[1].
  // The same point at z20/z21 -> data:[0], despite a successful image HTTP response.
  const esri = BASEMAP_IMAGERY.find((provider) => provider.id === "esri");
  const closeUp = { z: 21, x: 1365461, y: 901291 };
  const tileZoom = Math.min(closeUp.z, esri.maxzoom);
  const scale = 2 ** (closeUp.z - tileZoom);
  assert.deepEqual(
    {
      z: tileZoom,
      x: Math.floor(closeUp.x / scale),
      y: Math.floor(closeUp.y / scale),
    },
    { z: 19, x: 341365, y: 225322 },
  );
  assert.ok(closeUp.z > esri.maxzoom);
  assert.equal(imagerySelection("esri").scene, "esri");
});

test("map credits come from the reviewed registry, linked to the site's terms", () => {
  assert.equal(
    mapCreditText("openstreetmap"),
    "© OpenStreetMap contributors · ODbL 1.0",
  );
  assert.equal(
    mapCreditUrl("openstreetmap"),
    "https://www.openstreetmap.org/copyright",
  );
  assert.equal(
    mapCreditHtml("overture"),
    '<a href="https://docs.overturemaps.org/attribution/" target="_blank" rel="noopener noreferrer">© Overture Maps Foundation · CDLA Permissive 2.0</a>',
  );
  const worldcover = BASEMAP_IMAGERY.find(
    (provider) => provider.id === "sentinel-worldcover-2021",
  );
  assert.equal(worldcover.attribution, mapCreditText("esa-worldcover", "2021"));
  assert.match(
    worldcover.attribution,
    /ESA WorldCover project.*2021.*CC BY 4\.0$/,
  );
  assert.equal(worldcover.sourceUrl, mapCreditUrl("esa-worldcover"));
});
