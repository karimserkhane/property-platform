import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { test } from "node:test";
import { previewAccess } from "../src/preview-access.ts";

const credentials = "operator:high-entropy-test-password";
const digest = createHash("sha256").update(credentials).digest("hex");
const authorization = `Basic ${Buffer.from(credentials).toString("base64")}`;

test("the optional preview guard preserves local mode and fails closed on bad configuration", () => {
  assert.equal(previewAccess(null, {}), "allowed");
  assert.equal(previewAccess(null, { required: "0" }), "allowed");
  for (const environment of [
    { required: "1" },
    { required: "1", digest: "invalid" },
    { required: "true", digest },
    { required: "", digest },
  ])
    assert.equal(previewAccess(authorization, environment), "unavailable");
});

test("only the exact preview credentials authorize a request", () => {
  const environment = { required: "1", digest };
  assert.equal(previewAccess(authorization, environment), "allowed");
  assert.equal(
    previewAccess(authorization.replace("Basic", "basic"), environment),
    "allowed",
  );
  for (const header of [
    null,
    "",
    "Bearer token",
    "Basic YQ==ignored",
    "Basic YQ=",
    `Basic ${Buffer.from("operator:wrong").toString("base64")}`,
    `Basic ${Buffer.from("other:high-entropy-test-password").toString("base64")}`,
    `Basic ${"A".repeat(4096)}`,
  ])
    assert.equal(previewAccess(header, environment), "unauthorized");
});
