import { expect, test } from "@playwright/test";
import {
  expectNoHorizontalScroll,
  firstProject,
  projectCards,
  skipWithoutData,
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
    // Every citation states the reviewed licence of its source, or that it is unreviewed.
    await expect(
      evidence.locator("[data-project-evidence-rights]").first(),
    ).toContainText("Licence");
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
  skipWithoutData(
    !child,
    "The local data has no reviewed project hierarchy",
    "every reviewed relation cites a developer or listing page, which the public demonstration package does not hold (A18)",
  );
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
  // The hero and the verification sheet both link to the history.
  await page
    .getByRole("link", { name: "Developer delivery history" })
    .first()
    .click();
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

test("a registered project shows its verification sheet with cited checks", async ({
  page,
}) => {
  // Find a project the ADREC register describes, on the first directory pages.
  let found = false;
  for (let offset = 0; offset < 240 && !found; offset += 48) {
    await page.goto(`/en/projects?offset=${offset}`);
    const hrefs = await projectCards(page).evaluateAll((links) =>
      links.map((link) => link.getAttribute("href") ?? ""),
    );
    if (!hrefs.length) break;
    for (const href of hrefs) {
      await page.goto(href);
      if (await page.locator("[data-verification-reading]").count()) {
        found = true;
        break;
      }
    }
  }
  skipWithoutData(!found, "The local data has no ADREC register reading");
  const sheet = page.getByRole("region", { name: "Verification" });
  await expect(
    sheet.getByText("Registration number", { exact: true }),
  ).toBeVisible();
  await expect(sheet.getByText("Escrow bank", { exact: true })).toBeVisible();
  const proof = sheet.locator("[data-project-evidence]").first();
  await proof.locator("summary").click();
  await expect(proof).toHaveAttribute("open", "");
  await expect(
    sheet.getByRole("heading", { level: 3, name: "Check it yourself" }),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Project navigation" })
    .last()
    .getByRole("link", { name: "Verification" })
    .click();
  await expect(page).toHaveURL(/#project-verification$/);
  await expectNoHorizontalScroll(page);
  // The same sheet reads right to left in Arabic.
  await page.goto(page.url().replace("/en/", "/ar/").split("#")[0]);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("region", { name: "التحقق" })).toBeVisible();
  await expectNoHorizontalScroll(page);
});

test("the satellite signal states its method and limits, also right to left", async ({
  page,
}) => {
  const { href } = await firstProject(page);
  await page.goto(href);
  const signal = page.getByRole("region", {
    name: "Ground change seen by satellite",
  });
  await expect(signal).toBeVisible();
  // A measured parcel shows a level and two image dates, never a percentage.
  for (const parcel of await signal.locator("[data-activity-parcel]").all()) {
    await expect(parcel.getByText("Earlier image").first()).toBeVisible();
    await expect(parcel).not.toContainText("%");
  }
  const method = signal.locator("details").last();
  await method.locator("summary").click();
  await expect(method).toContainText("Copernicus");
  await expectNoHorizontalScroll(page);
  await page.goto(href.replace("/en/", "/ar/"));
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(
    page.getByRole("region", {
      name: "التغير على الأرض كما يُرى من القمر الصناعي",
    }),
  ).toBeVisible();
  await expectNoHorizontalScroll(page);
});

test("sources and licences list every reviewed site, also right to left", async ({
  page,
}) => {
  // The registry ships with the API, so this page needs no collected data.
  await page.goto("/en/sources");
  await expect(
    page.getByRole("heading", { level: 1, name: "Sources and licences" }),
  ).toBeVisible();
  const sites = page.locator("[data-source-site]");
  await expect(sites.first()).toBeVisible();
  await expect(sites.first().locator("[data-source-licence]")).not.toBeEmpty();
  await expectNoHorizontalScroll(page);
  await page.goto("/ar/sources");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(
    page.getByRole("heading", { level: 1, name: "المصادر والتراخيص" }),
  ).toBeVisible();
  await expectNoHorizontalScroll(page);
});
