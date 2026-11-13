// A43: updates Karim's private preview in one command, labels each version and can go back.
// Without --yes nothing changes: the plan is printed and the script stops.
//
//   node scripts/deploy/preview.mjs deploy [--yes] [--ingestion auto|yes|no] [--force]
//        [--wait-runs MINUTES] [--interrupt-runs] [--rebuild-base]
//   node scripts/deploy/preview.mjs rollback [--yes] [--to <tag>] [--wait-runs MINUTES] [--interrupt-runs]
//   node scripts/deploy/preview.mjs history
//
// Exit codes: 0 done (or plan printed), 1 failed or refused, 3 site updated but ingestion not
// recreated. Migrations are never undone: going back only swaps the images (RELEASE_CYCLE.md).
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  statfsSync,
  statSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { parseArgs } from "node:util";

const ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const HISTORY_PATH = ".cache/deploy/history.json";
const CA_PATH = ".cache/validation/ingestion-trusted-ca.crt";
const PREFECT_API = "http://127.0.0.1:4200/api";
const SITE_URL = "http://127.0.0.1:3102/fr";
const MIN_FREE_BYTES = 12 * 1024 ** 3;
const POLL_MS = 10_000;

const PREVIEW = [
  "-f",
  "infra/local/compose.yaml",
  "-f",
  "infra/local/compose.remote-preview.yaml",
  "--profile",
  "web-preview",
  "--profile",
  "remote-preview",
];
const TAILSCALE_STATUS = [
  "tailscale",
  "--socket=/tmp/tailscaled.sock",
  "status",
  "--json",
];

export const SERVICES = {
  api: {
    image: "property-platform-local-api",
    dockerfile: "apps/api/Dockerfile",
    container: "property-platform-local-api-1",
  },
  web: {
    image: "property-platform-web-preview",
    dockerfile: "apps/web/Dockerfile",
    container: "property-platform-local-web-1",
  },
  ingestion: {
    image: "property-platform-ingestion",
    dockerfile: "apps/ingestion/Dockerfile",
    container: "property-platform-local-ingestion-1",
  },
};

// The ingestion image also contains apps/api (apps/ingestion/Dockerfile).
const INGESTION_INPUTS =
  /^(apps\/ingestion\/|apps\/api\/|scripts\/acquire_reem_imagery\.py$|infra\/local\/compose\.ingestion\.yaml$)/;
const MIGRATION_FILE = /\/migrations\/\d+[^/]*\.py$/;
const COMPOSE_FILE = /^infra\/local\//;

export class DeployError extends Error {}

export function formatTag(date, suffix = "") {
  const pad = (value) => String(value).padStart(2, "0");
  const day = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  return `preview-${day}-${pad(date.getHours())}${pad(date.getMinutes())}${suffix}`;
}

export function needsIngestion(mode, changedFiles, hasPreviousTag) {
  if (mode === "yes") return true;
  if (mode === "no") return false;
  // Without a label, nobody knows which version is really running.
  return (
    !hasPreviousTag || changedFiles.some((file) => INGESTION_INPUTS.test(file))
  );
}

function lines(text) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function git(rt, ...args) {
  return rt.run("git", args).stdout.trim();
}

function compose(rt, files, ...args) {
  return rt.run("docker", ["compose", ...files, ...args], { stream: true });
}

function changedSince(rt, from, to) {
  return lines(git(rt, "diff", "--name-only", `${from}..${to}`));
}

function lastTag(rt) {
  const [name] = lines(
    git(rt, "tag", "--list", "preview-*", "--sort=-creatordate"),
  );
  return name ? { name, commit: git(rt, "rev-list", "-n", "1", name) } : null;
}

function dockerProblem(rt) {
  const { status } = rt.run("docker", ["version"], { allowFail: true });
  return status === 0
    ? null
    : "Docker ne répond pas : démarrer Docker Desktop.";
}

function preflight(rt) {
  const problems = [];
  if (git(rt, "rev-parse", "--abbrev-ref", "HEAD") !== "main") {
    problems.push(
      "Le dossier n'est pas sur main : lancer depuis le dossier principal.",
    );
  }
  const dirty = lines(git(rt, "status", "--porcelain")).length;
  if (dirty) {
    problems.push(
      `${dirty} fichier(s) modifié(s) dans ce dossier : rien n'est touché.`,
    );
  }
  git(rt, "fetch", "origin", "main", "--tags");
  const local = git(rt, "rev-parse", "HEAD");
  const remote = git(rt, "rev-parse", "origin/main");
  const ancestor = rt.run(
    "git",
    ["merge-base", "--is-ancestor", local, remote],
    {
      allowFail: true,
    },
  );
  if (ancestor.status !== 0) {
    problems.push(
      "main locale a divergé de origin/main : mise à jour impossible.",
    );
  }
  const free = rt.freeBytes();
  if (free < MIN_FREE_BYTES) {
    problems.push(
      `Disque : ${(free / 1024 ** 3).toFixed(1)} Go libres, il en faut au moins 12.`,
    );
  }
  const docker = dockerProblem(rt);
  if (docker) problems.push(docker);
  return { problems, local, remote };
}

function refuse(problems) {
  throw new DeployError(`Refusé :\n- ${problems.join("\n- ")}`);
}

function ingestionComposeFiles(rt) {
  const label = rt.run(
    "docker",
    [
      "inspect",
      SERVICES.ingestion.container,
      "--format",
      '{{index .Config.Labels "com.docker.compose.project.config_files"}}',
    ],
    { allowFail: true },
  );
  const files =
    label.status === 0 && label.stdout.trim()
      ? label.stdout.trim().split(",")
      : ["infra/local/compose.yaml", "infra/local/compose.ingestion.yaml"];
  return [...files.flatMap((file) => ["-f", file]), "--profile", "ingestion"];
}

async function activeRuns(rt) {
  try {
    const response = await rt.fetch(`${PREFECT_API}/flow_runs/filter`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        flow_runs: {
          state: { type: { any_: ["RUNNING", "PENDING", "CANCELLING"] } },
        },
        limit: 50,
      }),
    });
    if (!response.ok) return null;
    return (await response.json()).map((run) => run.name);
  } catch {
    return null;
  }
}

// Some flows fire every minute and last seconds: wait for one quiet instant, not for silence.
async function waitForQuietPrefect(rt, opts) {
  const deadline = rt.now() + opts.waitRuns * 60_000;
  for (;;) {
    const runs = await activeRuns(rt);
    if (runs && runs.length === 0) return { ready: true, interrupted: [] };
    if (opts.interruptRuns) {
      rt.log(
        runs
          ? `Courses interrompues par cette mise à jour : ${runs.join(", ")}`
          : "Prefect injoignable : l'ingestion est recréée sans savoir ce qui tourne.",
      );
      return { ready: true, interrupted: runs ?? [] };
    }
    if (rt.now() >= deadline) {
      return {
        ready: false,
        reason: runs
          ? `courses en cours : ${runs.join(", ")}`
          : "Prefect injoignable",
      };
    }
    await rt.sleep(POLL_MS);
  }
}

async function waitFor(rt, seconds, check) {
  const deadline = rt.now() + seconds * 1000;
  for (;;) {
    if (await check()) return true;
    if (rt.now() >= deadline) return false;
    await rt.sleep(POLL_MS);
  }
}

function isHealthy(rt, container) {
  const result = rt.run(
    "docker",
    ["inspect", container, "--format", "{{.State.Health.Status}}"],
    { allowFail: true },
  );
  return result.status === 0 && result.stdout.trim() === "healthy";
}

async function siteAsksForPassword(rt) {
  try {
    // Deliberately without credentials: the protected site must answer 401.
    return (await rt.fetch(SITE_URL, { redirect: "manual" })).status === 401;
  } catch {
    return false;
  }
}

function tailscaleRunning(rt) {
  const result = rt.run(
    "docker",
    [
      "compose",
      ...PREVIEW,
      "exec",
      "-T",
      "remote-preview",
      ...TAILSCALE_STATUS,
    ],
    { allowFail: true },
  );
  if (result.status !== 0) return false;
  try {
    return JSON.parse(result.stdout).BackendState === "Running";
  } catch {
    return false;
  }
}

async function verify(rt, ingestionRecreated) {
  const failures = [];
  if (!(await waitFor(rt, 180, () => isHealthy(rt, SERVICES.api.container)))) {
    failures.push("L'API n'est pas en bonne santé.");
  }
  if (!(await waitFor(rt, 90, () => siteAsksForPassword(rt)))) {
    failures.push("Le site ne répond pas 401 sans identifiants.");
  }
  if (!(await waitFor(rt, 180, () => tailscaleRunning(rt)))) {
    failures.push("Tailscale n'est pas à l'état Running.");
  }
  if (
    ingestionRecreated &&
    !(await waitFor(rt, 180, () => isHealthy(rt, SERVICES.ingestion.container)))
  ) {
    failures.push("L'ingestion n'est pas en bonne santé.");
  }
  if (failures.length) {
    throw new DeployError(
      `Vérifications en échec :\n- ${failures.join("\n- ")}`,
    );
  }
}

// The web container shares its network with remote-preview, which must always come after it.
async function rollOut(rt, { withIngestion, migrate, opts }) {
  const ingestionFiles = withIngestion ? ingestionComposeFiles(rt) : null;
  const recreate = ["up", "-d", "--no-build", "--no-deps", "--force-recreate"];
  compose(rt, PREVIEW, ...recreate, "api");
  if (migrate) {
    compose(
      rt,
      PREVIEW,
      "exec",
      "-T",
      "api",
      "python",
      "manage.py",
      "migrate",
      "--noinput",
    );
  }
  compose(rt, PREVIEW, ...recreate, "web");
  compose(rt, PREVIEW, ...recreate, "remote-preview");

  let ingestion = "non concernée";
  let recreated = false;
  if (withIngestion) {
    const quiet = await waitForQuietPrefect(rt, opts);
    if (quiet.ready) {
      compose(rt, ingestionFiles, ...recreate, "ingestion");
      recreated = true;
      ingestion = quiet.interrupted.length
        ? `recréée, courses interrompues : ${quiet.interrupted.join(", ")}`
        : "recréée";
    } else {
      ingestion = `pas recréée (${quiet.reason})`;
    }
  }
  await verify(rt, recreated);
  return { ingestion, partial: withIngestion && !recreated };
}

function applyGitTag(rt, tag, commit, note) {
  git(rt, "tag", "-a", tag, commit, "-m", note);
  const pushed = rt.run("git", ["push", "origin", tag], { allowFail: true });
  if (pushed.status !== 0) {
    rt.log(
      `Étiquette ${tag} créée ici, mais non envoyée : git push origin ${tag}`,
    );
  }
}

function versionNote(tag, fields, changes) {
  const details = Object.entries(fields).map(
    ([key, value]) => `${key} : ${value}`,
  );
  const list = changes.length
    ? changes.map((line) => `- ${line}`)
    : ["- aucun"];
  return [`Version ${tag}`, "", ...details, "", "Changements :", ...list].join(
    "\n",
  );
}

function saveRecord(rt, history, record) {
  rt.saveHistory([
    ...history.filter((item) => item.tag !== record.tag),
    record,
  ]);
}

function finish(rt, partial, tag) {
  rt.log(`Terminé : ${tag}.`);
  if (!partial) return 0;
  rt.log(
    "Ingestion non recréée. Une fois les courses finies : node scripts/deploy/preview.mjs deploy --yes --force --ingestion yes",
  );
  return 3;
}

export async function deploy(rt, opts) {
  const { problems, local, remote } = preflight(rt);
  if (problems.length) refuse(problems);

  const previous = lastTag(rt);
  if (previous?.commit === remote && !opts.force) {
    rt.log(`Rien de neuf : ${previous.name} est déjà cette version.`);
    return 0;
  }
  const base = previous?.commit ?? local;
  const changed = changedSince(rt, base, remote);
  const changes = lines(
    git(rt, "log", "--first-parent", "--format=%h %s", `${base}..${remote}`),
  );
  const migrations = changed.filter((file) => MIGRATION_FILE.test(file));
  const withIngestion = needsIngestion(
    opts.ingestion,
    changed,
    Boolean(previous),
  );
  const names = ["api", "web", ...(withIngestion ? ["ingestion"] : [])];
  const tag = formatTag(new Date(rt.now()));

  rt.log(`Version ${tag} : ${names.join(", ")}.`);
  rt.log(
    `Depuis ${previous?.name ?? `${base.slice(0, 7)} (aucune étiquette)`}, ${changes.length} changement(s), ${migrations.length} migration(s).`,
  );
  if (withIngestion) {
    const runs = await activeRuns(rt);
    rt.log(
      runs === null
        ? "Prefect injoignable : l'ingestion ne sera recréée qu'avec --interrupt-runs."
        : `Courses Prefect en cours : ${runs.length ? runs.join(", ") : "aucune"}.`,
    );
  }
  if (!opts.yes) {
    rt.log("Aperçu seulement : ajouter --yes pour déployer.");
    return 0;
  }

  const history = rt.loadHistory();
  const record = {
    tag,
    kind: "deploy",
    status: "started",
    commit: remote,
    previousCommit: base,
    kept: [],
    at: new Date(rt.now()).toISOString(),
  };
  try {
    git(rt, "pull", "--ff-only", "origin", "main");
    for (const name of names) {
      const { container, image } = SERVICES[name];
      const running = rt.run(
        "docker",
        ["inspect", container, "--format", "{{.Image}}"],
        { allowFail: true },
      );
      if (running.status !== 0) {
        rt.log(`${container} absent : pas d'image à conserver.`);
        continue;
      }
      rt.run("docker", [
        "image",
        "tag",
        running.stdout.trim(),
        `${image}:${tag}-before`,
      ]);
      record.kept.push(name);
    }
    saveRecord(rt, history, record);

    const secret = rt.hasCa()
      ? ["--secret", `id=platform_extra_ca,src=${CA_PATH}`]
      : [];
    const noCache = opts.rebuildBase ? ["--no-cache-filter", "base"] : [];
    for (const name of names) {
      const { image, dockerfile } = SERVICES[name];
      rt.run(
        "docker",
        [
          "build",
          ...secret,
          ...noCache,
          "-t",
          image,
          "-t",
          `${image}:${tag}`,
          "-f",
          dockerfile,
          ".",
        ],
        { stream: true },
      );
    }

    const { ingestion, partial } = await rollOut(rt, {
      withIngestion,
      migrate: true,
      opts,
    });
    record.status = "done";
    record.ingestion = ingestion;
    saveRecord(rt, history, record);
    applyGitTag(
      rt,
      tag,
      remote,
      versionNote(
        tag,
        {
          Commit: remote,
          Précédente: previous?.name ?? base,
          Services: names.join(", "),
          Ingestion: ingestion,
          Migrations: migrations.length ? migrations.join(", ") : "aucune",
        },
        changes,
      ),
    );
    return finish(rt, partial, tag);
  } catch (error) {
    record.status = "failed";
    record.error = error.message;
    saveRecord(rt, history, record);
    rt.log(`Échec du déploiement ${tag}.`);
    if (record.kept.length) {
      rt.log(
        "Pour revenir aux images d'avant : node scripts/deploy/preview.mjs rollback --yes",
      );
    }
    throw error;
  }
}

function rollbackSource(rt, opts, history) {
  if (opts.to) {
    return {
      imageTag: opts.to,
      commit: git(rt, "rev-list", "-n", "1", opts.to),
    };
  }
  const last = history
    .filter((item) => item.kind === "deploy" && item.kept.length)
    .at(-1);
  if (!last) {
    throw new DeployError(
      "Aucun déploiement dans l'historique de ce poste : préciser --to <étiquette>.",
    );
  }
  return { imageTag: `${last.tag}-before`, commit: last.previousCommit };
}

export async function rollback(rt, opts) {
  const problem = dockerProblem(rt);
  if (problem) refuse([problem]);
  const history = rt.loadHistory();
  const { imageTag, commit } = rollbackSource(rt, opts, history);
  const names = Object.keys(SERVICES).filter(
    (name) =>
      rt.run(
        "docker",
        ["image", "inspect", `${SERVICES[name].image}:${imageTag}`],
        {
          allowFail: true,
        },
      ).status === 0,
  );
  if (!names.includes("api") || !names.includes("web")) {
    throw new DeployError(
      `Images ${imageTag} introuvables pour l'API ou le site.`,
    );
  }

  const changed = changedSince(rt, commit, "HEAD");
  const migrations = changed.filter((file) => MIGRATION_FILE.test(file));
  const composeChanges = changed.filter((file) => COMPOSE_FILE.test(file));
  const tag = formatTag(new Date(rt.now()), "-rollback");
  rt.log(
    `Retour à ${imageTag} : ${names.join(", ")} (commit ${commit.slice(0, 7)}).`,
  );
  if (migrations.length) {
    rt.log(
      `Migrations conservées, jamais annulées (l'ancien code tourne sur le schéma récent) : ${migrations.join(", ")}`,
    );
  }
  if (composeChanges.length) {
    rt.log(
      `Fichiers Compose plus récents que cette version : ${composeChanges.join(", ")}`,
    );
  }
  if (!opts.yes) {
    rt.log("Aperçu seulement : ajouter --yes pour revenir en arrière.");
    return 0;
  }

  for (const name of names) {
    const { image } = SERVICES[name];
    rt.run("docker", [
      "image",
      "tag",
      `${image}:${imageTag}`,
      `${image}:latest`,
    ]);
  }
  const { ingestion, partial } = await rollOut(rt, {
    withIngestion: names.includes("ingestion"),
    migrate: false,
    opts,
  });
  saveRecord(rt, history, {
    tag,
    kind: "rollback",
    status: "done",
    commit,
    restored: imageTag,
    ingestion,
    kept: [],
    at: new Date(rt.now()).toISOString(),
  });
  applyGitTag(
    rt,
    tag,
    commit,
    versionNote(
      tag,
      {
        Commit: commit,
        "Images restaurées": imageTag,
        Services: names.join(", "),
        Ingestion: ingestion,
        "Migrations conservées": migrations.length
          ? migrations.join(", ")
          : "aucune",
      },
      [],
    ),
  );
  return finish(rt, partial, tag);
}

function realRuntime() {
  const historyFile = path.join(ROOT, HISTORY_PATH);
  return {
    run(command, args, { stream = false, allowFail = false } = {}) {
      const result = spawnSync(command, args, {
        cwd: ROOT,
        encoding: "utf8",
        maxBuffer: 64 * 1024 * 1024,
        stdio: stream ? "inherit" : ["ignore", "pipe", "pipe"],
      });
      const status = result.status ?? 1;
      if (status !== 0 && !allowFail) {
        throw new DeployError(
          `${command} ${args.slice(0, 3).join(" ")} a échoué (code ${status}). ${result.stderr ?? ""}`.trim(),
        );
      }
      return { status, stdout: result.stdout ?? "" };
    },
    fetch: (url, init) =>
      fetch(url, { ...init, signal: AbortSignal.timeout(10_000) }),
    now: () => Date.now(),
    sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
    log: (message) => console.log(message),
    freeBytes() {
      const stats = statfsSync(ROOT);
      return Number(stats.bavail) * Number(stats.bsize);
    },
    hasCa() {
      const file = path.join(ROOT, CA_PATH);
      return existsSync(file) && statSync(file).size > 0;
    },
    loadHistory: () =>
      existsSync(historyFile)
        ? JSON.parse(readFileSync(historyFile, "utf8"))
        : [],
    saveHistory(items) {
      mkdirSync(path.dirname(historyFile), { recursive: true });
      writeFileSync(historyFile, `${JSON.stringify(items, null, 2)}\n`);
    },
  };
}

function showHistory(rt) {
  const items = rt.loadHistory().slice(-10);
  if (!items.length) rt.log("Aucun déploiement sur ce poste.");
  for (const item of items) {
    rt.log(
      `${item.tag}\t${item.status}\t${item.commit.slice(0, 7)}\t${item.ingestion ?? ""}`,
    );
  }
  return 0;
}

export function parseCli(argv) {
  const { values, positionals } = parseArgs({
    args: argv,
    allowPositionals: true,
    options: {
      yes: { type: "boolean", default: false },
      force: { type: "boolean", default: false },
      ingestion: { type: "string", default: "auto" },
      "wait-runs": { type: "string", default: "30" },
      "interrupt-runs": { type: "boolean", default: false },
      "rebuild-base": { type: "boolean", default: false },
      to: { type: "string" },
    },
  });
  const waitRuns = Number(values["wait-runs"]);
  if (!["auto", "yes", "no"].includes(values.ingestion)) {
    throw new DeployError("--ingestion accepte auto, yes ou no.");
  }
  if (!Number.isFinite(waitRuns) || waitRuns < 0) {
    throw new DeployError("--wait-runs attend un nombre de minutes.");
  }
  return {
    command: positionals[0],
    yes: values.yes,
    force: values.force,
    ingestion: values.ingestion,
    waitRuns,
    interruptRuns: values["interrupt-runs"],
    rebuildBase: values["rebuild-base"],
    to: values.to,
  };
}

async function main() {
  const opts = parseCli(process.argv.slice(2));
  const rt = realRuntime();
  if (opts.command === "deploy") return deploy(rt, opts);
  if (opts.command === "rollback") return rollback(rt, opts);
  if (opts.command === "history") return showHistory(rt);
  throw new DeployError(
    "Commandes : deploy, rollback, history (voir AGENT_WORKFLOW.md, section 7).",
  );
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  main().then(
    (code) => {
      process.exitCode = code;
    },
    (error) => {
      if (!(error instanceof DeployError)) throw error;
      console.error(error.message);
      process.exitCode = 1;
    },
  );
}
