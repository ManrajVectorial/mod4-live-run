# T1-F7 — Browse the documents *(optional)*

**Status:** todo
**Optional:** yes. Dropped from the back if time runs short (after F8)
**Parent:** [T1](T1.md)
**Depends on:** F5
**Decisions it waits on:** D4

`/corpus` and `/corpus/[id]`, with superseded documents labelled, citations linking to their
section, and a Corpus link in the top bar.

## Requirements

REQ-B1, B2, B3, B4, B5 · REQ-A6, A7 · REQ-U14

## Done when (from `features.md`)

Open `http://localhost:3000/corpus` and see five documents with v3.0 labelled superseded; open `/corpus/travel-expense-policy-v3.0` and see a banner linking to v3.1; click a citation on `/` and land on its section

## Command that checks it

```
cd backend && python -m pytest tests/test_api_corpus.py
cd frontend && npm run build && npm run dev
```

Then the manual check in the Done-when line, recorded below.

## Files it will touch

- `backend/app/main.py`: changed. Adds `GET /api/corpus` and `GET /api/corpus/{document_id}`
  (A6, A7)
- `backend/tests/test_api_corpus.py`: new
- `frontend/app/corpus/page.tsx`: new (B1)
- `frontend/app/corpus/[id]/page.tsx`: new. Includes the superseded banner and the
  not-found page (B2, B3, B5)
- `frontend/components/`: changed. Citations link to `/corpus/[id]#section` (B4)
- `frontend/app/layout.tsx`: changed. Adds the Corpus link (U14)

## Not in it

- Editing documents
- Document preview or PDF rendering
- History (F8)

## Evidence
