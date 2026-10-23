# T1-F6 — Follow-up questions *(optional)*

**Status:** in development (2026-10-23). **The cut is reversed: every feature ships.** D9 is amended (amendment 2, below).
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
