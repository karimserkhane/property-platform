import assert from "node:assert/strict";
import test from "node:test";
import {
  publicationLabelKey,
  readSourceSitesData,
  sortSourceSites,
} from "../src/features/sources/data.ts";

const site = Object.freeze({
  host: "openstreetmap.org",
  publisher: "OpenStreetMap Foundation",
  licence: "ODbL-1.0",
  licence_url: "https://opendatacommons.org/licenses/odbl/1-0/",
  terms_url: "https://osmfoundation.org/wiki/Terms_of_Use",
  collection: "allowed",
  publication: "open",
  attribution: "© OpenStreetMap contributors",
  reviewed_on: "2026-10-27",
});

test("the source rights registry is read from the preview API and checked", async () => {
  const paths = [];
  const ok = await readSourceSitesData(async (path) => {
    paths.push(path);
    return { status: 200, data: { items: [site] } };
  });
  assert.deepEqual(paths, ["source-rights"]);
  assert.deepEqual(ok, { status: 200, sites: [site] });
  for (const data of [
    null,
    {},
    { items: [{ ...site, publication: "everything" }] },
    { items: [{ ...site, collection: undefined }] },
    { items: [{ ...site, host: 1 }] },
  ])
    assert.deepEqual(
      await readSourceSitesData(async () => ({ status: 200, data })),
      { status: 503, sites: null },
    );
  assert.deepEqual(
    await readSourceSitesData(async () => ({ status: 403, data: null })),
    { status: 403, sites: null },
  );
  assert.deepEqual(
    await readSourceSitesData(async () => {
      throw new Error("offline");
    }),
    { status: 503, sites: null },
  );
});

test("reviewed sites come first, then by publisher, and every level has a label", () => {
  const unreviewed = {
    ...site,
    host: "aiph.org",
    publisher: "AIPH",
    licence: "unknown",
    reviewed_on: null,
  };
  const later = { ...site, host: "zeta.example", publisher: "Zeta" };
  const earlier = { ...site, host: "adrec.gov.ae", publisher: "ADREC" };
  assert.deepEqual(
    sortSourceSites([unreviewed, later, earlier], "en").map((row) => row.host),
    ["adrec.gov.ae", "zeta.example", "aiph.org"],
  );
  assert.deepEqual(["open", "facts", "link", "none"].map(publicationLabelKey), [
    "publicationOpen",
    "publicationFacts",
    "publicationLink",
    "publicationNone",
  ]);
});
