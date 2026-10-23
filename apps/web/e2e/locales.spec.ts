import { expect, test } from "@playwright/test";
import { expectNoHorizontalScroll, firstProject } from "./support";

for (const locale of ["ar", "fa", "ur"]) {
  test(`${locale} pages render right to left without horizontal scroll`, async ({
    page,
  }) => {
    await page.goto(`/${locale}`);
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expectNoHorizontalScroll(page);
    const { card } = await firstProject(page, locale);
    await card.click();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expectNoHorizontalScroll(page);
  });
}

test("left-to-right locales keep their direction", async ({ page }) => {
  for (const locale of ["en", "fr"]) {
    await page.goto(`/${locale}/projects`);
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  }
});
