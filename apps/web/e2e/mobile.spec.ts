import { expect, test } from "@playwright/test";
import { expectNoHorizontalScroll, firstProject } from "./support";

// Runs in the `mobile` project (Pixel 7 viewport, touch) only.
test("@mobile home, directory and project page fit a phone screen", async ({
  page,
}) => {
  await page.goto("/en");
  await expect(page.locator("main").first()).toBeVisible();
  await expectNoHorizontalScroll(page);
  const { card, name } = await firstProject(page);
  await expectNoHorizontalScroll(page);
  await card.click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  await expectNoHorizontalScroll(page);
});

test("@mobile the explorer map loads on a phone", async ({ page }) => {
  await page.goto("/en/explore?territory=al-reem-island");
  await expect(page.locator("canvas.maplibregl-canvas")).toBeVisible();
  await expectNoHorizontalScroll(page);
});
