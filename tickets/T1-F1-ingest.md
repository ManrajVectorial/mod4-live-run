# T1-F1 — Load the documents

**Status:** todo
**Parent:** [T1](T1.md)
**Decisions it waits on:** D0, D1

Read the five MANIFEST documents, split them into passages, embed them, and store them in
Qdrant with their status.

## Requirements

REQ-I1, I2, I3, I4, I5, I6, I7, I8, I9, I10, I11

## Done when (from `features.md`)

`python -m app.ingest && python -m app.ingest`, then a Qdrant point count on `$QDRANT_COLLECTION`: the total is the same after both runs, the count filtered to `status = superseded` is above zero, and `git status --porcelain backend/corpus` prints nothing

## Command that checks it

```
cd backend && python -m pytest tests/test_ingest.py
```

Then run the Done-when line above. Module names and paths are placeholders until the plan
fixes them (T1-assumptions A38, A39).

## Files it will touch

- `backend/pyproject.toml`: new, with the Python 3.12 project and dependencies (listed in the plan)
- `backend/app/settings.py`: new. Reads §8 settings from the environment and refuses to start
  without the required ones
- `backend/app/corpus.py`: new. MANIFEST and front-matter loading and validation (I1, I2)
- `backend/app/chunking.py`: new. Passages per D1, with section number and title (I3, I4)
- `backend/app/embeddings.py`: new. OpenRouter embedding client (I6)
- `backend/app/vector_store.py`: new. Qdrant collection and §7 payload (I5, I7, I8, I9, I11)
- `backend/app/ingest.py`: new. Command-line entry point
- `backend/tests/test_ingest.py`, `backend/tests/fixtures/`: new. Fixtures are modified
  copies of corpus files, kept outside `backend/corpus/` (A14)
- `.env.example`: new. Variable names only, no values
- `.github/workflows/ci.yml`: new. Tests, security scan, licence check (A7)
- `backend/corpus/`: **read only, never written** (I10)

## Not in it

- Search and scoring (F2)
- Any API (F3)
- Scheduled or change-triggered re-indexing
- Choosing D0 or D1: they are decided at planning, not in this ticket

## Evidence
