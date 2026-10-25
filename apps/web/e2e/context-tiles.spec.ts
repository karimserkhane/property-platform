import { expect, test } from "@playwright/test";

test("buildings and streets come from tiles and the map stays selectable", async ({
  page,
}) => {
  // Software WebGL renders 3D slowly; each probe waits for a card.
  test.setTimeout(150_000);
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
  // A click near the centre selects a tiled building or street, or a place,
  // through its index row; the card must load. Which one is data dependent.
  const kicker = page.locator("section.parcel-inspector .property-kicker");
  let found = false;
  for (const dy of [-0.15, 0, 0.15])
    for (const dx of [-0.2, -0.1, 0, 0.1]) {
      if (found) break;
      await page.mouse.click(
        box.x + box.width * (0.5 + dx),
        box.y + box.height * (0.5 + dy),
      );
      try {
        await expect(kicker.first()).toBeVisible({ timeout: 1500 });
        found = true;
      } catch {
        await page.keyboard.press("Escape");
      }
    }
  expect(found, "a map object must be selectable near the centre").toBe(true);
  test.info().annotations.push({
    type: "selected",
    description: await kicker.first().innerText(),
  });
  await expect(
    page.getByText("These details could not be loaded."),
  ).toHaveCount(0);
});
