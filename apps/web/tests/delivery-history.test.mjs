import assert from "node:assert/strict";
import test from "node:test";
import {
  deliveryChangeKey,
  deliveryOutcomeKey,
  developerHistoryHref,
  isDeveloperKey,
  readDeliveryHistoryData,
  splitDeliveryProjects,
} from "../src/features/projects/delivery.ts";

const history = {
  developer: { id: "1", key: "reportage-properties", name: "Reportage" },
  summary: { projects: 2 },
  projects: [
    { slug: "sensi", announcements: [{}], register_readings: [] },
    { slug: "quiet", announcements: [], register_readings: [] },
  ],
};

test("a developer page only reads a reviewed key from the local API", async () => {
  const paths = [];
  const read = async (path) => {
    paths.push(path);
    return { status: 200, data: history };
  };
  assert.deepEqual(
    await readDeliveryHistoryData("reportage-properties", read),
    {
      status: 200,
      history,
    },
  );
  assert.deepEqual(paths, ["developers/reportage-properties/delivery-history"]);
  for (const key of ["../secrets", "Bad_Key", "a".repeat(101), ""]) {
    assert.equal(isDeveloperKey(key), false, key);
    assert.equal((await readDeliveryHistoryData(key, read)).status, 404);
  }
  assert.equal(paths.length, 1);
  assert.equal(developerHistoryHref("aldar"), "/developers/aldar");
});

test("an unexpected or failed answer is unavailable, never partly rendered", async () => {
  const answer = (status, data) => async () => ({ status, data });
  assert.equal(
    (await readDeliveryHistoryData("reportage-properties", answer(404, null)))
      .status,
    404,
  );
  for (const data of [
    null,
    { ...history, developer: { ...history.developer, key: "other" } },
    { ...history, projects: [{ slug: "sensi", announcements: [] }] },
  ])
    assert.deepEqual(
      await readDeliveryHistoryData("reportage-properties", answer(200, data)),
      { status: 503, history: null },
    );
  const failing = async () => {
    throw new Error("offline");
  };
  assert.equal(
    (await readDeliveryHistoryData("reportage-properties", failing)).status,
    503,
  );
});

test("changes and outcomes map to labels and unknown codes render nothing", () => {
  assert.equal(deliveryChangeKey("later"), "changeLater");
  assert.equal(deliveryChangeKey("refined"), "changeRefined");
  assert.equal(deliveryOutcomeKey("late"), "outcomeLate");
  assert.equal(deliveryOutcomeKey("undetermined"), "outcomeUndetermined");
  assert.equal(deliveryChangeKey("constructor"), null);
  assert.equal(deliveryOutcomeKey("estimated"), null);
});

test("projects without dated observations are listed apart", () => {
  const { observed, silent } = splitDeliveryProjects(history.projects);
  assert.deepEqual(
    observed.map((row) => row.slug),
    ["sensi"],
  );
  assert.deepEqual(
    silent.map((row) => row.slug),
    ["quiet"],
  );
});
