import { expect, test } from "@playwright/test";
import {
  expectNoHorizontalScroll,
  firstProject,
  projectCards,
} from "./support";

test("directory search narrows the list and opens the matching project", async ({
  page,
}) => {
  const { name } = await firstProject(page);
  await page.getByLabel("Search projects").fill(name);
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page).toHaveURL(/[?&]q=/);
  const match = projectCards(page)
    .filter({ has: page.locator("h2", { hasText: name }) })
    .first();
  await expect(match).toBeVisible();
  await match.click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
});

test("an unknown search says so instead of showing unrelated projects", async ({
  page,
}) => {
  await page.goto("/en/projects?q=zz-no-such-project-zz");
  await expect(
    page.getByRole("heading", { name: "No matching projects" }),
  ).toBeVisible();
  await expect(projectCards(page)).toHaveCount(0);
});

test("a project page shows its facts with sources and links back", async ({
  page,
}) => {
  const { card, name } = await firstProject(page);
  await card.click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  await expect(
    page.getByRole("heading", { level: 2, name: "Overview" }),
  ).toBeVisible();
  const evidence = page.locator("[data-project-evidence]").first();
  if (await evidence.count()) {
    await evidence.locator("summary").click();
    await expect(evidence).toHaveAttribute("open", "");
  }
  await page
    .getByRole("navigation", { name: "Project navigation" })
    .first()
    .getByRole("link", { name: "Projects" })
    .click();
  await expect(page).toHaveURL(/\/en\/projects\?territory=/);
});

test("a reviewed component links to its programme and back", async ({
  page,
}) => {
  // Find a directory card that carries a reviewed parent, on any page.
  let child = null;
  for (let offset = 0; offset < 480 && !child; offset += 48) {
    await page.goto(`/en/projects?offset=${offset}`);
    const cards = projectCards(page);
    if (!(await cards.count())) break;
    const withParent = cards.filter({ hasText: /Part of ·/ });
    if (await withParent.count()) child = withParent.first();
  }
  test.skip(!child, "The local data has no reviewed project hierarchy");
  if (!child) return;
  const childName = (await child.locator("h2").innerText()).trim();
  await child.click();
  const parentLink = page
    .getByText("Part of", { exact: true })
    .locator("xpath=following-sibling::a[1]");
  await expect(parentLink).toBeVisible();
  const parentName = (await parentLink.innerText()).trim();
  await parentLink.click();
  await expect(
    page.getByRole("heading", { level: 1, name: parentName }),
  ).toBeVisible();
  const components = page.getByRole("region", { name: "Buildings & phases" });
  await expect(components.getByRole("link", { name: childName })).toBeVisible();
});

test("a project links to its developer's delivery history with cited points", async ({
  page,
}) => {
  const { card } = await firstProject(page);
  await card.click();
  const developer = (
    await page
      .getByText("Developer", { exact: true })
      .locator("xpath=following-sibling::bdi[1]")
      .innerText()
  ).trim();
  await page.getByRole("link", { name: "Developer delivery history" }).click();
  await expect(page).toHaveURL(/\/en\/developers\/[a-z0-9-]+$/);
  await expect(
    page.getByRole("heading", { level: 1, name: developer }),
  ).toBeVisible();
  const point = page.locator("[data-delivery-announcement]").first();
  if (await point.count()) {
    const proof = point.locator("[data-project-evidence]").first();
    await proof.locator("summary").click();
    await expect(proof).toHaveAttribute("open", "");
  }
  await expectNoHorizontalScroll(page);
});
