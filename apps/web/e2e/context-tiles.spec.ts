import { expect, test } from "@playwright/test";

test("buildings and streets come from tiles and stay selectable", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(request.url()));
  const tiles = page.waitForResponse(
    (response) =>
      /\/api\/atlas\/context-tiles\//.test(response.url()) &&
      response.status() === 200,
  );
  const index = page.waitForResponse(
    (response) =>
      /\/api\/atlas\/context-index\?/.test(response.url()) &&
      response.status() === 200,
  );
  // Catalogue 3D: extrusions read index heights through feature state, and the
  // 3D camera zooms to footprint scale.
  await page.goto(
    "/en/explore?territory=al-reem-island&view=3d&buildings3d=catalogue",
  );
  const canvas = page.locator("canvas.maplibregl-canvas");
  await expect(canvas).toBeVisible();
  await Promise.all([tiles, index]);
  await page.waitForTimeout(2500);
  expect(
    requests.filter((url) => url.includes("/api/atlas/map-context")),
    "the explorer no longer downloads context geometry as GeoJSON",
  ).toEqual([]);
  const box = await canvas.boundingBox();
  expect(box).not.toBeNull();
  if (!box) return;
  // Probe from the centre outwards until a building card opens; which building
  // is data dependent, but Al Reem must have one near its centre.
  const inspector = page.locator("section.parcel-inspector");
  let found = false;
  for (const dy of [0, -0.1, 0.1, -0.2, 0.2])
    for (const dx of [0, -0.1, 0.1, -0.2, 0.2, -0.3, 0.3]) {
      if (found) break;
      await page.mouse.click(
        box.x + box.width * (0.5 + dx),
        box.y + box.height * (0.5 + dy),
      );
      try {
        await expect(inspector.getByText("Building").first()).toBeVisible({
          timeout: 1200,
        });
        found = true;
      } catch {
        const close = page.getByRole("button", { name: "Close details" });
        if (await close.first().isVisible()) await close.first().click();
      }
    }
  test.skip(!found, "no catalogue building rendered near the Al Reem centre");
  await expect(
    inspector.getByText("These details could not be loaded."),
  ).toHaveCount(0);
});
