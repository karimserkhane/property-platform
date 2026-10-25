import { expect, type Page, test } from "@playwright/test";

// Journeys read the local stack only; they never submit data or use preview access.
export const projectCards = (page: Page, locale = "en") =>
  page.locator(`a[href^="/${locale}/projects/"]`);

// Locally a journey without its data is skipped with the reason. Against the
// demonstration package (E2E_REQUIRE_DATA=1, CI) missing data fails instead.
export function skipWithoutData(missing: boolean, reason: string) {
  if (process.env.E2E_REQUIRE_DATA === "1") {
    expect(missing, reason).toBe(false);
    return;
  }
  test.skip(missing, reason);
}

export async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflow, "page must not scroll horizontally").toBeLessThanOrEqual(1);
}

export async function firstProject(page: Page, locale = "en") {
  await page.goto(`/${locale}/projects`);
  const card = projectCards(page, locale).first();
  await expect(card, "the local directory must list projects").toBeVisible();
  return {
    card,
    name: (await card.locator("h2").innerText()).trim(),
    href: (await card.getAttribute("href")) ?? "",
  };
}
