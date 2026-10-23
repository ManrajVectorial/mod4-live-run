// F9 — what each kind of result looks like, before any styling (T1.md F9 criteria).
// Run with: npm test  (Node's built-in runner; no extra library)
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  CONFLICT_LEAD,
  RESULT_LOOKS,
  citationCards,
  conflictView,
  degradedView,
  errorView,
  markerHref,
  refusalView,
  resultLook,
  type AskResponse,
  type Source,
} from "./present.ts";

const REFUSAL_TEXT = readFileSync(new URL("../../backend/app/text/refusal.md", import.meta.url), "utf8").trim();
const CONFLICT_TEMPLATE = readFileSync(new URL("../../backend/app/text/conflict.md", import.meta.url), "utf8").trim();

function source(overrides: Partial<Source>): Source {
  return {
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
    text: "| £75 or more | Line-manager approval |",
    score: 0.72,
    ...overrides,
  };
}

function response(overrides: Partial<AskResponse>): AskResponse {
  return {
    status: "answered",
    conversation_id: "c",
    message_id: "msg-1",
    answer: "A claim of £75 or more needs line-manager approval [1].",
    refusal: null,
    degraded: null,
    sources: [source({})],
    meta: {
      prompt_version: "answer-v1",
      model: "m",
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

// Q10 as the API returns it: the answer, then the D6 notice filled in exactly as the
// backend does (conflicts.py: "{title} v{version} §{section} [{marker}]").
const retention = source({
  marker: 1,
  passage_id: "records-retention-v4.0:4.1:0",
  document_id: "records-retention-v4.0",
  policy_id: "records-retention",
  title: "Records Retention and Data Handling Policy",
  version: "4.0",
  section: "4.1",
  section_title: "General table",
  text: "| Client correspondence | 7 years from end of relationship |",
});
const outsourcing = source({
  marker: 2,
  passage_id: "outsourcing-third-party-v1.8:6.4:0",
  document_id: "outsourcing-third-party-v1.8",
  policy_id: "outsourcing-third-party",
  title: "Outsourcing and Third-Party Risk Policy",
  version: "1.8",
  section: "6.4",
  section_title: "Return and destruction on exit",
  text: "The provider must destroy all copies within five years of termination.",
});
const label = (s: Source) => `${s.title} v${s.version} §${s.section} [${s.marker}]`;
const NOTE = CONFLICT_TEMPLATE.replace("{first}", label(retention)).replace("{second}", label(outsourcing));
const q10 = response({
  answer: `Records Retention requires seven years [1]. Outsourcing requires destruction within five years [2].\n\n${NOTE}`,
  sources: [retention, outsourcing],
});

test("every result kind, and an error, has its own look: colour, icon and heading", () => {
  const kinds = ["answer", "conflict", "refusal", "passages", "error"] as const;
  assert.deepEqual(Object.keys(RESULT_LOOKS).sort(), [...kinds].sort());
  const icons = kinds.map((k) => RESULT_LOOKS[k].icon);
  const headings = kinds.map((k) => RESULT_LOOKS[k].heading);
  assert.equal(new Set(icons).size, kinds.length, "icons are all different");
  assert.equal(new Set(headings).size, kinds.length, "headings are all different");
  assert.equal(resultLook(response({})), "answer");
  assert.equal(resultLook(q10), "conflict");
  assert.equal(resultLook(response({ status: "refused", answer: null, sources: [] })), "refusal");
  assert.equal(resultLook(response({ status: "degraded", answer: null, degraded: { reason: "generation_disabled" } })), "passages");
});

test("a refusal shows the 'not covered' message and who to ask, as a list (U4, D5)", () => {
  const view = refusalView(response({ status: "refused", answer: null, sources: [], refusal: { reason: "below_threshold", message: REFUSAL_TEXT } }));
  assert.equal(view.heading, "Not covered by the policy documents");
  assert.match(view.message, /don't cover this/);
  assert.doesNotMatch(view.message, /Who to ask/);
  assert.deepEqual(view.whoToAsk, [
    { topic: "expenses", team: "Group Finance" },
    { topic: "leave, pay and benefits", team: "HR" },
    { topic: "anything else", team: "Compliance" },
  ]);
  assert.equal(view.cards.length, 0, "a refusal cites no policy");
});

test("a refusal whose text has no who-to-ask part still shows the whole message", () => {
  const view = refusalView(response({ status: "refused", answer: null, sources: [], refusal: { reason: "below_threshold", message: "Not covered." } }));
  assert.equal(view.message, "Not covered.");
  assert.deepEqual(view.whoToAsk, []);
});

test("a degraded result says no answer was composed and shows every passage (U5)", () => {
  const old = source({ marker: 2, document_id: "travel-expense-policy-v3.0", version: "3.0", status: "superseded", superseded_by: "3.1", passage_id: "p2" });
  const view = degradedView(response({ status: "degraded", answer: null, degraded: { reason: "generation_disabled" }, sources: [source({}), old] }));
  assert.equal(view.heading, "No answer was composed");
  assert.match(view.message, /No answer was composed/);
  assert.equal(view.cards.length + view.earlier.length, 2);
});

test("an error says what went wrong and what to try, and is not a refusal (U12)", () => {
  const view = errorView("The service can't be reached. Check your connection and try again.");
  assert.equal(view.heading, RESULT_LOOKS.error.heading);
  assert.notEqual(view.heading, RESULT_LOOKS.refusal.heading);
  assert.match(view.message, /can't be reached/);
  assert.ok(view.tryThis.length >= 1);
  assert.ok(view.tryThis.every((step) => /\w/.test(step)));
});

test("citation cards show document, section and version, link to the section, and badge superseded (U16, U17, B4)", () => {
  const old = source({ marker: 4, document_id: "travel-expense-policy-v3.0", version: "3.0", status: "superseded", superseded_by: "3.1", section: "4.1", passage_id: "p4" });
  const [card, oldCard] = citationCards("msg-1", [source({}), old]);
  assert.equal(card.document, "Travel and Expense Policy");
  assert.equal(card.section, "§4.2 Approval thresholds");
  assert.equal(card.version, "v3.1");
  assert.equal(card.href, "/corpus/travel-expense-policy-v3.1#section-4.2");
  assert.equal(card.badge, null);
  assert.equal(oldCard.href, "/corpus/travel-expense-policy-v3.0#section-4.1");
  assert.equal(oldCard.badge, "Superseded: replaced by v3.1 on this policy");
});

test("citation anchors are unique per answer, so [n] jumps to its own card (FND-4)", () => {
  const [a] = citationCards("msg-1", [source({})]);
  const [b] = citationCards("msg-2", [source({})]);
  assert.notEqual(a.anchorId, b.anchorId);
  assert.equal(markerHref("msg-1", 1), `#${a.anchorId}`);
});

test("the conflict notice matches the backend's D6 template", () => {
  assert.ok(CONFLICT_TEMPLATE.startsWith(CONFLICT_LEAD), "the frontend detects the notice by its first words");
  assert.match(CONFLICT_TEMPLATE, /Escalate to Group Legal and Group Operational Risk/);
});

test("the conflict case shows both policies side by side under the escalation notice (Q10, D6)", () => {
  const view = conflictView(q10);
  assert.ok(view, "Q10 is recognised as a conflict");
  assert.equal(view.body, "Records Retention requires seven years [1]. Outsourcing requires destruction within five years [2].");
  assert.equal(view.heading, "These policies conflict");
  assert.match(view.escalate, /Escalate to Group Legal and Group Operational Risk/);
  assert.deepEqual(view.sides.map((s) => s.document), [
    "Records Retention and Data Handling Policy",
    "Outsourcing and Third-Party Risk Policy",
  ]);
  assert.deepEqual(view.sides.map((s) => s.section), ["§4.1 General table", "§6.4 Return and destruction on exit"]);
  assert.ok(view.sides.every((s) => s.text.length > 0), "each side shows its passage");
});

test("an ordinary answer is not a conflict", () => {
  assert.equal(conflictView(response({})), null);
  assert.equal(conflictView(response({ status: "refused", answer: null, sources: [] })), null);
});
