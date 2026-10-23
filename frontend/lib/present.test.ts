// F5 — what the ask page shows for each response (REQ-U2 to U8, U16, U17).
// Run with: npm test  (Node's built-in runner; no extra library)
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  NOTICE,
  answerParts,
  citationLabel,
  degradedMessage,
  indexedLabel,
  splitSources,
  supersededLabel,
  type AskResponse,
  type Source,
} from "./present.ts";

const current: Source = {
  marker: 1,
  passage_id: "travel-expense-policy-v3.1:4.2:0",
  document_id: "travel-expense-policy-v3.1",
  policy_id: "travel-expense-policy",
  title: "Travel and Expense Policy",
  version: "3.1",
  status: "current",
  effective: "2026-04-01",
  superseded_by: null,
  section: "4.2",
  section_title: "Approval thresholds",
  text: "| Claim value | Approval required |",
  score: 0.72,
};
const superseded: Source = {
  ...current,
  marker: 4,
  passage_id: "travel-expense-policy-v3.0:4.1:0",
  document_id: "travel-expense-policy-v3.0",
  version: "3.0",
  status: "superseded",
  superseded_by: "3.1",
  section: "4.1",
};

function response(overrides: Partial<AskResponse>): AskResponse {
  return {
    status: "answered",
    conversation_id: "c",
    message_id: "m",
    answer: "A claim of £75 or more needs approval [1].",
    refusal: null,
    degraded: null,
    sources: [current, superseded],
    meta: {
      prompt_version: "answer-v1",
      model: "anthropic/claude-haiku-5.5",
      top_score: 0.72,
      threshold: 0.5092,
      retrieved: 5,
      corpus_indexed_at: "2026-10-22T23:57:18Z",
      latency_ms: 2000,
    },
    created_at: "2026-10-23T00:00:00Z",
    ...overrides,
  };
}

test("every citation shows document, section number and title, and version (U16)", () => {
  assert.equal(citationLabel(current), "Travel and Expense Policy, §4.2 Approval thresholds, v3.1");
});

test("superseded text is always labelled, never shown as current (U17)", () => {
  assert.equal(supersededLabel(superseded), "Superseded: replaced by v3.1 on this policy");
  assert.equal(supersededLabel(current), null);
});

test("cited sources and earlier versions are kept apart (U2, U8, D4, D7)", () => {
  const { cited, earlier } = splitSources(response({}).sources);
  assert.deepEqual(cited.map((s) => s.marker), [1]);
  assert.deepEqual(earlier.map((s) => s.marker), [4]);
});

test("answer markers become references to their citations (U2)", () => {
  assert.deepEqual(answerParts("Needs approval [1] and sign-off [2]."), [
    { text: "Needs approval " },
    { marker: 1 },
    { text: " and sign-off " },
    { marker: 2 },
    { text: "." },
  ]);
});

test("the indexed date is shown in plain words (U7)", () => {
  assert.equal(indexedLabel("2026-10-22T23:57:18Z"), "Policy documents indexed 22 October 2026");
  assert.equal(indexedLabel(null), "Policy documents: indexed date unknown");
});

test("the standing notice says it is policy, not a decision, and where exceptions go (U6)", () => {
  assert.match(NOTICE, /what the policy says/);
  assert.match(NOTICE, /not a decision/);
  assert.match(NOTICE, /exception/i);
});

test("a degraded result says no answer was composed, for every reason (U5)", () => {
  for (const reason of [
    "generation_disabled",
    "provider_error",
    "provider_timeout",
    "invalid_citations",
  ] as const) {
    assert.match(degradedMessage(reason), /No answer was composed/);
  }
});
