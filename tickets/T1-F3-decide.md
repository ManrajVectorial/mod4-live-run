# T1-F3 — Decide whether to answer

**Status:** done (2026-10-23)
**Parent:** [T1](T1.md)
**Depends on:** F2
**Decisions it waits on:** D2, D5

Add the refusal rule and the `/api/ask` endpoint. Before F4 exists, a question that clears the
threshold comes back `degraded` (`generation_disabled`). Every exchange is recorded in Postgres.

## Requirements

REQ-R5, R6, R7, R8 · REQ-C1, C2 · REQ-A2, A3, A4, A5 · NFR-2, NFR-3, NFR-4, NFR-6

## Done when (from `features.md`)

With the API running, `curl -s -w ' %{time_total}s\n' -H 'Content-Type: application/json' -d '{"question":"How many days of paid parental leave am I entitled to?"}' localhost:8000/api/ask` prints `"status":"refused"` in under 1.5 s, and the same call with Q1 prints `"status":"degraded"` with a source at `travel-expense-policy-v3.1` §4.2

## Command that checks it

```
cd backend && python -m pytest tests/test_refusal.py tests/test_api_ask.py tests/test_healthz.py tests/test_logging.py
```

Then run the Done-when line above against a running API. Paths and port are placeholders (A38, A39).

## Files it will touch

- `backend/app/refusal.py`: new. The deterministic threshold rule (R5, R6, R7)
- `backend/app/main.py`: new. FastAPI app, `POST /api/ask` (refused and degraded paths),
  `GET /healthz` (A2–A5)
- `backend/app/schemas.py`: new. The PRD §5.1, §5.6 and §5.7 shapes
- `backend/app/db/`: new. The §6 tables for conversations, messages and citations, plus
  migrations (C1, C2)
- `backend/app/logging.py`: new. Structured logs without question text or secrets
  (NFR-4, NFR-6)
- `backend/tests/test_refusal.py`, `test_api_ask.py`, `test_healthz.py`, `test_logging.py`: new
- `tickets/eval-results.md`: updated with the threshold run (R8)

## Not in it

- The chat model and composed answers (F4)
- Follow-ups with `conversation_id` (F6)
- Any web page (F5)
- Choosing D2 or D5

## Evidence

**Done-when, real API (`uvicorn --factory app.main:create_app`) against the Compose Postgres
and Qdrant, with real OpenRouter embeddings:**

```
$ curl -s -w ' %{time_total}s\n' -H 'Content-Type: application/json' -d '{"question":"How many days of paid parental leave am I entitled to?"}' localhost:8000/api/ask
{"status":"refused","conversation_id":"585058ae-a40c-490a-be91-0fd7f1820cc9","message_id":"f4b96384-863e-4519-b4bc-885cc0421a80","answer":null,"refusal":{"reason":"below_threshold","message":"The policy documents don't cover this, so there is no policy answer to give. Who to ask: expenses → Group Finance; leave, pay and benefits → HR; anything else → Compliance."},"degraded":null,"sources":[],"meta":{"prompt_version":null,"model":null,"top_score":0.274968,"threshold":0.5092,"retrieved":5,"corpus_indexed_at":"2026-10-22T23:57:18Z","latency_ms":983},"created_at":"2026-10-23T00:07:46.337017Z"} 2.187753s
```

That was the first request after startup: 2.19 s, which included creating the tables and
opening connections. Five warm repeats:

```
Q13 refused run 1: 1.943487s
Q13 refused run 2: 1.055618s
Q13 refused run 3: 1.148854s
Q13 refused run 4: 1.071948s
Q13 refused run 5: 1.196708s
```

**Honest reading:** 4 of 5 warm refusals are under 1.5 s, and one took 1.94 s. Nearly all of
the time is the embedding call to OpenRouter: 0.8 to 0.97 s of the server-side time. NFR-2
is formally measured on Railway at verification (A18). I'm flagging it as a risk to watch,
not claiming it as met.

```
$ curl ... '{"question":"What is the approval threshold for a travel expense claim?"}' localhost:8000/api/ask
status: degraded   degraded: {"reason": "generation_disabled"}
first source: marker 1, travel-expense-policy-v3.1 §4.2 Approval thresholds, v3.1, current, score 0.7230
sources: v3.1 §4.2, v3.1 §4.1, v3.1 §2.4, v3.1 §3 (current); v3.0 §4.1 (superseded, labelled)
meta: prompt_version null, model null, top_score 0.7230, threshold 0.5092, retrieved 5, latency_ms 793
```

**The 13 questions through the local API** (`python -m app.eval`): Q1–Q10 come back
`degraded` with the expected section in their top three, because composing answers is F4.
Q11–Q13 come back `refused`. That's REQ-R8 at the chosen threshold.
`eval 0/10 answered, 3/3 refused`.

**D2: the refusal threshold**

| Q | expected | top current score |
|---|---|---|
| Q1 | answer | 0.7230 |
| Q2 | answer | 0.7333 |
| Q3 | answer | 0.5819 |
| Q4 | answer | 0.6657 |
| Q5 | answer | **0.5568** (lowest answerable) |
| Q6 | answer | 0.6108 |
| Q7 | answer | 0.6056 |
| Q8 | answer | 0.7116 |
| Q9 | answer | 0.6184 |
| Q10 | answer | 0.5698 |
| Q11 | refuse | 0.4381 |
| Q12 | refuse | **0.4616** (highest must-refuse) |
| Q13 | refuse | 0.2750 |

- **Number:** `REFUSAL_THRESHOLD=0.5092` in `.env`.
- **Reason:** the plan's D2 method. The gap runs from 0.4616 to 0.5568 (0.0952 wide), and
  0.5092 is its midpoint, about 0.048 from each edge. A score must be strictly above it to
  clear, matching the brief's "nothing above threshold". Recorded in the plan's D2 row too.

**Rephrased variants** (`python -m app.eval --variants`, 26 questions in
`backend/eval/variants.md`): 22 land on the right side and **4 mismatch**.

| Q | rephrased question | top score | verdict |
|---|---|---|---|
| Q4 | How much can I spend per night on a hotel in Singapore? | 0.5090 | refuses (should answer) |
| Q6 | What do we do when a client's KYC review is over three months late? | 0.4944 | refuses (should answer) |
| Q7 | For EDD, from what percentage of ownership must we identify the owners? | 0.4261 | refuses (should answer) |
| **Q11** | **Can I claim travel costs for a family member who joins me on business travel?** | **0.5365** | **clears (should refuse)** |

**Open risk:** across all 39 wordings no single threshold separates the two groups. Three
of the mismatches err safe (a refusal), but the Q11 rephrasing clears the gate and would
reach the model. That is exactly the "inferable, not stated" trap the brief warns about. I
haven't changed the plan's method, because the 13 pass and the plan defines the number from
them. I'll check what the model does with that rephrasing once F4 wires it in, and record
the result in the F4 ticket. The full variant table is in the run output.

**Tests:** 66 backend tests passed, including:
- `test_refusal.py`: strictly-above rule, an equal score refuses, no chat-model call, D5 text,
  no start without the threshold
- `test_api_ask.py`: the refused and degraded paths, the record (C1, C2), the 422 and 404
  errors, and the error shape with no trace
- `test_contract.py`: PRD §5.1, written independently of the app's own models
- `test_logging.py`: NFR-4 and NFR-6

In the real API log, the question text appears 0 times and no secret appears.

**Simplest options taken where the plan was silent:**
- `MAX_QUESTION_CHARS=1000`. Assumption A22 said "set in the plan", but the plan has no value.
- A missing `question` and a malformed body both return 422 `question_blank`.
- Framework errors (an unknown route, the wrong method) use the §5.7 error shape with codes
  `not_found` and `method_not_allowed`, which the PRD's list doesn't name.
- A `conversation_id` that is unknown or isn't a UUID returns 404 `conversation_not_found`.
  Appending to a known conversation works already; F6 adds the follow-up behaviour (C3–C6).
- Degraded sources are the current passages scoring strictly above the threshold, plus
  superseded passages of the same policy above it, labelled `superseded` (D4).
- Two test inputs I wrote were wrong and were fixed before the feature passed:
  - a `+00:00` timestamp, where PRD §5.1 shows `...Z`, which is what the app returns;
  - a malformed SQLite URL in the secrets test, replaced by a Postgres URL that holds the
    secret and points at a closed port, so the connection-failure path is tested too.
