import assert from "node:assert/strict";
import test from "node:test";
import { getHomeMotion } from "../src/features/atlas/home-motion.ts";

const geometry = {
  heroTop: 0,
  heroHeight: 800,
  chapterTop: 800,
  chapterHeight: 900,
  viewportHeight: 720,
  compact: false,
};

test("hero remains still at the start and travels more slowly than scrolling", () => {
  assert.equal(getHomeMotion(geometry).heroShift, 0);
  const halfway = getHomeMotion({ ...geometry, heroTop: -400 });
  assert.ok(halfway.heroShift > 0 && halfway.heroShift < 400);
  assert.ok(halfway.copyShift < halfway.heroShift);
  assert.ok(halfway.copyOpacity >= 0.45);
});

test("offscreen scenes clamp their travel and mobile uses less movement", () => {
  const desktop = getHomeMotion({
    ...geometry,
    heroTop: -10000,
    chapterTop: -10000,
  });
  const mobile = getHomeMotion({
    ...geometry,
    heroTop: -10000,
    chapterTop: -10000,
    compact: true,
  });
  assert.equal(desktop.heroShift, 150);
  assert.equal(desktop.chapterShift, 60);
  assert.ok(mobile.heroShift < desktop.heroShift);
  assert.ok(mobile.chapterShift < desktop.chapterShift);
  assert.equal(
    getHomeMotion({ ...geometry, chapterTop: 10000 }).chapterShift,
    -60,
  );
});

test("chapter centers naturally and a collapsed viewport has finite results", () => {
  assert.equal(getHomeMotion({ ...geometry, chapterTop: -90 }).chapterShift, 0);
  const collapsed = getHomeMotion({
    ...geometry,
    heroHeight: 0,
    chapterHeight: 0,
    viewportHeight: 0,
  });
  assert.ok(Object.values(collapsed).every(Number.isFinite));
});
