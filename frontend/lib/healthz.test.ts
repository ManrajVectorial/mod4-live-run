// Deployment: the web service answers its own /healthz, for the platform's health check.
// It does not call the API, so a slow API never fails the web's health check.
import assert from "node:assert/strict";
import { test } from "node:test";

import { GET } from "../app/healthz/route.ts";

test("the web /healthz answers 200 with its own status, without calling the API", async () => {
  const realFetch = globalThis.fetch;
  globalThis.fetch = (() => {
    throw new Error("/healthz must not call the API");
  }) as typeof fetch;
  try {
    const response = GET();
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { status: "ok", service: "policy-assistant-web" });
  } finally {
    globalThis.fetch = realFetch;
  }
});
