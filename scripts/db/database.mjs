// A45: separate PostgreSQL roles and one scratch database per agent, on the local PostGIS server.
// Without --yes nothing changes: the plan is printed and the script stops.
//
//   node scripts/db/database.mjs roles [--yes]
//   node scripts/db/database.mjs scratch list
//   node scripts/db/database.mjs scratch create <agent> [--name <suffix>] [--yes]
//   node scripts/db/database.mjs scratch drop <agent> [--name <suffix>] [--yes]
//   node scripts/db/database.mjs psql --as readonly|scratch [--db <name>] [-- <psql arguments>]
//
// Common options: --container (default property-platform-local-db-1), --superuser
// (default property_platform), --min-free-gb (default 12, for scratch create), --secrets (default .cache/db/roles.local.json in the main checkout).
// Passwords are generated once, kept in the git-ignored secrets file and passed to psql through
// the environment: never on a command line, never printed (DATABASE_ROLES.md).

import { spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import {
  chmodSync,
  existsSync,
  mkdirSync,
  readFileSync,
  statfsSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { parseArgs } from "node:util";

const ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const SECRETS_PATH = ".cache/db/roles.local.json";
export const MIN_FREE_BYTES = 12 * 1024 ** 3;
export const SHARED_DATABASE = "property_platform";
export const TEMPLATE_DATABASE = "template_postgis";

export const ROLES = {
  readonly: {
    name: "pp_agent_readonly",
    env: "PP_READONLY_PASSWORD",
    purpose: "agents : lecture seule de la base partagée",
  },
  scratch: {
    name: "pp_agent_scratch",
    env: "PP_SCRATCH_PASSWORD",
    purpose:
      "agents : propriétaire des bases d'essai, aucun accès à la base partagée",
  },
  app: {
    name: "pp_app",
    env: "PP_APP_PASSWORD",
    purpose:
      "API et ingestion : sans super-utilisateur (adoption après essai à part)",
  },
};

const AGENT = /^[a-z][a-z0-9]{1,19}$/;
const SUFFIX = /^[a-z0-9]{1,20}$/;
const SCRATCH = /^scratch_[a-z][a-z0-9]{1,19}(_[a-z0-9]{1,20})?$/;

export class DatabaseError extends Error {}

export function scratchName(agent, suffix) {
  if (!AGENT.test(agent ?? "")) {
    throw new DatabaseError(
      `Nom d'agent invalide : ${JSON.stringify(agent)} (minuscules et chiffres, 2 à 20 caractères, par exemple claude ou codex).`,
    );
  }
  if (suffix !== undefined && !SUFFIX.test(suffix)) {
    throw new DatabaseError(
      `Suffixe invalide : ${JSON.stringify(suffix)} (minuscules et chiffres, 1 à 20 caractères).`,
    );
  }
  return suffix ? `scratch_${agent}_${suffix}` : `scratch_${agent}`;
}

export function isScratchName(name) {
  return SCRATCH.test(name);
}

// Idempotent: every run converges to the same attributes and grants, whatever existed before.
// Runs as the bootstrap superuser through the container's local socket; the passwords come
// from the environment with \getenv, so they never appear in the SQL text or a process list.
export function rolesSql() {
  const { readonly, scratch, app } = ROLES;
  const all = [readonly.name, scratch.name, app.name];
  return `\\set ON_ERROR_STOP on
\\getenv readonly_password ${readonly.env}
\\getenv scratch_password ${scratch.env}
\\getenv app_password ${app.env}
SELECT format('CREATE ROLE %I', r) FROM unnest(ARRAY[${all.map((r) => `'${r}'`).join(", ")}]) AS r
  WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) \\gexec
ALTER ROLE ${readonly.name} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS INHERIT CONNECTION LIMIT 10 PASSWORD :'readonly_password';
ALTER ROLE ${readonly.name} SET default_transaction_read_only = on;
ALTER ROLE ${readonly.name} SET statement_timeout = '120s';
ALTER ROLE ${readonly.name} SET idle_in_transaction_session_timeout = '300s';
GRANT pg_read_all_data TO ${readonly.name};
ALTER ROLE ${scratch.name} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 10 PASSWORD :'scratch_password';
ALTER ROLE ${app.name} WITH LOGIN NOSUPERUSER CREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'app_password';
REVOKE CONNECT, TEMPORARY ON DATABASE ${SHARED_DATABASE} FROM PUBLIC;
GRANT CONNECT ON DATABASE ${SHARED_DATABASE} TO ${readonly.name}, ${app.name};
REVOKE ALL ON DATABASE ${SHARED_DATABASE} FROM ${scratch.name};
SELECT r.rolname, r.rolsuper, r.rolcreatedb, r.rolcanlogin,
       pg_has_role(r.rolname, 'pg_read_all_data', 'MEMBER') AS reads_all,
       has_database_privilege(r.rolname, '${SHARED_DATABASE}', 'CONNECT') AS connects_shared
  FROM pg_roles r WHERE r.rolname IN (${all.map((r) => `'${r}'`).join(", ")}) ORDER BY 1;
`;
}

export function createScratchSql(name) {
  if (!isScratchName(name)) throw new DatabaseError(`Refusé : ${name}`);
  return `\\set ON_ERROR_STOP on
CREATE DATABASE ${name} TEMPLATE ${TEMPLATE_DATABASE} OWNER ${ROLES.scratch.name};
REVOKE ALL ON DATABASE ${name} FROM PUBLIC;
GRANT ALL ON DATABASE ${name} TO ${ROLES.scratch.name};
GRANT CONNECT ON DATABASE ${name} TO ${ROLES.readonly.name};
`;
}

export function dropScratchSql(name) {
  if (!isScratchName(name)) throw new DatabaseError(`Refusé : ${name}`);
  return `\\set ON_ERROR_STOP on
DROP DATABASE IF EXISTS ${name} WITH (FORCE);
`;
}

const LIST_SQL = `SELECT datname, pg_size_pretty(pg_database_size(datname)), pg_get_userbyid(datdba)
  FROM pg_database WHERE datname LIKE 'scratch\\_%' ORDER BY 1;`;

export function generatePassword() {
  return randomBytes(24).toString("base64url");
}

// Missing passwords are generated; existing ones are kept so other worktrees keep working.
export function completeSecrets(secrets, generate = generatePassword) {
  const result = { ...secrets };
  let changed = false;
  for (const role of Object.values(ROLES)) {
    if (
      typeof result[role.name] !== "string" ||
      result[role.name].length < 16
    ) {
      result[role.name] = generate();
      changed = true;
    }
  }
  return { secrets: result, changed };
}

function env(secrets) {
  return Object.fromEntries(
    Object.values(ROLES).map((role) => [role.env, secrets[role.name]]),
  );
}

export function checkFreeSpace(hostFree, serverFree, minimum = MIN_FREE_BYTES) {
  const problems = [];
  if (hostFree < minimum) {
    problems.push(`disque du PC : ${gb(hostFree)} Go libres`);
  }
  if (serverFree !== null && serverFree < minimum) {
    problems.push(`disque du serveur PostgreSQL : ${gb(serverFree)} Go libres`);
  }
  if (problems.length) {
    throw new DatabaseError(
      `Place insuffisante (minimum ${gb(minimum)} Go) : ${problems.join(", ")}. Rien n'est créé.`,
    );
  }
}

function gb(bytes) {
  return (bytes / 1024 ** 3).toFixed(1);
}

export async function roles(rt, opts) {
  const loaded = rt.loadSecrets();
  const { secrets, changed } = completeSecrets(loaded);
  rt.log(
    `Serveur : ${opts.container}. Rôles appliqués (procédure rejouable) :`,
  );
  for (const role of Object.values(ROLES)) {
    rt.log(`- ${role.name} : ${role.purpose}`);
  }
  rt.log(
    `- ${SHARED_DATABASE} : connexion retirée à PUBLIC, accordée à ${ROLES.readonly.name} et ${ROLES.app.name}.`,
  );
  if (changed)
    rt.log(`Mots de passe manquants générés dans ${rt.secretsPath}.`);
  if (!opts.yes) {
    rt.log("Plan seulement : relancer avec --yes pour appliquer.");
    return 0;
  }
  if (changed) rt.saveSecrets(secrets);
  rt.superuserSql(rolesSql(), env(secrets), SHARED_DATABASE);
  rt.log("Rôles à jour.");
  return 0;
}

export async function scratch(rt, opts) {
  if (opts.action === "list") {
    rt.superuserSql(LIST_SQL, {}, "postgres");
    return 0;
  }
  const name = scratchName(opts.agent, opts.name);
  if (opts.action === "create") {
    checkFreeSpace(
      rt.hostFreeBytes(),
      rt.serverFreeBytes(),
      (opts.minFreeGb ?? MIN_FREE_BYTES / 1024 ** 3) * 1024 ** 3,
    );
    if (rt.databaseExists(name)) {
      rt.log(`${name} existe déjà : rien à faire.`);
      return 0;
    }
    if (!rt.roleExists(ROLES.scratch.name)) {
      throw new DatabaseError(
        `Le rôle ${ROLES.scratch.name} n'existe pas : lancer d'abord « roles --yes ».`,
      );
    }
    rt.log(
      `Création de ${name} depuis ${TEMPLATE_DATABASE}, propriétaire ${ROLES.scratch.name}.`,
    );
    if (!opts.yes) {
      rt.log("Plan seulement : relancer avec --yes pour créer.");
      return 0;
    }
    rt.superuserSql(createScratchSql(name), {}, "postgres");
    rt.log(`${name} créée. Connexion : psql --as scratch --db ${name}.`);
    return 0;
  }
  if (opts.action === "drop") {
    if (!rt.databaseExists(name)) {
      rt.log(`${name} n'existe pas : rien à faire.`);
      return 0;
    }
    rt.log(`Suppression de ${name} (connexions ouvertes fermées).`);
    if (!opts.yes) {
      rt.log("Plan seulement : relancer avec --yes pour supprimer.");
      return 0;
    }
    rt.superuserSql(dropScratchSql(name), {}, "postgres");
    rt.log(`${name} supprimée.`);
    return 0;
  }
  throw new DatabaseError("Actions : list, create, drop.");
}

export async function psql(rt, opts) {
  const role = ROLES[opts.as];
  if (!role || opts.as === "app") {
    throw new DatabaseError("--as readonly ou --as scratch.");
  }
  const database =
    opts.db ?? (opts.as === "readonly" ? SHARED_DATABASE : undefined);
  if (!database)
    throw new DatabaseError(
      "--db scratch_<agent> est requis avec --as scratch.",
    );
  if (opts.as === "scratch" && !isScratchName(database)) {
    throw new DatabaseError(
      `Le rôle scratch ne se connecte qu'aux bases scratch_* (reçu ${database}).`,
    );
  }
  const password = rt.loadSecrets()[role.name];
  if (!password) {
    throw new DatabaseError(
      `Aucun mot de passe pour ${role.name} : lancer d'abord « roles --yes ».`,
    );
  }
  return rt.rolePsql(role.name, password, database, opts.rest);
}

export function parseCli(argv) {
  const { values, positionals } = parseArgs({
    args: argv,
    allowPositionals: true,
    options: {
      yes: { type: "boolean", default: false },
      name: { type: "string" },
      as: { type: "string" },
      db: { type: "string" },
      container: { type: "string", default: "property-platform-local-db-1" },
      superuser: { type: "string", default: "property_platform" },
      secrets: { type: "string" },
      "min-free-gb": { type: "string" },
    },
  });
  const separator = argv.indexOf("--");
  const head =
    separator === -1
      ? positionals
      : positionals.slice(
          0,
          positionals.length - (argv.length - separator - 1),
        );
  const [command, action, agent] = head;
  return {
    command,
    action: command === "scratch" ? action : undefined,
    agent: command === "scratch" ? agent : undefined,
    rest: separator === -1 ? [] : argv.slice(separator + 1),
    ...values,
    minFreeGb:
      values["min-free-gb"] === undefined
        ? undefined
        : Number(values["min-free-gb"]),
  };
}

function mainCheckout() {
  const result = spawnSync(
    "git",
    ["rev-parse", "--path-format=absolute", "--git-common-dir"],
    {
      cwd: ROOT,
      encoding: "utf8",
    },
  );
  return result.status === 0 ? path.dirname(result.stdout.trim()) : ROOT;
}

function realRuntime(opts) {
  const secretsPath = path.resolve(
    opts.secrets ?? path.join(mainCheckout(), SECRETS_PATH),
  );
  const exec = (args, { input, envVars = {}, stdio } = {}) => {
    const passed = Object.keys(envVars).flatMap((name) => ["-e", name]);
    return spawnSync(
      "docker",
      ["exec", "-i", ...passed, opts.container, ...args],
      {
        input,
        encoding: "utf8",
        env: { ...process.env, ...envVars, MSYS_NO_PATHCONV: "1" },
        stdio: stdio ?? ["pipe", "pipe", "pipe"],
      },
    );
  };
  const query = (sql) => {
    const result = exec([
      "psql",
      "-X",
      "-At",
      "-U",
      opts.superuser,
      "-d",
      "postgres",
      "-c",
      sql,
    ]);
    if (result.status !== 0)
      throw new DatabaseError(result.stderr.trim() || "psql a échoué.");
    return result.stdout.trim();
  };
  return {
    secretsPath,
    log: (line) => console.log(line),
    loadSecrets: () =>
      existsSync(secretsPath)
        ? JSON.parse(readFileSync(secretsPath, "utf8"))
        : {},
    saveSecrets(secrets) {
      mkdirSync(path.dirname(secretsPath), { recursive: true });
      writeFileSync(secretsPath, `${JSON.stringify(secrets, null, 2)}\n`, {
        mode: 0o600,
      });
      try {
        chmodSync(secretsPath, 0o600);
      } catch {
        // Windows ignores POSIX modes; the file stays in a git-ignored folder.
      }
    },
    superuserSql(sql, envVars, database) {
      const result = exec(
        [
          "psql",
          "-X",
          "-q",
          "-U",
          opts.superuser,
          "-d",
          database,
          "-v",
          "ON_ERROR_STOP=1",
          "-f",
          "-",
        ],
        { input: sql, envVars },
      );
      if (result.stdout.trim()) console.log(result.stdout.trim());
      if (result.status !== 0)
        throw new DatabaseError(result.stderr.trim() || "psql a échoué.");
    },
    databaseExists: (name) =>
      query(`SELECT 1 FROM pg_database WHERE datname = '${name}'`) === "1",
    roleExists: (name) =>
      query(`SELECT 1 FROM pg_roles WHERE rolname = '${name}'`) === "1",
    hostFreeBytes() {
      const stats = statfsSync(ROOT);
      return Number(stats.bavail) * Number(stats.bsize);
    },
    serverFreeBytes() {
      const result = exec([
        "df",
        "-B1",
        "--output=avail",
        "/var/lib/postgresql",
      ]);
      const value = Number(result.stdout.trim().split("\n").pop());
      return result.status === 0 && Number.isFinite(value) ? value : null;
    },
    rolePsql(role, password, database, rest) {
      // TCP inside the container, so PostgreSQL checks this role's password and privileges.
      const result = exec(
        ["psql", "-X", "-h", "127.0.0.1", "-U", role, "-d", database, ...rest],
        { envVars: { PGPASSWORD: password }, stdio: "inherit" },
      );
      return result.status ?? 1;
    },
  };
}

async function main() {
  const opts = parseCli(process.argv.slice(2));
  const rt = realRuntime(opts);
  if (opts.command === "roles") return roles(rt, opts);
  if (opts.command === "scratch") return scratch(rt, opts);
  if (opts.command === "psql") return psql(rt, opts);
  throw new DatabaseError(
    "Commandes : roles, scratch list|create|drop, psql (voir docs/engineering/DATABASE_ROLES.md).",
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
      if (!(error instanceof DatabaseError)) throw error;
      console.error(error.message);
      process.exitCode = 1;
    },
  );
}
