import { execFileSync } from "node:child_process";
import { access, readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const files = [
  ...new Set(
    execFileSync(
      "git",
      ["ls-files", "--cached", "--others", "--exclude-standard", "--", "*.md"],
      { encoding: "utf8" },
    )
      .trim()
      .split(/\r?\n/)
      .filter(Boolean),
  ),
];
const failures = [];

for (const file of files) {
  const contents = await readFile(file, "utf8");
  for (const match of contents.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
    const target = match[1].replace(/^<|>$/g, "").split("#")[0];
    if (
      !target ||
      /^[a-z][a-z\d+.-]*:/i.test(target) ||
      target.startsWith("/")
    ) {
      continue;
    }
    try {
      await access(resolve(dirname(file), decodeURIComponent(target)));
    } catch {
      failures.push(`${file}: ${target}`);
    }
  }
}

if (failures.length)
  throw new Error(`Broken local links:\n${failures.join("\n")}`);
console.log(`Checked local links in ${files.length} Markdown files.`);
