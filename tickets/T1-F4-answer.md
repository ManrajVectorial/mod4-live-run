# T1-F4 — Write the answer

**Status:** todo
**Parent:** [T1](T1.md)
**Depends on:** F3
**Decisions it waits on:** D3, D4, D6, D7

Add the chat model: a cited answer from the retrieved passages only, the kill switch,
citation validation, and the prompt version and model recorded on every answer.

## Requirements

REQ-A1 · REQ-G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11 · NFR-1, NFR-5

## Done when (from `features.md`)

With `GENERATION_ENABLED=true`, `curl -s -H 'Content-Type: application/json' -d '{"question":"Does a claim of exactly £75 need approval?"}' localhost:8000/api/ask` prints `"status":"answered"`, an answer saying yes, a source at v3.1 §4.2, and non-null `prompt_version` and `model`. The same call with `GENERATION_ENABLED=false` prints `"status":"degraded"`

## Command that checks it

```
cd backend && python -m pytest tests/test_generation.py tests/test_api_ask.py && python -m app.evaluate
```

Then run the Done-when line above. The G8 and G11 checks are recorded below by me and
reviewed by you (A4).

## Files it will touch

- `backend/app/generation.py`: new. OpenRouter chat client, timeout, kill switch
  (G1, G6, G7)
- `backend/app/prompts/answer.md`: new. Versioned system prompt (G2, G3)
- `backend/app/citations.py`: new. Validates markers against the retrieved passages (G4)
- `backend/app/main.py`: changed. Adds the `answered` path to `/api/ask` (A1)
- `backend/app/db/`: changed only to write `prompt_version` and `model` (G5). No schema
  change
- `backend/app/logging.py`: changed. Adds token counts (NFR-5)
- `backend/tests/test_generation.py`: new. `test_api_ask.py`: extended
- `tickets/eval-results.md`: updated

## Not in it

- Any web page (F5)
- Follow-up context (F6)
- Choosing D6 or D7

## Evidence
