# T1-F3 — Decide whether to answer

**Status:** todo
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
