import assert from "node:assert/strict";
import test from "node:test";
import {
  availableDirectoryOffset,
  PROJECT_DIRECTORY_PAGE_SIZE,
  projectDirectoryHref,
} from "../src/features/projects/directory-navigation.ts";

test("area filters preserve the search and reset the directory page", () => {
  assert.deepEqual(
    projectDirectoryHref({
      territory: "saadiyat-island",
      query: "Louvre & sea",
    }),
    {
      pathname: "/projects",
      query: { territory: "saadiyat-island", q: "Louvre & sea" },
    },
  );
  assert.deepEqual(projectDirectoryHref({ query: "Louvre & sea" }), {
    pathname: "/projects",
    query: { q: "Louvre & sea" },
  });
});

test("directory pagination keeps area and search while clearing removes only search", () => {
  assert.deepEqual(
    projectDirectoryHref({
      territory: "al-reem-island",
      query: "District",
      offset: PROJECT_DIRECTORY_PAGE_SIZE,
    }),
    {
      pathname: "/projects",
      query: { territory: "al-reem-island", q: "District", offset: 48 },
    },
  );
  assert.deepEqual(
    projectDirectoryHref({ territory: "al-reem-island", query: "", offset: 0 }),
    { pathname: "/projects", query: { territory: "al-reem-island" } },
  );
});

test("a saved directory page recovers after results shrink without hiding a valid page", () => {
  assert.equal(availableDirectoryOffset(144, 174), 144);
  assert.equal(availableDirectoryOffset(144, 120), 96);
  assert.equal(availableDirectoryOffset(144, 48), 0);
  assert.equal(availableDirectoryOffset(48, 0), 0);
  assert.equal(availableDirectoryOffset(0, 174), 0);
  assert.equal(availableDirectoryOffset(48, 96), 48);
});
