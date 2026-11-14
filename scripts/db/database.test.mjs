import assert from "node:assert/strict";
import test from "node:test";
import {
  checkFreeSpace,
  completeSecrets,
  createScratchSql,
  DatabaseError,
  dropScratchSql,
  isScratchName,
  MIN_FREE_BYTES,
  parseCli,
  psql,
  ROLES,
  roles,
  rolesSql,
  scratch,
  scratchName,
} from "./database.mjs";

const PASSWORDS = Object.fromEntries(
  Object.values(ROLES).map((role) => [role.name, `${role.name}-password-0123456789`]),
);

// A runtime with no Docker: every SQL text and psql call is recorded.
function fakeRuntime(overrides = {}) {
  const state = {
    secrets: { ...PASSWORDS },
    saved: null,
    sql: [],
    psql: [],
    logs: [],
    databases: new Set(["postgres", "property_platform", "template_postgis"]),
    roles: new Set(Object.values(ROLES).map((role) => role.name)),
    hostFree: 40 * 1024 ** 3,
    serverFree: 40 * 1024 ** 3,
    ...overrides,
  };
  const rt = {
    secretsPath: "/tmp/roles.local.json",
    log: (line) => state.logs.push(line),
    loadSecrets: () => state.secrets,
    saveSecrets: (secrets) => {
      state.saved = secrets;
    },
    superuserSql: (sql, env, database) => state.sql.push({ sql, env, database }),
    databaseExists: (name) => state.databases.has(name),
    roleExists: (name) => state.roles.has(name),
    hostFreeBytes: () => state.hostFree,
    serverFreeBytes: () => state.serverFree,
    rolePsql: (...args) => {
      state.psql.push(args);
      return 0;
    },
  };
  return { rt, state };
}

test("scratch names are limited to scratch_<agent>[_<suffix>]", () => {
  assert.equal(scratchName("claude"), "scratch_claude");
  assert.equal(scratchName("codex", "a45"), "scratch_codex_a45");
  for (const bad of [undefined, "", "C", "claude;drop", "1claude", "a".repeat(21)]) {
    assert.throws(() => scratchName(bad), DatabaseError);
  }
  assert.throws(() => scratchName("claude", "x-y"), DatabaseError);
  assert.ok(isScratchName("scratch_claude_trial1"));
  for (const name of ["property_platform", "scratch_", "restore_check_1", "scratch_x;drop"]) {
    assert.equal(isScratchName(name), false, name);
  }
  assert.throws(() => dropScratchSql("property_platform"), DatabaseError);
  assert.throws(() => createScratchSql("rebuild_check_1"), DatabaseError);
});

test("roles SQL is idempotent and never contains a password", () => {
  const sql = rolesSql();
  for (const role of Object.values(ROLES)) {
    assert.match(sql, new RegExp(`\\\\getenv \\w+ ${role.env}`));
    assert.match(sql, new RegExp(`ALTER ROLE ${role.name} WITH LOGIN NOSUPERUSER`));
  }
  assert.match(sql, /WHERE NOT EXISTS \(SELECT 1 FROM pg_roles WHERE rolname = r\) \\gexec/);
  assert.match(sql, /GRANT pg_read_all_data TO pp_agent_readonly;/);
  assert.match(sql, /ALTER ROLE pp_agent_readonly SET default_transaction_read_only = on;/);
  assert.match(sql, /REVOKE CONNECT, TEMPORARY ON DATABASE property_platform FROM PUBLIC;/);
  assert.match(sql, /REVOKE ALL ON DATABASE property_platform FROM pp_agent_scratch;/);
  assert.doesNotMatch(sql, /(?<!NO)SUPERUSER/);
  assert.doesNotMatch(sql, /password-0123456789/);
});

test("missing passwords are generated, existing ones kept", () => {
  const partial = { pp_agent_readonly: "kept-password-0123456789" };
  const { secrets, changed } = completeSecrets(partial, () => "generated-password-0123456789");
  assert.equal(changed, true);
  assert.equal(secrets.pp_agent_readonly, "kept-password-0123456789");
  assert.equal(secrets.pp_app, "generated-password-0123456789");
  assert.equal(completeSecrets(PASSWORDS).changed, false);
});

test("roles prints a plan without --yes and applies with the passwords in the environment", async () => {
  const plan = fakeRuntime({ secrets: {} });
  assert.equal(await roles(plan.rt, { container: "db", yes: false }), 0);
  assert.equal(plan.state.sql.length, 0);
  assert.equal(plan.state.saved, null);

  const apply = fakeRuntime({ secrets: {} });
  await roles(apply.rt, { container: "db", yes: true });
  assert.ok(apply.state.saved);
  const [call] = apply.state.sql;
  assert.equal(call.database, "property_platform");
  assert.equal(call.env.PP_APP_PASSWORD, apply.state.saved.pp_app);
  assert.doesNotMatch(call.sql, new RegExp(apply.state.saved.pp_app));
  assert.ok(apply.state.logs.every((line) => !line.includes(apply.state.saved.pp_app)));
});

test("scratch create checks the disk before anything", async () => {
  const { rt, state } = fakeRuntime({ hostFree: MIN_FREE_BYTES - 1 });
  await assert.rejects(
    scratch(rt, { action: "create", agent: "claude", yes: true }),
    /Place insuffisante/,
  );
  assert.equal(state.sql.length, 0);
  assert.throws(() => checkFreeSpace(MIN_FREE_BYTES, MIN_FREE_BYTES - 1), /serveur PostgreSQL/);
  assert.doesNotThrow(() => checkFreeSpace(MIN_FREE_BYTES, null));
});

test("scratch create uses the PostGIS template and the scratch owner", async () => {
  const { rt, state } = fakeRuntime();
  await scratch(rt, { action: "create", agent: "claude", name: "a45", yes: true });
  const [call] = state.sql;
  assert.match(call.sql, /CREATE DATABASE scratch_claude_a45 TEMPLATE template_postgis OWNER pp_agent_scratch;/);
  assert.match(call.sql, /REVOKE ALL ON DATABASE scratch_claude_a45 FROM PUBLIC;/);

  const missingRole = fakeRuntime({ roles: new Set() });
  await assert.rejects(
    scratch(missingRole.rt, { action: "create", agent: "claude", yes: true }),
    /roles --yes/,
  );
});

test("scratch drop only touches its own database and needs --yes", async () => {
  const databases = new Set(["scratch_claude"]);
  const plan = fakeRuntime({ databases });
  await scratch(plan.rt, { action: "drop", agent: "claude", yes: false });
  assert.equal(plan.state.sql.length, 0);

  const apply = fakeRuntime({ databases });
  await scratch(apply.rt, { action: "drop", agent: "claude", yes: true });
  assert.match(apply.state.sql[0].sql, /DROP DATABASE IF EXISTS scratch_claude WITH \(FORCE\);/);

  const absent = fakeRuntime();
  await scratch(absent.rt, { action: "drop", agent: "codex", yes: true });
  assert.equal(absent.state.sql.length, 0);
});

test("psql connects as a limited role only", async () => {
  const { rt, state } = fakeRuntime();
  await psql(rt, { as: "readonly", rest: ["-c", "select 1"] });
  assert.deepEqual(state.psql[0], [
    "pp_agent_readonly",
    PASSWORDS.pp_agent_readonly,
    "property_platform",
    ["-c", "select 1"],
  ]);
  await assert.rejects(psql(rt, { as: "app", rest: [] }), DatabaseError);
  await assert.rejects(psql(rt, { as: "scratch", db: "property_platform", rest: [] }), /scratch_/);
  await assert.rejects(psql(rt, { as: "scratch", rest: [] }), /--db/);
});

test("parseCli separates psql arguments after --", () => {
  const opts = parseCli(["psql", "--as", "readonly", "--", "-c", "select 1"]);
  assert.equal(opts.command, "psql");
  assert.equal(opts.as, "readonly");
  assert.deepEqual(opts.rest, ["-c", "select 1"]);
  const create = parseCli(["scratch", "create", "claude", "--name", "a45", "--yes"]);
  assert.equal(create.action, "create");
  assert.equal(create.agent, "claude");
  assert.equal(create.name, "a45");
  assert.equal(create.yes, true);
  assert.equal(create.container, "property-platform-local-db-1");
});
