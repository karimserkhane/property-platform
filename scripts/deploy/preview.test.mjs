import assert from "node:assert/strict";
import test from "node:test";
import {
  DeployError,
  deploy,
  formatTag,
  needsIngestion,
  parseCli,
  rollback,
} from "./preview.mjs";

const OPTS = {
  ingestion: "auto",
  waitRuns: 1,
  interruptRuns: false,
  force: false,
  yes: true,
};
const NEW = "b".repeat(40);
const OLD = "a".repeat(40);

// A runtime with no Docker and no Git: every command is recorded and answered from `state`.
function fakeRuntime(overrides = {}) {
  const state = {
    branch: "main",
    dirty: "",
    ancestor: 0,
    free: 40 * 1024 ** 3,
    tags: "preview-2026-11-01-1000",
    changed: "apps/web/page.tsx",
    runs: [[]],
    site: 401,
    tailscale: "Running",
    health: "healthy",
    missingImages: [],
    history: [],
    ...overrides,
  };
  const calls = [];
  const logs = [];
  let clock = Date.parse("2026-11-10T06:00:00Z");
  const rt = {
    run(command, args) {
      const line = `${command} ${args.join(" ")}`;
      calls.push(line);
      const ok = (stdout = "") => ({ status: 0, stdout });
      if (command === "git") {
        if (args[0] === "rev-parse") {
          if (args[1] === "--abbrev-ref") return ok(state.branch);
          return ok(args[1] === "HEAD" ? OLD : NEW);
        }
        if (args[0] === "status") return ok(state.dirty);
        if (args[0] === "merge-base")
          return { status: state.ancestor, stdout: "" };
        if (args[0] === "tag" && args[1] === "--list") return ok(state.tags);
        if (args[0] === "rev-list") return ok(OLD);
        if (args[0] === "diff") return ok(state.changed);
        if (args[0] === "log") return ok("abc1234 A change");
        return ok();
      }
      if (args[0] === "inspect") {
        if (args.includes("{{.State.Health.Status}}")) return ok(state.health);
        if (args.includes("{{.Image}}")) return ok("sha256:running");
        return ok(
          "C:/repo/infra/local/compose.yaml,C:/repo/infra/local/compose.ingestion.yaml",
        );
      }
      if (args[0] === "image" && args[1] === "inspect") {
        return {
          status: state.missingImages.some((name) => args[2].includes(name))
            ? 1
            : 0,
          stdout: "",
        };
      }
      if (args.includes("status") && args.includes("--json")) {
        return ok(JSON.stringify({ BackendState: state.tailscale }));
      }
      return ok();
    },
    async fetch(url) {
      if (url.includes("flow_runs")) {
        const runs = state.runs.length > 1 ? state.runs.shift() : state.runs[0];
        if (runs === null) throw new Error("unreachable");
        return { ok: true, json: async () => runs.map((name) => ({ name })) };
      }
      return { status: state.site };
    },
    now: () => clock,
    async sleep(ms) {
      clock += ms;
    },
    log: (message) => logs.push(message),
    freeBytes: () => state.free,
    hasCa: () => Boolean(state.ca),
    loadHistory: () => state.history,
    saveHistory(items) {
      state.history = items;
    },
  };
  return { rt, calls, logs, state };
}

const indexOf = (calls, fragment) =>
  calls.findIndex((call) => call.includes(fragment));
const has = (calls, fragment) => indexOf(calls, fragment) >= 0;

test("labels a version with its local date", () => {
  assert.equal(
    formatTag(new Date(2026, 10, 9, 7, 5)),
    "preview-2026-11-09-0705",
  );
  assert.equal(
    formatTag(new Date(2026, 0, 2, 13, 40), "-rollback"),
    "preview-2026-01-02-1340-rollback",
  );
});

test("rebuilds ingestion only when its image can have changed", () => {
  assert.equal(needsIngestion("auto", ["apps/web/a.ts"], true), false);
  assert.equal(needsIngestion("auto", ["apps/api/src/a.py"], true), true);
  assert.equal(
    needsIngestion("auto", ["infra/local/compose.ingestion.yaml"], true),
    true,
  );
  assert.equal(needsIngestion("auto", ["apps/web/a.ts"], false), true);
  assert.equal(needsIngestion("yes", [], true), true);
  assert.equal(needsIngestion("no", ["apps/ingestion/a.py"], true), false);
});

test("refuses a checkout that is not clean, current main or has no disk", async () => {
  for (const [overrides, message] of [
    [{ branch: "claude/x" }, /pas sur main/],
    [{ dirty: " M a.py\n?? b.py" }, /2 fichier/],
    [{ ancestor: 1 }, /divergé/],
    [{ free: 5 * 1024 ** 3 }, /5.0 Go/],
  ]) {
    const { rt, calls } = fakeRuntime(overrides);
    await assert.rejects(deploy(rt, OPTS), message);
    assert.equal(has(calls, "docker build"), false);
    assert.equal(has(calls, "pull"), false);
  }
});

test("without --yes only prints the plan", async () => {
  const { rt, calls, logs } = fakeRuntime();
  assert.equal(await deploy(rt, { ...OPTS, yes: false }), 0);
  for (const fragment of [
    "pull",
    "docker build",
    " up ",
    "image tag",
    "migrate",
    "tag -a",
  ]) {
    assert.equal(has(calls, fragment), false, fragment);
  }
  assert.ok(logs.some((line) => line.includes("Aperçu")));
});

test("stops when this version is already deployed, unless forced", async () => {
  const deployed = fakeRuntime();
  deployed.rt.run = (
    (run) => (command, args, options) =>
      command === "git" && args[0] === "rev-list"
        ? { status: 0, stdout: NEW }
        : run(command, args, options)
  )(deployed.rt.run);
  assert.equal(await deploy(deployed.rt, OPTS), 0);
  assert.equal(has(deployed.calls, "docker build"), false);
  assert.equal(await deploy(deployed.rt, { ...OPTS, force: true }), 0);
  assert.equal(has(deployed.calls, "docker build"), true);
});

test("deploys in the safe order and labels the version", async () => {
  const { rt, calls, state } = fakeRuntime();
  assert.equal(await deploy(rt, OPTS), 0);
  const order = [
    "pull --ff-only origin main",
    "image tag sha256:running property-platform-local-api:preview-",
    "docker build -t property-platform-local-api",
    "--force-recreate api",
    "manage.py migrate --noinput",
    "--force-recreate web",
    "--force-recreate remote-preview",
    "tag -a preview-",
    "push origin preview-",
  ];
  const positions = order.map((fragment) => indexOf(calls, fragment));
  assert.ok(
    positions.every((position) => position >= 0),
    positions.join(),
  );
  assert.deepEqual(
    positions,
    [...positions].sort((a, b) => a - b),
  );
  assert.equal(has(calls, "ingestion:"), false);
  assert.equal(has(calls, "--force-recreate ingestion"), false);
  const [record] = state.history;
  assert.equal(record.status, "done");
  assert.deepEqual(record.kept, ["api", "web"]);
  assert.equal(record.previousCommit, OLD);
});

test("passes the approved certificate only when the file exists", async () => {
  const withCa = fakeRuntime({ ca: true });
  await deploy(withCa.rt, OPTS);
  assert.equal(
    has(withCa.calls, "--secret id=platform_extra_ca,src=.cache/validation/"),
    true,
  );
  const without = fakeRuntime();
  await deploy(without.rt, OPTS);
  assert.equal(has(without.calls, "--secret"), false);
});

test("recreates ingestion with the compose files of the running container, once Prefect is quiet", async () => {
  const { rt, calls, logs } = fakeRuntime({
    changed: "apps/ingestion/flow.py",
    runs: [["long-import"], ["long-import"], []],
  });
  assert.equal(await deploy(rt, OPTS), 0);
  assert.equal(
    has(
      calls,
      "-f C:/repo/infra/local/compose.ingestion.yaml --profile ingestion up",
    ),
    true,
  );
  assert.ok(logs.some((line) => line.includes("long-import")));
  assert.ok(
    indexOf(calls, "--force-recreate remote-preview") <
      indexOf(calls, "--force-recreate ingestion"),
  );
});

test("leaves ingestion alone and says so when a long run outlasts the wait", async () => {
  const { rt, calls, logs, state } = fakeRuntime({
    changed: "apps/ingestion/flow.py",
    runs: [["long-import"]],
  });
  assert.equal(await deploy(rt, OPTS), 3);
  assert.equal(has(calls, "--force-recreate ingestion"), false);
  assert.match(state.history[0].ingestion, /pas recréée.*long-import/);
  assert.ok(logs.some((line) => line.includes("--force --ingestion yes")));
  assert.equal(has(calls, "tag -a preview-"), true);
});

test("announces what --interrupt-runs interrupts", async () => {
  const { rt, calls, logs, state } = fakeRuntime({
    changed: "apps/ingestion/flow.py",
    runs: [["long-import"]],
  });
  assert.equal(await deploy(rt, { ...OPTS, interruptRuns: true }), 0);
  assert.equal(has(calls, "--force-recreate ingestion"), true);
  assert.ok(
    logs.some(
      (line) => line.includes("interrompues") && line.includes("long-import"),
    ),
  );
  assert.match(state.history[0].ingestion, /interrompues : long-import/);
});

test("does not treat an unreachable Prefect as quiet", async () => {
  const { rt, calls } = fakeRuntime({
    changed: "apps/ingestion/flow.py",
    runs: [null],
  });
  assert.equal(await deploy(rt, OPTS), 3);
  assert.equal(has(calls, "--force-recreate ingestion"), false);
});

test("a failed check leaves no label and points to the rollback", async () => {
  const { rt, calls, logs, state } = fakeRuntime({ site: 200 });
  await assert.rejects(
    deploy(rt, OPTS),
    (error) => error instanceof DeployError && /401/.test(error.message),
  );
  assert.equal(has(calls, "tag -a preview-"), false);
  assert.equal(state.history[0].status, "failed");
  assert.ok(logs.some((line) => line.includes("rollback --yes")));
});

test("a Tailscale connector that does not come back fails the checks", async () => {
  const { rt } = fakeRuntime({ tailscale: "NoState" });
  await assert.rejects(deploy(rt, OPTS), /Tailscale/);
});

const DEPLOYED = {
  tag: "preview-2026-11-10-0900",
  kind: "deploy",
  status: "failed",
  commit: NEW,
  previousCommit: OLD,
  kept: ["api", "web"],
};

test("rollback restores the images kept before the last deployment, without migrating", async () => {
  const { rt, calls, logs, state } = fakeRuntime({
    history: [DEPLOYED],
    changed: "apps/api/src/x/migrations/0042_new.py\ninfra/local/compose.yaml",
    missingImages: ["property-platform-ingestion"],
  });
  assert.equal(await rollback(rt, OPTS), 0);
  assert.equal(
    has(
      calls,
      "image tag property-platform-web-preview:preview-2026-11-10-0900-before property-platform-web-preview:latest",
    ),
    true,
  );
  assert.equal(has(calls, "migrate"), false);
  assert.equal(has(calls, "--force-recreate ingestion"), false);
  assert.ok(
    indexOf(calls, "--force-recreate web") <
      indexOf(calls, "--force-recreate remote-preview"),
  );
  assert.ok(
    logs.some(
      (line) => line.includes("jamais annulées") && line.includes("0042_new"),
    ),
  );
  assert.ok(logs.some((line) => line.includes("Compose")));
  assert.equal(state.history.at(-1).kind, "rollback");
  assert.equal(has(calls, `tag -a preview-2026-11-10`), true);
  assert.equal(has(calls, `-rollback ${OLD}`), true);
});

test("rollback can target a label and previews without --yes", async () => {
  const { rt, calls } = fakeRuntime();
  assert.equal(
    await rollback(rt, { ...OPTS, yes: false, to: "preview-2026-11-01-1000" }),
    0,
  );
  assert.equal(
    has(
      calls,
      "image inspect property-platform-web-preview:preview-2026-11-01-1000",
    ),
    true,
  );
  assert.equal(has(calls, "image tag"), false);
  assert.equal(has(calls, " up "), false);
});

test("rollback refuses when it has nothing to restore", async () => {
  await assert.rejects(rollback(fakeRuntime().rt, OPTS), /--to/);
  await assert.rejects(
    rollback(fakeRuntime({ missingImages: ["web-preview"] }).rt, {
      ...OPTS,
      to: "preview-x",
    }),
    /introuvables/,
  );
});

test("reads the command line and refuses unknown values", () => {
  const parsed = parseCli([
    "deploy",
    "--yes",
    "--ingestion",
    "no",
    "--wait-runs",
    "5",
  ]);
  assert.equal(parsed.command, "deploy");
  assert.equal(parsed.yes, true);
  assert.equal(parsed.ingestion, "no");
  assert.equal(parsed.waitRuns, 5);
  assert.equal(parseCli(["rollback"]).yes, false);
  assert.throws(
    () => parseCli(["deploy", "--ingestion", "maybe"]),
    DeployError,
  );
  assert.throws(() => parseCli(["deploy", "--wait-runs", "soon"]), DeployError);
});
