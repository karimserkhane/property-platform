import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import test from "node:test";
import { localeDefinitions } from "../src/i18n/locales.ts";
import { getFontPreloads } from "../src/theme/fonts.ts";

const directory = new URL("../public/fonts/", import.meta.url);
const credits = JSON.parse(
  await readFile(new URL("credits.json", directory), "utf8"),
);

test("locale font profiles reference licensed local files with matching integrity", async () => {
  const files = (await readdir(directory)).filter((file) =>
    file.endsWith(".woff2"),
  );
  assert.deepEqual(
    files.sort(),
    credits.assets.map((asset) => asset.file).sort(),
  );
  const css = await readFile(new URL("fonts.css", directory), "utf8");
  for (const asset of credits.assets) {
    const bytes = await readFile(new URL(asset.file, directory));
    assert.equal(bytes.subarray(0, 4).toString(), "wOF2", asset.file);
    assert.equal(bytes.byteLength, asset.bytes, asset.file);
    assert.equal(
      createHash("sha256").update(bytes).digest("hex"),
      asset.sha256,
      asset.file,
    );
    assert.ok(css.includes(`/fonts/${asset.file}`), asset.file);
    const family = credits.families.find((item) => item.name === asset.family);
    assert.ok(family, asset.family);
    assert.ok(
      (await readFile(new URL(family.licenseFile, directory), "utf8")).includes(
        "SIL OPEN FONT LICENSE",
      ),
    );
  }
  for (const [locale, definition] of Object.entries(localeDefinitions)) {
    const preloads = getFontPreloads(definition.fontProfile);
    assert.equal(
      new Set(preloads.map((font) => font.href)).size,
      preloads.length,
      locale,
    );
    let bytes = 0;
    for (const font of preloads) {
      const asset = credits.assets.find(
        (item) => font.href === `/fonts/${item.file}`,
      );
      assert.ok(asset, `${locale}: ${font.href}`);
      bytes += asset.bytes;
    }
    assert.ok(bytes > 0 && bytes < 200000, `${locale}: preload budget`);
  }
});

test("Vietnamese labels and their uppercase headings are covered by both local font families", async () => {
  const messages = JSON.parse(
    await readFile(new URL("../messages/vi.json", import.meta.url), "utf8"),
  );
  const text = JSON.stringify(messages);
  const letters = new Set(
    [...`${text}${text.toLocaleUpperCase("vi")}`].filter((letter) =>
      /[\p{L}\p{M}]/u.test(letter),
    ),
  );
  const css = await readFile(new URL("fonts.css", directory), "utf8");
  const preloads = getFontPreloads(localeDefinitions.vi.fontProfile).map(
    (font) => font.href,
  );
  const faces = [...css.matchAll(/@font-face\s*\{([^}]+)\}/g)].map(
    ([, block]) => ({
      family: block.match(/font-family:\s*"([^"]+)"/)[1],
      href: block.match(/src:\s*url\("([^"]+)"\)/)[1],
      ranges: [...block.matchAll(/U\+([0-9A-F]+)(?:-([0-9A-F]+))?/g)].map(
        ([, first, last]) => [
          Number.parseInt(first, 16),
          Number.parseInt(last ?? first, 16),
        ],
      ),
    }),
  );
  for (const family of ["Manrope", "Cormorant Garamond"]) {
    const ranges = faces
      .filter((face) => face.family === family && preloads.includes(face.href))
      .flatMap((face) => face.ranges);
    for (const letter of letters) {
      const point = letter.codePointAt(0);
      assert.ok(
        ranges.some(([first, last]) => point >= first && point <= last),
        `${family}: ${letter} U+${point.toString(16)}`,
      );
    }
  }
});
