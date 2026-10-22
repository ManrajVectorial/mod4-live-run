# T1-F1 — Load the documents

**Status:** done (2026-10-23)
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

**Done-when, run against Docker Compose Qdrant with real OpenRouter embeddings
(`openai/text-embedding-3-small`, 1,536 dimensions):**

```
$ python -m app.ingest && echo "total after run 1: $(count '{"exact":true}')"
Indexed 5 documents as 130 passages (19 from superseded documents) into 'policy_passages' at 2026-10-22T23:57:12+00:00.
total after run 1: 130
$ python -m app.ingest && echo "total after run 2: $(count '{"exact":true}')"
Indexed 5 documents as 130 passages (19 from superseded documents) into 'policy_passages' at 2026-10-22T23:57:18+00:00.
total after run 2: 130
$ echo "superseded: $(count '{"exact":true,"filter":{"must":[{"key":"status","match":{"value":"superseded"}}]}}')"
superseded: 19
$ git status --porcelain backend/corpus
(prints nothing)
```

`count` is `curl -X POST http://127.0.0.1:6333/collections/policy_passages/points/count`.

**Tests:** `cd backend && python -m pytest tests/test_ingest.py` gives 12 passed. These cover
I1 to I11, run against an in-memory Qdrant with a fake embedder. Whole suite: 33 backend and
41 CI tests passed; ruff, bandit and the scope check are clean.

**D1 size cap (set at F1, from measured section lengths):** `CHUNK_SIZE=1200` characters. The
130 real sections run from 40 to 1,001 characters; the longest is Records Retention §4.1, and
the median is 217. 1,200 is the smallest round number that keeps every current section
whole, so the cap only applies to sections added later.

**Simplest options taken where the plan was silent:**
- `CHUNK_SIZE` is measured in characters.
- `EMBEDDING_TIMEOUT_SECONDS=5` is a new setting. The plan named no embedding timeout.
- Every `## N.` and `### N.N` heading starts a section. A `##` with no subsections (for
  example T&E §8) is its own section.
- The preamble before the first numbered heading (title, owner line, superseded banner) is
  not indexed. The document's status travels in each passage's payload instead.
- What gets embedded is the section heading ("4.2 Approval thresholds") followed by the
  passage text, per D1. The payload `text` is the passage alone.
- A failed run writes nothing, because every vector is computed before any write (I9). After
  a successful run, points for passages no longer in the corpus are deleted.
- The fixture for I2 is a modified copy of the corpus in a temporary folder, outside
  `backend/corpus/` (A14). There is no `tests/fixtures/` folder.
- Pins are in `backend/requirements*.txt`, not `pyproject.toml` (Task 0).
