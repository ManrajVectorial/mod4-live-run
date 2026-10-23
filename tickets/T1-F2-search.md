# T1-F2 — Search them

**Status:** done (2026-10-23)
**Parent:** [T1](T1.md)
**Depends on:** F1
**Decisions it waits on:** D0, D3, D4

Embed a question and return the top-K passages with scores, plus the thirteen-question
evaluation command.

## Requirements

REQ-R1, R2, R3, R4

## Done when (from `features.md`)

`python -m app.evaluate` writes a thirteen-row results table under `tickets/`, and the Q1 row shows `travel-expense-policy-v3.1` §4.2 in the top three

## Command that checks it

```
cd backend && python -m pytest tests/test_retrieval.py && python -m app.evaluate
```

Module names are placeholders (A39).

## Files it will touch

- `backend/app/retrieval.py`: new. Embed the question, run the Qdrant top-K search, order
  deterministically, apply D4 (R1, R2, R3)
- `backend/app/evaluate.py`: new. Runs the 13 `EVALUATION.md` questions and writes the table (R4)
- `backend/tests/test_retrieval.py`: new
- `tickets/eval-results.md`: new. Generated and overwritten on each run (A16)
- `backend/corpus/EVALUATION.md`: **read only**

## Not in it

- The refusal rule and threshold (F3)
- Any API endpoint (F3)
- Composing answers (F4)
- Choosing D3 or D4

## Evidence

**Done-when, real OpenRouter embeddings against the Compose Qdrant (130 passages from F1):**

```
$ cd backend && python -m app.eval
| Q | top score | expected in top 3 | top 3 retrieved | API status | cited | outcome |
|---|---|---|---|---|---|---|
| Q1 | 0.723 | yes | travel-expense-policy-v3.1 §4.2 (0.723), travel-expense-policy-v3.1 §4.1 (0.643), travel-expense-policy-v3.1 §2.4 (0.554) | error: URLError | — | — |
| Q2 | 0.733 | yes | travel-expense-policy-v3.1 §4.2 (0.733), travel-expense-policy-v3.1 §4.1 (0.570), travel-expense-policy-v3.1 §4.5 (0.529) | error: URLError | — | — |
| Q3 | 0.582 | yes | travel-expense-policy-v3.1 §5.2 (0.582), travel-expense-policy-v3.1 §5.3 (0.494), travel-expense-policy-v3.1 §6.3 (0.361) | error: URLError | — | — |
| Q4 | 0.666 | yes | travel-expense-policy-v3.1 §6.2 (0.666), travel-expense-policy-v3.1 §6.1 (0.403), travel-expense-policy-v3.1 §6.3 (0.342) | error: URLError | — | — |
| Q5 | 0.557 | yes | client-onboarding-kyc-v2.4 §6.3 (0.557), client-onboarding-kyc-v2.4 §6.1 (0.527), client-onboarding-kyc-v2.4 §6.2 (0.494) | error: URLError | — | — |
| Q6 | 0.611 | yes | client-onboarding-kyc-v2.4 §6.4 (0.611), client-onboarding-kyc-v2.4 §6.3 (0.491), client-onboarding-kyc-v2.4 §6.2 (0.472) | error: URLError | — | — |
| Q7 | 0.606 | yes | client-onboarding-kyc-v2.4 §4.2 (0.606), client-onboarding-kyc-v2.4 §4.3 (0.542), client-onboarding-kyc-v2.4 §5.2 (0.517) | error: URLError | — | — |
| Q8 | 0.712 | yes | records-retention-v4.0 §4.2 (0.712), records-retention-v4.0 §4.1 (0.600), client-onboarding-kyc-v2.4 §7.2 (0.511) | error: URLError | — | — |
| Q9 | 0.618 | yes | outsourcing-third-party-v1.8 §4.1 (0.618), outsourcing-third-party-v1.8 §4.2 (0.588), outsourcing-third-party-v1.8 §4.3 (0.582) | error: URLError | — | — |
| Q10 | 0.570 | yes | records-retention-v4.0 §4.2 (0.570), outsourcing-third-party-v1.8 §6.4 (0.565), records-retention-v4.0 §4.1 (0.534) | error: URLError | — | — |
| Q11 | 0.438 | must refuse | travel-expense-policy-v3.1 §5.2 (0.438), travel-expense-policy-v3.1 §5.1 (0.423), travel-expense-policy-v3.1 §6.3 (0.410) | error: URLError | — | — |
| Q12 | 0.462 | must refuse | client-onboarding-kyc-v2.4 §9 (0.462), client-onboarding-kyc-v2.4 §1.2 (0.437), records-retention-v4.0 §9 (0.436) | error: URLError | — | — |
| Q13 | 0.275 | must refuse | travel-expense-policy-v3.1 §6.3 (0.275), travel-expense-policy-v3.1 §7.4 (0.272), records-retention-v4.0 §4.1 (0.253) | error: URLError | — | — |
eval --
```

- The table has 13 rows and is written to `tickets/eval-results.md`.
- The Q1 row shows `travel-expense-policy-v3.1 §4.2` in the top three, as its top hit (0.723).
- The expected section is in the top three for all ten answerable questions.
- The API columns show `URLError` because `/api/ask` arrives in F3, so the command exits 1
  for now, as designed.

**Tests:** `python -m pytest tests/test_retrieval.py` gives 8 passed, covering R1 to R4.
Whole suite: 41 backend tests passed; ruff and bandit are clean.

**Notes:**
- One test I wrote first was wrong before any code existed. Its row filter also matched the
  table header, and it relied on the fake word-hashing embedder to find §4.2, which says
  nothing about real retrieval. I replaced it with tests that feed fixed search results into
  the table and outcome code and check them exactly. Real retrieval is proved by the
  Done-when run above.
- Simplest option taken: one query returns the top-K over all passages. The hits are then
  split into current passages (the gate and the model use these, D4) and superseded ones
  (kept for "earlier version" notes). The "top score" column is the top *current* score,
  which is what the refusal rule uses.
- The expected sections from `EVALUATION.md` are written out in `app/eval.py` (`EXPECTED`).
  The file itself is read only. Q8 accepts §4.1 or §4.2; Q10 needs both conflicting
  sections.
