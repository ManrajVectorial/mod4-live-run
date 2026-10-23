# T1-F6 — Follow-up questions *(optional)*

**Status:** done (2026-10-23). Built with D9 amendment 2 (the model rewrites follow-ups); every check below passes.
**Optional:** no. Every feature ships (product owner, 2026-10-23)
**Parent:** [T1](T1.md)
**Depends on:** F5
**Decisions it waits on:** D8, D9

Continue a conversation: context per D8, retrieval per D9, the refusal rule on every turn, and
Reset starting afresh.

## Requirements

REQ-C3, C4, C5, C6

## Done when (from `features.md`)

`curl` Q1 to `/api/ask` and keep its `conversation_id`; sending `"And does a claim of exactly that amount need it?"` with that ID prints `"status":"answered"` citing v3.1 §4.2, then `"Can I expense my partner's flight?"` with the same ID prints `"status":"refused"`

## Command that checks it

```
cd backend && python -m pytest tests/test_conversation.py
```

Then run the Done-when sequence above.

## Files it will touch

- `backend/app/conversation.py`: new. Loads earlier turns per D8 and builds the follow-up
  retrieval query per D9 (C4, C5)
- `backend/app/main.py`: changed. Accepts `conversation_id`, returns 404 for unknown IDs (C3)
- `frontend/app/page.tsx`: changed. Keeps `conversation_id` across turns, and Reset drops it (C6)
- `backend/tests/test_conversation.py`: new

## Not in it

- Viewing past conversations (F8)
- Any chat-model call before the refusal rule (REQ-R6 still holds)
- Choosing D8 or D9

## Evidence

**Done-when, real API (port 8014), one conversation:**

```
1) Q1 "What is the approval threshold for a travel expense claim?"
   status: answered | top_score: 0.7230 | cited: v3.1 §4.2            PASS
2) "And does a claim of exactly that amount need it?"
   status: answered | top_score: 0.7299 | cited: v3.1 §4.2
   answer: Yes. A claim of exactly £75 requires line-manager approval before reimbursement,
   and thresholds are inclusive of the stated value [1]. ...           PASS
3) "Can I expense my partner's flight?"
   status: degraded (invalid_citations: the model said NOT STATED) | top_score: 0.5420
   cited: v3.1 §7.2                                                     FAIL: must be refused
```

**This is the planned stop agreed for D9.** Joined with the question before it, the partner's
flight question clears the gate. No answer was invented, but it isn't refused.

**Gate scores (threshold 0.5092):**

| Search text | Score | Result |
|---|---|---|
| Follow-up on its own | 0.5071 | refuses |
| Follow-up joined with Q1 (D9) | 0.7299 | clears |
| Partner's flight on its own | 0.4229 | refuses |
| Partner's flight joined with the follow-up (D9) | 0.5420 | clears |

No single text passes both checks. Gating on the joined text lets the partner's flight
through. Gating on the question alone refuses the follow-up, which is 0.002 under the
threshold.

**Tests:** 97 backend tests passed, including `test_conversation.py` (7, covering C3–C6), and
8 frontend tests passed. The 13 single questions still give `eval 10/10 answered, 3/3
refused` with this code in place.

**History: option B tried, then F6 cut (product owner's instruction, 2026-10-23). Superseded by amendment 2 below.** The plan was to
keep D9 and add a second rule: the follow-up on its own must also clear a floor, set at the
midpoint of the gap measured on a small follow-up test set. Then F6 would be finished. If no
floor separated the cases, F6 would be cut instead.

**Follow-up test set:** `backend/eval/followups.md`, six two-turn cases, measured with
`python -m app.followup_eval` (threshold 0.5092):

| case | expect | follow-up | joined (D9) | alone |
|---|---|---|---|---|
| C1 | answer | And does a claim of exactly that amount need it? | 0.7299 | 0.5070 |
| C2 | answer | And for Singapore? | 0.7471 | **0.3447** |
| C3 | answer | And for a standard-risk client? | 0.5412 | 0.4635 |
| C4 | refuse | Can I expense my partner's flight? | 0.6275 | 0.4229 |
| C5 | refuse | How many days of paid parental leave am I entitled to? | 0.5641 | 0.2750 |
| C6 | refuse | What is our policy on cryptocurrency held by clients? | 0.5370 | **0.4616** |

```
No floor separates the cases on their own scores: cut F6 (option C).
```

**Why it was cut:**
- **On its own:** the lowest answerable follow-up ("And for Singapore?", 0.3447) scores
  below the highest off-topic one (cryptocurrency, 0.4616), so no floor sits between them.
- **Joined (D9):** every off-topic case clears the 0.5092 threshold, so the joined text
  can't separate them either.

A short follow-up carries too little meaning to score on its own, and joining it to the
previous question carries that question's topic over to whatever comes next. Any rule built
on these scores would either refuse real follow-ups or let off-topic ones through. That
second failure is the one the product must not have (S5).

**What was removed and what stays:**
- **Removed:** the uncommitted F6 code (follow-up context, the joined search, and the
  conversation view on the page). It was never committed.
- **Stays:** `backend/eval/followups.md` and `python -m app.followup_eval`, so the
  measurement can be repeated if retrieval changes.
- **Delivered of C3–C6:** only what F3 already built. `/api/ask` accepts a known
  `conversation_id` and appends to it, and an unknown one returns 404. Each question is
  searched and gated on its own. The model sees no earlier context, and the web page asks one
  question at a time.

**D9 amendment 2 (2026-10-23, decided by the product owner).** This reverses the cut.
- On a follow-up, the chat model first rewrites the new question as a standalone question,
  using the conversation so far. It only rewrites; it never answers.
- The search runs on the rewritten question, and the same refusal rule and threshold (0.5092)
  apply to it.
- The first question of a conversation is never rewritten.
- The check is the six-case follow-up set in `backend/eval/followups.md`, plus the Done-when
  line.

**This departs from REQ-R6 and ADR-001.** A refused follow-up has now made one chat-model
call, the rewrite. The locked PRD (REQ-R6) and ADR-001 put the refusal rule before any model
call. The model still decides nothing, because the rule judges the rewritten question. First
questions are unchanged. If you want the documents to match, REQ-R6 needs an amendment, which
only you can approve (the PRD is protected).

## Evidence (D9 amendment 2 build)

**Done-when, real API on 8014, one conversation:**

```
1) Q1 "What is the approval threshold for a travel expense claim?"
   status: answered | top_score: 0.7230 | cited: v3.1 §4.2                       PASS
2) "And does a claim of exactly that amount need it?"
   status: answered | top_score: 0.7182 (rewritten question) | cited: v3.1 §4.2
   Yes, a claim of exactly £75 requires line-manager approval before reimbursement [1]. ...   PASS
3) "Can I expense my partner's flight?"
   status: refused | top_score: 0.4229 | cited: none
   The policy documents don't cover this, so there is no policy answer to give. Who to ask: ...   PASS
```

**Follow-up set** (`python -m app.followup_eval`, every case run through the API as a
two-turn conversation):

| case | expect | follow-up | status | top score (rewritten) | outcome |
|---|---|---|---|---|---|
| C1 | answer | And does a claim of exactly that amount need it? | answered | 0.7225 | PASS |
| C2 | answer | And for Singapore? | answered | 0.6657 | PASS |
| C3 | answer | And for a standard-risk client? | answered | 0.5374 | PASS |
| C4 | refuse | Can I expense my partner's flight? | refused | 0.4690 | PASS |
| C5 | refuse | How many days of paid parental leave am I entitled to? | refused | 0.2750 | PASS |
| C6 | refuse | What is our policy on cryptocurrency held by clients? | refused | 0.4825 | PASS |

`followups 6/6 passed`. Through the web proxy on 3014, "And for Singapore?" after the London
question is answered in the same conversation (£300 per night).

**The 13 questions after F6:** `eval 10/10 answered, 3/3 refused`. In the API log: 0 unhandled
errors and 0 rewrite fallbacks.

**What it took:**
- **`rewrite-v1` failed the check.** The model added framing the person never asked for. The
  partner's-flight question became "...under Aldermere Bank's travel expense policy?"
  (0.6499), and the cryptocurrency one gained "Aldermere Bank's policy" (0.5267). Both cleared
  the threshold. With a thin history, it once replied with a sentence instead of a question.
- **`rewrite-v2` fixed it.** If the question already makes sense on its own, it is returned
  unchanged. No words are added that the person didn't say or refer to; only references like
  "that amount" are filled in.
- **A code guard was added.** A rewrite that doesn't end with "?" counts as failed, and the
  search falls back to the question as asked. Both prompt versions are registered in
  `app/prompts/versions.json`.

**Risks:**
- **Refusal latency.** A refused follow-up took 1.9 s, because the rewrite is an extra model
  call. That is above NFR-2's 1.5 s target, which was written for refusals with no model call.
- **Thin margins.** Through the API, C4 and C6 refuse by only about 0.04 and 0.03. The rewrite
  is a model output, so a different wording on another run could move them. The set is small
  (six cases).
- **REQ-R6 deviation:** recorded above, in the D9 amendment.

**Tests:** 117 backend tests passed, including:
- `test_conversation.py` (9):
  - append to a conversation, or 404 if it doesn't exist;
  - the first question is never rewritten;
  - a follow-up is rewritten with the conversation and searched as rewritten;
  - the refusal rule judges the rewritten question, with no answering call;
  - D8: the answer model sees the last 5 messages;
  - a failed rewrite falls back to the question as asked;
  - no rewrite when generation is off;
  - Reset;
  - the rewrite prompt is registered.
- `test_rewriter.py` (7) and `test_followup_eval.py` (4).

The frontend has 11 tests (a new one for the conversation state); the typecheck and build pass.

**Simplest options taken:**
- The rewriter uses the same chat model and settings as answers, at temperature 0.
- The answer model is given the rewritten question plus the D8 context.
- The stored question is the one the person typed.
- `FOLLOWUP_QUERY_QUESTIONS`, the old joined-search setting, is removed.
- The page shows the conversation turn by turn, and Reset reloads it.

## Change after review (2026-10-23, T1-review FND-1)

- **The failed-rewrite fallback is narrowed.** "Search as asked" was my simplest-option choice
  above.
- **When the rewrite fails at the provider** (a timeout or an error, so the model is down):
  - the follow-up is searched joined with the previous question, judged by the same rule and
    threshold;
  - if it clears, the response is `degraded` with the passages, without calling the model
    again (T1 Error criterion).
- **When the reply is unusable** (not a question, empty or too long), it still searches as
  asked.
- **Evidence:** in `T1-review.md`, under "Fixes". The follow-up set is still 6/6.
