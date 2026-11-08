import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { claimable, parseTask, renderBoard, validate } from "./tasks.mjs";

const cli = fileURLToPath(new URL("./tasks.mjs", import.meta.url));

function taskText(
  id,
  status = "todo",
  dependencies = "",
  needsDecision = "no",
) {
  return `---
id: ${id}
phase: ${id[0]}
title: Title ${id}
status: ${status}
owner: unassigned
priority: 1
depends_on: [${dependencies}]
needs_owner_decision: ${needsDecision}
branch:
pr:
---
# ${id}
`;
}

test("parses a task and its list of dependencies", () => {
  const task = parseTask(taskText("A2", "todo", "A1, B3"));
  assert.equal(task.id, "A2");
  assert.deepEqual(task.depends_on, ["A1", "B3"]);
});

test("rewrites only the rows and keeps the text, in natural order", () => {
  const previous =
    "# Board\n\n| Tâche |\n| --- |\n| [A1](A1.md) | old |\n\nEnd\n";
  const rendered = renderBoard(previous, [
    parseTask(taskText("A10")),
    parseTask(taskText("A2")),
  ]);
  assert.match(rendered, /^# Board/);
  assert.match(rendered, /End\n$/);
  assert.ok(rendered.indexOf("[A2]") < rendered.indexOf("[A10]"));
  assert.ok(!rendered.includes("old"));
});

test("a task waiting on a dependency, a decision or a claim is not claimable", () => {
  const tasks = [
    parseTask(taskText("A1", "done")),
    parseTask(taskText("A2", "todo", "A1")),
    parseTask(taskText("A3", "todo", "A4")),
    parseTask(taskText("A4")),
    parseTask(taskText("A5", "todo", "", "yes")),
  ];
  assert.deepEqual(
    claimable(tasks).map((task) => task.id),
    ["A2", "A4"],
  );
  assert.deepEqual(
    claimable(tasks, new Set(["A2"])).map((task) => task.id),
    ["A4"],
  );
});

test("validation reports an unknown dependency and a bad status", () => {
  const entries = [
    { file: "A1.md", task: parseTask(taskText("A1", "started", "Z9")) },
  ];
  const problems = validate(entries);
  assert.ok(
    problems.some((problem) => problem.includes("unknown dependency Z9")),
  );
  assert.ok(problems.some((problem) => problem.includes("unknown status")));
});

function run(cwd, ...args) {
  execFileSync("git", args, { cwd, stdio: "pipe" });
}

test("two agents cannot claim the same task", () => {
  const root = mkdtempSync(path.join(tmpdir(), "tasks-claim-"));
  try {
    const bare = path.join(root, "origin.git");
    run(root, "init", "--quiet", "--bare", "-b", "main", bare);
    const first = path.join(root, "first");
    run(root, "clone", "--quiet", bare, first);
    run(first, "config", "user.name", "test");
    run(first, "config", "user.email", "test@example.invalid");
    run(first, "switch", "--quiet", "-c", "main");
    mkdirSync(path.join(first, "docs/tasks"), { recursive: true });
    writeFileSync(path.join(first, "docs/tasks/A1.md"), taskText("A1"));
    run(first, "add", ".");
    run(first, "commit", "--quiet", "-m", "tasks");
    run(first, "push", "--quiet", "origin", "main");
    const second = path.join(root, "second");
    run(root, "clone", "--quiet", bare, second);

    const claim = (cwd, agent) =>
      spawnSync(process.execPath, [cli, "claim", "A1", "--agent", agent], {
        cwd,
        encoding: "utf8",
      });
    assert.equal(claim(first, "claude").status, 0);
    const refused = claim(second, "codex");
    assert.equal(refused.status, 1);
    assert.match(refused.stderr, /claimed by claude/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
