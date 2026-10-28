import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

// Explicit source identity permits migration from any previous local project name.
// This is maintenance tooling, never a startup hook or a production migration.
const { values } = parseArgs({
  options: {
    "source-container": { type: "string" },
    "source-database": { type: "string" },
    "source-role": { type: "string" },
  },
});
for (const key of ["source-container", "source-database", "source-role"]) {
  assert.match(
    values[key] ?? "",
    /^[a-zA-Z0-9_.-]+$/,
    `Supply --${key} explicitly`,
  );
}
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const compose = [
  "compose",
  "-f",
  "infra/local/compose.yaml",
  "--profile",
  "web-preview",
];
function docker(args) {
  return execFileSync("docker", args, {
    cwd: root,
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  }).trim();
}
function sql(container, role, database, query) {
  return docker([
    "exec",
    container,
    "psql",
    "-X",
    "-v",
    "ON_ERROR_STOP=1",
    "-U",
    role,
    "-d",
    database,
    "-At",
    "-c",
    query,
  ]);
}
const quote = (name) => `"${name.replaceAll('"', '""')}"`;
const tableQuery =
  "SELECT schemaname, tablename FROM pg_tables WHERE schemaname IN ('public','real_estate','evidence') ORDER BY 1,2";
function snapshot(container, role, database) {
  const tables = sql(container, role, database, tableQuery)
    .split("\n")
    .filter(Boolean);
  return Object.fromEntries(
    tables.map((row) => {
      const [schema, table] = row.split("|");
      const key = `${schema}.${table}`;
      const value = sql(
        container,
        role,
        database,
        `SELECT count(*), md5(coalesce(string_agg(md5(to_jsonb(r)::text), '' ORDER BY md5(to_jsonb(r)::text)), '')) FROM ${quote(schema)}.${quote(table)} r`,
      );
      return [key, value];
    }),
  );
}
const configuration = JSON.parse(
  docker([...compose, "config", "--format", "json"]),
);
const sourceContainer = values["source-container"];
const sourceDatabase = values["source-database"];
const sourceRole = values["source-role"];
const source = JSON.parse(docker(["inspect", sourceContainer]))[0];
assert.equal(
  source.State.Running,
  true,
  "Source database must be running before maintenance",
);
const sourceProject = source.Config.Labels?.["com.docker.compose.project"];
assert.ok(sourceProject, "Source must be a Compose database container");
assert.equal(
  source.Config.Labels?.["com.docker.compose.service"],
  "db",
  "Source must be the database service",
);
assert.notEqual(
  sourceProject,
  configuration.name,
  "Source and target projects must differ; do not rerun after migration",
);
const existingTarget = docker([...compose, "ps", "--all", "--quiet"]);
assert.equal(
  existingTarget,
  "",
  "Target already exists; refusing to overwrite an existing environment",
);
const targetVolume = configuration.volumes["postgres18-data"].name;
const existingVolumes = docker(["volume", "ls", "--format", "{{.Name}}"]);
assert.ok(
  !existingVolumes.split("\n").includes(targetVolume),
  "Target volume already exists; refusing to overwrite it",
);
const sourceContainers = docker([
  "ps",
  "--filter",
  `label=com.docker.compose.project=${sourceProject}`,
  "--format",
  "{{.ID}}",
])
  .split("\n")
  .filter(Boolean);
const sourcePeers = sourceContainers.filter((id) => !source.Id.startsWith(id));
const targetRole = configuration.services.db.environment.POSTGRES_USER;
const targetDatabase = configuration.services.db.environment.POSTGRES_DB;
const stamp = new Date().toISOString().replaceAll(/[:.]/g, "-");
const backupDirectory = join(root, ".cache", "backups", `identity-${stamp}`);
mkdirSync(backupDirectory, { recursive: true });
let targetStarted = false;
try {
  if (sourcePeers.length) docker(["stop", ...sourcePeers]);
  const before = snapshot(sourceContainer, sourceRole, sourceDatabase);
  writeFileSync(
    join(backupDirectory, "before.json"),
    `${JSON.stringify(before, null, 2)}\n`,
  );
  const archivePath = "/tmp/property-platform-identity.dump";
  docker([
    "exec",
    sourceContainer,
    "pg_dump",
    "-Fc",
    "-U",
    sourceRole,
    "-d",
    sourceDatabase,
    "-f",
    archivePath,
  ]);
  const archive = join(backupDirectory, "database.dump");
  docker(["cp", `${sourceContainer}:${archivePath}`, archive]);
  const hash = createHash("sha256").update(readFileSync(archive)).digest("hex");
  writeFileSync(join(backupDirectory, "database.sha256"), `${hash}\n`);
  assert.deepEqual(
    snapshot(sourceContainer, sourceRole, sourceDatabase),
    before,
    "Source changed during backup; retry in a quiet maintenance window",
  );
  docker(["stop", sourceContainer]);
  targetStarted = true;
  docker([...compose, "up", "-d", "--wait", "--wait-timeout", "90", "db"]);
  const targetContainer = docker([...compose, "ps", "--quiet", "db"]);
  assert.ok(targetContainer, "Target database must be running");
  docker(["cp", archive, `${targetContainer}:${archivePath}`]);
  docker([
    "exec",
    targetContainer,
    "pg_restore",
    "--clean",
    "--if-exists",
    "--no-owner",
    "--no-privileges",
    "--exit-on-error",
    "--single-transaction",
    "-U",
    targetRole,
    "-d",
    targetDatabase,
    archivePath,
  ]);
  const after = snapshot(targetContainer, targetRole, targetDatabase);
  assert.deepEqual(
    after,
    before,
    "Restored content differs; keeping source for recovery",
  );
  writeFileSync(
    join(backupDirectory, "verified.json"),
    `${JSON.stringify({ targetDatabase, targetVolume, sha256: hash, tables: after }, null, 2)}\n`,
  );
  console.log(
    `Verified ${Object.keys(after).length} tables in ${targetDatabase}. Backup: ${backupDirectory}`,
  );
  console.log(
    "The source containers and source volume remain stopped and available for recovery.",
  );
  console.log(
    "Next: docker compose -f infra/local/compose.yaml --profile web-preview up -d --build web",
  );
} catch (error) {
  if (targetStarted) docker([...compose, "stop", "db"]);
  docker(["start", ...sourceContainers]);
  throw error;
}
