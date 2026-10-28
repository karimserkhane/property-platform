import assert from "node:assert/strict";
import test from "node:test";
import { pageWindow } from "../src/features/atlas/page-window.ts";

test("pagination handles empty lists, one page and stale page indices", () => {
  assert.deepEqual(pageWindow(0, 0).items, []);
  assert.deepEqual(pageWindow(0, 1).items, [0]);
  assert.equal(pageWindow(-20, 12).page, 0);
  assert.equal(pageWindow(20, 12).page, 11);
  for (const invalid of [NaN, Infinity, -Infinity, 1.5]) {
    assert.equal(pageWindow(invalid, 12).page, 0);
    assert.equal(pageWindow(0, invalid).pageCount, 0);
  }
});

test("large pagination stays bounded, ordered and navigable at every position", () => {
  for (const total of [2, 5, 6, 7, 10, 57, 1000, Number.MAX_SAFE_INTEGER]) {
    const positions = new Set([
      0,
      1,
      2,
      3,
      Math.floor(total / 2),
      total - 3,
      total - 2,
      total - 1,
    ]);
    for (const current of positions) {
      const result = pageWindow(current, total);
      const numbers = result.items.filter((item) => typeof item === "number");
      assert.ok(numbers.length <= 5);
      assert.equal(new Set(numbers).size, numbers.length);
      assert.deepEqual(
        numbers,
        [...numbers].sort((a, b) => a - b),
      );
      assert.equal(numbers[0], 0);
      assert.equal(numbers.at(-1), total - 1);
      assert.ok(numbers.includes(result.page));
      assert.ok(numbers.every((value) => value >= 0 && value < total));
      assert.equal(new Set(result.items).size, result.items.length);
      for (let index = 1; index < numbers.length; index++) {
        const previous = numbers[index - 1];
        const next = numbers[index];
        const between = result.items.slice(
          result.items.indexOf(previous) + 1,
          result.items.indexOf(next),
        );
        assert.equal(between.length, next - previous > 1 ? 1 : 0);
      }
    }
  }
});

test("nearby pages remain reachable around the middle and at either endpoint", () => {
  for (const current of [0, 1, 24, 48, 49]) {
    const { items } = pageWindow(current, 50);
    if (current > 0) assert.ok(items.includes(current - 1));
    if (current < 49) assert.ok(items.includes(current + 1));
  }
});
