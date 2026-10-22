# T1-F2 — Search them

**Status:** todo
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
