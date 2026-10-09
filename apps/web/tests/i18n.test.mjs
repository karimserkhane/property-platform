import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import test from "node:test";
import { createTranslator } from "next-intl";
import {
  defaultLocale,
  getDirection,
  isLocale,
  locales,
} from "../src/i18n/locales.ts";

const directory = new URL("../messages/", import.meta.url);
const readMessages = async (code) =>
  JSON.parse(await readFile(new URL(`${code}.json`, directory), "utf8"));

function flattenMessages(messages, prefix = "") {
  return Object.fromEntries(
    Object.entries(messages).flatMap(([key, value]) => {
      const path = prefix ? `${prefix}.${key}` : key;
      return typeof value === "string"
        ? [[path, value]]
        : Object.entries(flattenMessages(value, path));
    }),
  );
}

test("default language and directions cover the requested languages", () => {
  assert.equal(defaultLocale, "en");
  for (const code of ["en", "ar", "es", "de", "ru"]) assert.ok(isLocale(code));
  for (const code of ["ar", "ur", "fa"])
    assert.equal(getDirection(code), "rtl");
  for (const code of locales.filter(
    (code) => !["ar", "ur", "fa"].includes(code),
  )) {
    assert.equal(getDirection(code), "ltr");
  }
  for (const invalid of ["constructor", "__proto__", "../../secrets", "xx"]) {
    assert.equal(isLocale(invalid), false);
  }
});

test("every enabled locale has exactly one complete message dictionary", async () => {
  const files = (await readdir(directory)).filter((file) =>
    file.endsWith(".json"),
  );
  assert.deepEqual(files.sort(), locales.map((code) => `${code}.json`).sort());
  const reference = flattenMessages(await readMessages(defaultLocale));
  for (const code of locales) {
    const messages = await readMessages(code);
    const entries = flattenMessages(messages);
    assert.deepEqual(
      Object.keys(entries).sort(),
      Object.keys(reference).sort(),
      code,
    );
    const translate = createTranslator({
      locale: code,
      messages,
      onError: (error) => {
        throw error;
      },
    });
    for (const [key, text] of Object.entries(entries)) {
      assert.ok(text.trim().length > 0, `${code}:${key}`);
      assert.equal(translate(key), text, `${code}:${key}`);
      assert.equal(text.includes("�"), false, `${code}:${key}`);
    }
  }
});
