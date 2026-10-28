import { expect, test } from "@playwright/test";

test("clicking a parcel on the map opens its details", async ({ page }) => {
  const tiles = page.waitForResponse(
    (response) =>
      /\/api\/atlas\/parcel-tiles\//.test(response.url()) &&
      response.status() === 200,
  );
  await page.goto("/en/explore?territory=al-reem-island");
  const canvas = page.locator("canvas.maplibregl-canvas");
  await expect(canvas).toBeVisible();
  await tiles;
  // Let the first vector tiles render before probing the canvas.
  await page.waitForTimeout(1500);
  const box = await canvas.boundingBox();
  expect(box).not.toBeNull();
  if (!box) return;
  // Probe a grid from the centre outwards: water, roads and empty plots are not
  // parcels, so the first parcel hit is data dependent but must exist.
  const points: [number, number][] = [];
  for (const dy of [0, -0.12, 0.12, -0.24, 0.24])
    for (const dx of [0, -0.1, 0.1, -0.2, 0.2, -0.3, 0.3])
      points.push([
        box.x + box.width * (0.5 + dx),
        box.y + box.height * (0.5 + dy),
      ]);
  let selected = false;
  for (const [x, y] of points) {
    await page.mouse.click(x, y);
    try {
      await expect(page).toHaveURL(/[?&]parcel=/, { timeout: 1500 });
      selected = true;
      break;
    } catch {
      const close = page.getByRole("button", { name: "Close details" });
      if (await close.first().isVisible()) await close.first().click();
    }
  }
  expect(selected, "a parcel must be clickable near the map centre").toBe(true);
  const inspector = page.locator("section.parcel-inspector");
  await expect(inspector).toBeVisible();
  // The "Selected property" label is visually hidden; the card itself must load.
  await expect(inspector.getByRole("heading", { level: 2 })).toBeVisible();
  await expect(inspector.getByText("Parcel reference")).toBeVisible();
  await expect(inspector.getByText("Loading parcels…")).toHaveCount(0);
  await expect(
    inspector.getByText("These details could not be loaded."),
  ).toHaveCount(0);
  // The selection is addressable: reloading the URL restores the same parcel.
  const url = page.url();
  await page.reload();
  await expect(page).toHaveURL(url);
  await expect(page.locator("section.parcel-inspector")).toBeVisible();
});
