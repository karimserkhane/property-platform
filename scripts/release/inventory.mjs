// A42: compares every pinned component with what upstream has published, including what
// Dependabot cannot update. Read-only: it reports, and the changes go through pull requests.
//
//   node scripts/release/inventory.mjs [--host] [--output report.md]
//
// On a machine behind HTTPS inspection, add --use-system-ca before the script name.
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const COOLDOWN_DAYS = 7; // Same delay as .github/dependabot.yml.
const DAY = 86_400_000;

export function compareVersions(left, right) {
  const parts = (version) =>
    String(version)
      .match(/\d+(\.\d+)*/)[0]
      .split(".")
      .map(Number);
  const a = parts(left);
  const b = parts(right);
  for (let index = 0; index < Math.max(a.length, b.length); index += 1) {
    const difference = (a[index] ?? 0) - (b[index] ?? 0);
    if (difference) return difference;
  }
  return 0;
}

// "available" means public for long enough to be taken; "cooling" gives the first allowed day.
export function classify(pinned, latest, publishedAt, now = new Date()) {
  if (!latest) return { state: "unknown" };
  if (!pinned) return { state: "manual" };
  if (compareVersions(pinned, latest) >= 0) return { state: "current" };
  if (!publishedAt) return { state: "available" };
  const allowedAt = new Date(
    new Date(publishedAt).getTime() + COOLDOWN_DAYS * DAY,
  );
  return allowedAt <= now
    ? { state: "available" }
    : { state: "cooling", allowedAt: allowedAt.toISOString().slice(0, 10) };
}

async function getJson(url) {
  const headers = { "user-agent": "property-platform-release-cycle" };
  if (url.startsWith("https://api.github.com/") && process.env.GITHUB_TOKEN) {
    headers.authorization = `Bearer ${process.env.GITHUB_TOKEN}`;
  }
  const response = await fetch(url, {
    headers,
    signal: AbortSignal.timeout(30_000),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

// Highest plain release tag (v1.2.3 or 1.2.3) among the most recent tags of a Docker Hub image,
// for projects that publish their releases outside GitHub (Garage).
export function latestTag(tags) {
  const releases = tags.filter((tag) => /^v?\d+\.\d+\.\d+$/.test(tag.name));
  if (!releases.length) return undefined;
  const best = releases.reduce((a, b) =>
    compareVersions(a.name, b.name) >= 0 ? a : b,
  );
  return {
    version: best.name.replace(/^v/, ""),
    publishedAt: best.last_updated,
  };
}

async function latestFrom(source, pinned) {
  const [kind, id, mode] = source.split(":");
  if (kind === "node") {
    const major = `v${String(pinned).split(".")[0]}.`;
    const releases = await getJson("https://nodejs.org/dist/index.json");
    const release = releases.find((item) => item.version.startsWith(major));
    return {
      version: release.version.slice(1),
      publishedAt: release.date,
    };
  }
  if (kind === "npm") {
    const data = await getJson(`https://registry.npmjs.org/${id}`);
    const version = data["dist-tags"].latest;
    return { version, publishedAt: data.time[version] };
  }
  if (kind === "pypi") {
    const data = await getJson(`https://pypi.org/pypi/${id}/json`);
    const version = data.info.version;
    return {
      version,
      publishedAt: data.releases[version]?.[0]?.upload_time_iso_8601,
    };
  }
  if (kind === "github") {
    const data = await getJson(
      `https://api.github.com/repos/${id}/releases/latest`,
    );
    return {
      version: data.tag_name.replace(/^[^\d]*/, ""),
      publishedAt: data.published_at,
    };
  }
  if (kind === "dockerhub") {
    const data = await getJson(
      `https://hub.docker.com/v2/repositories/${id}/tags?page_size=100&ordering=last_updated`,
    );
    return latestTag(data.results);
  }
  if (kind === "endoflife") {
    const cycles = await getJson(`https://endoflife.date/api/${id}.json`);
    if (mode === "major") {
      return { version: cycles[0].cycle, publishedAt: cycles[0].releaseDate };
    }
    const prefix = String(pinned).split(".").slice(0, 2).join(".");
    const cycle = cycles.find((item) => item.cycle === prefix);
    return {
      version: cycle.latest,
      publishedAt: cycle.latestReleaseDate,
      endOfLife: cycle.eol,
    };
  }
  throw new Error(`unknown source ${source}`);
}

function readPinned(component) {
  if (!component.file) return undefined;
  const match = readFileSync(component.file, "utf8").match(
    new RegExp(component.pattern, "m"),
  );
  if (!match) throw new Error(`no version in ${component.file}`);
  return match[1];
}

function hostVersion(command, args, pattern) {
  try {
    return execFileSync(command, args, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).match(pattern)?.[1];
  } catch {
    return undefined;
  }
}

function hostComponents(pinnedNode) {
  return [
    {
      name: "Node.js du PC",
      installed: hostVersion("node", ["--version"], /v(\d+\.\d+\.\d+)/),
      expected: pinnedNode,
      source: "node",
      note: "Installateur officiel sur nodejs.org",
    },
    {
      name: "Git du PC",
      installed: hostVersion("git", ["--version"], /(\d+\.\d+\.\d+)/),
      source: "github:git-for-windows/git",
    },
    {
      name: "GitHub CLI du PC",
      installed: hostVersion("gh", ["--version"], /(\d+\.\d+\.\d+)/),
      source: "github:cli/cli",
    },
    {
      name: "Docker du PC",
      installed: hostVersion(
        "docker",
        ["version", "--format", "{{.Server.Platform.Name}}"],
        /(\d+\.\d+\.\d+)/,
      ),
      note: "Mise à jour depuis Docker Desktop",
    },
  ];
}

const LABELS = {
  current: "à jour",
  available: "disponible",
  cooling: "trop récente",
  manual: "à vérifier",
  unknown: "non vérifié",
};

function rowFor(item) {
  const status =
    item.state === "cooling"
      ? `${LABELS.cooling}, acceptable le ${item.allowedAt}`
      : LABELS[item.state];
  const date = item.publishedAt ? String(item.publishedAt).slice(0, 10) : "—";
  return `| ${item.name} | ${item.pinned ?? "empreinte"} | ${item.latest ?? "—"} | ${date} | ${status} | ${item.note ?? ""} |`;
}

function section(title, items) {
  if (!items.length) return [];
  return [
    `## ${title}`,
    "",
    "| Composant | Version en place | Dernière publiée | Publiée le | État | Note |",
    "| --- | --- | --- | --- | --- | --- |",
    ...items.map(rowFor),
    "",
  ];
}

async function inspect(base, pinned) {
  if (!base.source) return { ...base, pinned, state: "manual" };
  try {
    const latest = await latestFrom(base.source, base.expected ?? pinned);
    return {
      ...base,
      pinned,
      latest: latest.version,
      publishedAt: latest.publishedAt,
      ...classify(pinned, latest.version, latest.publishedAt),
    };
  } catch (error) {
    return {
      ...base,
      pinned,
      state: "unknown",
      note: `${base.note ?? ""} ${error.message}`.trim(),
    };
  }
}

export function renderReport(items, hosts, now = new Date()) {
  const needsWork = (item) => item.state === "available" && item.by === "hand";
  const byDependabot = (item) =>
    item.state === "available" && item.by === "dependabot";
  const rest = (item) => !needsWork(item) && !byDependabot(item);
  return [
    `# Cycle de mises à jour — ${now.toISOString().slice(0, 10)}`,
    "",
    "Rapport automatique ([RELEASE_CYCLE.md](docs/engineering/RELEASE_CYCLE.md)). Une version n'est acceptée que 7 jours après sa publication, sauf faille critique exploitée.",
    "",
    ...section("À mettre à jour à la main", items.filter(needsWork)),
    ...section("Pris en charge par Dependabot", items.filter(byDependabot)),
    ...section("Outils du PC", hosts),
    ...section("Le reste", items.filter(rest)),
  ].join("\n");
}

async function main(args) {
  const now = new Date();
  const components = JSON.parse(
    readFileSync("scripts/release/components.json", "utf8"),
  );
  const items = await Promise.all(
    components.map((component) => inspect(component, readPinned(component))),
  );
  const pinnedNode = items.find((item) => item.name === "Node.js")?.pinned;
  const hosts = args.includes("--host")
    ? await Promise.all(
        hostComponents(pinnedNode).map((host) => inspect(host, host.installed)),
      )
    : [];
  const report = renderReport(items, hosts, now);
  const index = args.indexOf("--output");
  if (index >= 0) writeFileSync(args[index + 1], report);
  else process.stdout.write(report);
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  await main(process.argv.slice(2));
}
