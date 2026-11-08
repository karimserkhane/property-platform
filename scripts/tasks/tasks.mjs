// A41: the task files are the source of truth and BOARD.md is generated from them, so a pull
// request only touches its own task file. A claim is a ref, refs/heads/claims/<ID>: creating
// it is atomic on the Git server, so two agents cannot win the same task.
//
//   node scripts/tasks/tasks.mjs next [--limit N]
//   node scripts/tasks/tasks.mjs claim <ID> --agent <name> [--takeover]
//   node scripts/tasks/tasks.mjs release <ID>
//   node scripts/tasks/tasks.mjs claims
//   node scripts/tasks/tasks.mjs board [--write]
//   node scripts/tasks/tasks.mjs validate
//   node scripts/tasks/tasks.mjs prune-claims
import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const TASKS_DIR = "docs/tasks";
const BOARD_PATH = `${TASKS_DIR}/BOARD.md`;
const REQUIRED = [
  "id",
  "phase",
  "title",
  "status",
  "owner",
  "priority",
  "depends_on",
  "needs_owner_decision",
];
const STATUSES = new Set(["todo", "in-progress", "done"]);
const STALE_DAYS = 3; // AGENT_WORKFLOW.md section 2: a claim idle for 3 days can be taken over.
const CLAIM_REFS = "+refs/heads/claims/*:refs/remotes/origin/claims/*";
const TASK_FILE = /^[A-Z]\d+\.md$/;

export function parseTask(text) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) throw new Error("no front matter");
  const task = {};
  for (const line of match[1].split(/\r?\n/)) {
    const separator = line.indexOf(":");
    if (separator < 0) continue;
    const key = line.slice(0, separator).trim();
    const value = line.slice(separator + 1).trim();
    task[key] = /^\[.*\]$/.test(value)
      ? value
          .slice(1, -1)
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean)
      : value;
  }
  return task;
}

function sortKey(id) {
  return [id[0], Number(id.slice(1))];
}

export function compareIds(left, right) {
  const [leftPhase, leftNumber] = sortKey(left);
  const [rightPhase, rightNumber] = sortKey(right);
  return leftPhase.localeCompare(rightPhase) || leftNumber - rightNumber;
}

export function boardRow(task) {
  const decision =
    task.decision || (task.needs_owner_decision === "yes" ? "oui" : "non");
  const dependencies = task.depends_on.join(", ") || "—";
  return `| [${task.id}](${task.id}.md) | ${task.phase} | ${task.title} | ${task.priority} | ${dependencies} | ${decision} | ${task.status} | ${task.owner} |`;
}

// Keeps the text around the table; only the task rows are rewritten.
export function renderBoard(previous, tasks) {
  const lines = previous.split(/\r?\n/);
  const first = lines.findIndex((line) => line.startsWith("| ["));
  if (first < 0) throw new Error("no task row in BOARD.md");
  const kept = lines.filter((line) => !line.startsWith("| ["));
  const rows = [...tasks].sort((a, b) => compareIds(a.id, b.id)).map(boardRow);
  return [...kept.slice(0, first), ...rows, ...kept.slice(first)].join("\n");
}

export function claimable(tasks, claimed = new Set()) {
  const byId = new Map(tasks.map((task) => [task.id, task]));
  return tasks
    .filter(
      (task) =>
        task.status === "todo" &&
        task.needs_owner_decision !== "yes" &&
        !claimed.has(task.id) &&
        task.depends_on.every((id) => byId.get(id)?.status === "done"),
    )
    .sort(
      (a, b) =>
        Number(a.priority) - Number(b.priority) || compareIds(a.id, b.id),
    );
}

export function validate(entries) {
  const problems = [];
  const ids = new Map(entries.map(({ task }) => [task.id, task]));
  if (ids.size !== entries.length) problems.push("duplicate task id");
  for (const { file, task } of entries) {
    for (const field of REQUIRED) {
      if (task[field] === undefined || task[field] === "")
        problems.push(`${file}: missing ${field}`);
    }
    if (`${task.id}.md` !== file) problems.push(`${file}: id is ${task.id}`);
    if (!STATUSES.has(task.status))
      problems.push(`${file}: unknown status ${task.status}`);
    if (!/^\d+$/.test(task.priority ?? ""))
      problems.push(`${file}: priority is not a number`);
    if (!["yes", "no"].includes(task.needs_owner_decision)) {
      problems.push(`${file}: needs_owner_decision must be yes or no`);
    }
    if (!Array.isArray(task.depends_on)) {
      problems.push(`${file}: depends_on must be a list`);
      continue;
    }
    for (const dependency of task.depends_on) {
      if (!ids.has(dependency))
        problems.push(`${file}: unknown dependency ${dependency}`);
    }
  }
  return problems;
}

function git(args, options = {}) {
  return execFileSync("git", args, {
    encoding: "utf8",
    stdio: ["pipe", "pipe", "pipe"],
    ...options,
  }).trim();
}

function readWorkingTree() {
  return readdirSync(TASKS_DIR)
    .filter((file) => TASK_FILE.test(file))
    .map((file) => ({
      file,
      task: parseTask(readFileSync(`${TASKS_DIR}/${file}`, "utf8")),
    }));
}

function readRef(ref) {
  return git(["ls-tree", "--name-only", ref, `${TASKS_DIR}/`])
    .split("\n")
    .filter((path) => TASK_FILE.test(path.split("/").pop()))
    .map((path) => parseTask(git(["show", `${ref}:${path}`])));
}

function refreshClaims() {
  git(["fetch", "--quiet", "--prune", "origin", "main", CLAIM_REFS]);
}

function listClaims() {
  const output = git([
    "for-each-ref",
    "refs/remotes/origin/claims",
    "--format=%(refname:lstrip=4)|%(authorname)|%(committerdate:iso-strict)|%(objectname)",
  ]);
  return new Map(
    output
      .split("\n")
      .filter(Boolean)
      .map((line) => {
        const [id, agent, date, sha] = line.split("|");
        return [id, { id, agent, date, sha }];
      }),
  );
}

function ageInDays(date) {
  return (Date.now() - new Date(date).getTime()) / 86_400_000;
}

function option(args, name) {
  const index = args.indexOf(name);
  return index < 0 ? undefined : args[index + 1];
}

function fail(message) {
  console.error(message);
  process.exitCode = 1;
}

function next(args) {
  refreshClaims();
  const claims = listClaims();
  const limit = Number(option(args, "--limit") ?? 5);
  const tasks = claimable(readRef("origin/main"), new Set(claims.keys()));
  for (const task of tasks.slice(0, limit)) {
    console.log(`${task.id}\tpriority ${task.priority}\t${task.title}`);
  }
  console.log(`${tasks.length} claimable, ${claims.size} claimed.`);
}

function claim(args) {
  const [id] = args;
  const agent = option(args, "--agent");
  if (!id || !agent)
    return fail("usage: claim <ID> --agent <name> [--takeover]");
  refreshClaims();
  const existing = listClaims().get(id);
  const takeover = args.includes("--takeover");
  if (existing && !takeover)
    return fail(
      `${id} is already claimed by ${existing.agent} (${existing.date}).`,
    );
  if (existing && ageInDays(existing.date) < STALE_DAYS) {
    return fail(
      `${id}: the claim of ${existing.agent} is less than ${STALE_DAYS} days old.`,
    );
  }
  const tasks = readRef("origin/main");
  if (!existing && !claimable(tasks).some((task) => task.id === id)) {
    return fail(
      `${id} is not claimable: check its status, dependencies and owner decision.`,
    );
  }
  const commit = git([
    "-c",
    `user.name=${agent}`,
    "-c",
    `user.email=${agent}@agents.invalid`,
    "commit-tree",
    "origin/main^{tree}",
    "-p",
    "origin/main",
    "-m",
    `Claim ${id} by ${agent} at ${new Date().toISOString()}`,
  ]);
  const lease = existing
    ? [`--force-with-lease=refs/heads/claims/${id}:${existing.sha}`]
    : [];
  try {
    git([
      "push",
      "--quiet",
      ...lease,
      "origin",
      `${commit}:refs/heads/claims/${id}`,
    ]);
  } catch {
    return fail(`${id}: another agent claimed it first.`);
  }
  console.log(`${id} claimed by ${agent}.`);
}

function release(args) {
  const [id] = args;
  if (!id) return fail("usage: release <ID>");
  git(["push", "--quiet", "origin", "--delete", `claims/${id}`]);
  console.log(`${id} released.`);
}

function claims() {
  refreshClaims();
  for (const claim of listClaims().values()) {
    const age = ageInDays(claim.date);
    console.log(
      `${claim.id}\t${claim.agent}\t${claim.date}\t${age >= STALE_DAYS ? "stale" : "active"}`,
    );
  }
}

function pruneClaims() {
  refreshClaims();
  const done = new Set(
    readRef("origin/main")
      .filter((task) => task.status === "done")
      .map((task) => task.id),
  );
  for (const id of listClaims().keys()) {
    if (done.has(id)) {
      git(["push", "--quiet", "origin", "--delete", `claims/${id}`]);
      console.log(`${id}: claim removed, task done.`);
    }
  }
}

function board(args) {
  const previous = readFileSync(BOARD_PATH, "utf8");
  const rendered = renderBoard(
    previous,
    readWorkingTree().map(({ task }) => task),
  );
  if (args.includes("--write")) writeFileSync(BOARD_PATH, rendered);
  else process.stdout.write(rendered);
}

function validateCommand() {
  const problems = validate(readWorkingTree());
  for (const problem of problems) console.error(problem);
  if (problems.length) process.exitCode = 1;
  else console.log("Task files are valid.");
}

const COMMANDS = {
  next,
  claim,
  release,
  claims,
  board,
  validate: validateCommand,
  "prune-claims": pruneClaims,
};

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  const [command, ...args] = process.argv.slice(2);
  if (!COMMANDS[command])
    fail(`usage: tasks.mjs ${Object.keys(COMMANDS).join("|")}`);
  else COMMANDS[command](args);
}
