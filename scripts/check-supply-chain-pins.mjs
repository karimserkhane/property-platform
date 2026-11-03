// A38: every third-party action and image is pinned by an immutable digest, and one
// image tag resolves to the same digest everywhere (Dockerfiles, Compose files, CI).
// Dependabot updates Dockerfiles, Compose files and workflow actions separately; this
// check makes a partial bump fail until the other copies are aligned.
import { execFileSync } from "node:child_process";
import { appendFile, readFile } from "node:fs/promises";

const files = execFileSync(
  "git",
  [
    "ls-files",
    "--",
    "**/Dockerfile",
    "infra/local/compose*.yaml",
    ".github/workflows/*.yml",
  ],
  { encoding: "utf8" },
)
  .trim()
  .split(/\r?\n/)
  .filter(Boolean);

const failures = [];
const digestsByImage = new Map();

for (const file of files) {
  const lines = (await readFile(file, "utf8")).split(/\r?\n/);
  const stages = new Set();
  lines.forEach((line, index) => {
    const where = `${file}:${index + 1}`;
    const action = line.match(/^\s*-?\s*uses:\s*(\S+)/);
    if (action) {
      const reference = action[1];
      if (!reference.startsWith("./") && !/@[0-9a-f]{40}$/.test(reference)) {
        failures.push(
          `${where}: action ${reference} is not pinned by commit SHA`,
        );
      }
      return;
    }
    const from = line.match(/^\s*FROM\s+(\S+)(?:\s+AS\s+(\S+))?/i);
    const image = line.match(/^\s*image:\s*(\S+)/);
    const reference = from?.[1] ?? image?.[1];
    // Workflow expressions (the scan matrix) are checked through the values they expand to.
    if (!reference || reference.startsWith("${{")) return;
    const local =
      (from && stages.has(reference)) ||
      reference.startsWith("property-platform-");
    if (from?.[2]) stages.add(from[2]);
    // Earlier build stages and images built by this repository carry no registry digest.
    if (local) return;
    const [name, digest] = reference.split("@");
    if (!/^sha256:[0-9a-f]{64}$/.test(digest ?? "")) {
      failures.push(`${where}: image ${reference} is not pinned by digest`);
      return;
    }
    const seen = digestsByImage.get(name);
    if (seen && seen.digest !== digest) {
      failures.push(
        `${where}: ${name} is pinned to ${digest}, but ${seen.where} uses ${seen.digest}`,
      );
    } else if (!seen) {
      digestsByImage.set(name, { digest, where });
    }
  });
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log(
  `Checked supply-chain pins in ${files.length} files (${digestsByImage.size} images).`,
);

// CI scans exactly the pinned images, so a Dependabot bump is scanned in its own pull request.
if (process.argv.includes("--github-output")) {
  const images = [...digestsByImage]
    .map(([name, { digest }]) => `${name}@${digest}`)
    .sort();
  const targets = JSON.stringify(["lockfiles", ...images]);
  await appendFile(process.env.GITHUB_OUTPUT, `targets=${targets}\n`);
}
