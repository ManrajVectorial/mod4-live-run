# T1-F7 — Browse the documents *(optional)*

**Status:** done (2026-10-23). Automated checks below; you can look at the pages in a browser at http://127.0.0.1:3014/corpus
**Optional:** no. Every feature ships (product owner, 2026-10-23)
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

**Done-when, API on 8014 and production web build on 3014 (the Done-when line's `:3000` is now
`:3014`).** The pages render in the browser, so their data was checked through the web
app's proxy, and each page route was checked as served:

```
page /corpus                             HTTP 200
page /corpus/travel-expense-policy-v3.0  HTTP 200
page /corpus/no-such-document            HTTP 200   (the page renders "Document not found")
top bar links on /: Corpus

/api/corpus via proxy: 5 documents
  Client Onboarding and KYC Refresh Policy, v2.4  [current]  passages=26
  Outsourcing and Third-Party Risk Policy, v1.8  [current]  passages=28
  Records Retention and Data Handling Policy, v4.0  [current]  passages=26
  Travel and Expense Policy, v3.1  [current]  passages=31
  Travel and Expense Policy, v3.0  [superseded]  passages=19

/api/corpus/travel-expense-policy-v3.0: status=superseded, superseded_by=v3.1, superseded_on=2026-04-01, current_document_id=travel-expense-policy-v3.1

Q1 citation [1] links to /corpus/travel-expense-policy-v3.1#section-4.2; section 4.2 is on that page: True

unknown id via proxy: HTTP 404 {"error":{"code":"document_not_found","message":"That document isn't in the corpus."}}
```

On `/corpus/travel-expense-policy-v3.0` the page shows a red banner: "Superseded on 1 April
2026: this version is kept for reference only. The current version is v3.1", with a link to
`/corpus/travel-expense-policy-v3.1`. That's the `documentBanner` output, unit-tested below.
I haven't looked at it in a browser.

**The 13 questions after F7:** `eval 10/10 answered, 3/3 refused`.

**Tests:**
- Backend: `test_api_corpus.py` (4): A6, A7, B1, B2, B3 data and B5. Whole backend suite: 97
  passed.
- Frontend: 10 passed, including B4 (citation link), B3 and U17 (banner) and U14 (top-bar
  link).
- Other checks: ruff, bandit, licence and scope checks clean; 41 CI-script tests passed.

**Simplest options taken where the plan was silent:**
- The corpus pages read the documents back from Qdrant's passage payloads, so they show
  exactly what retrieval searches.
- Documents are listed by title, current versions first.
- The pages are client-rendered and use the same-origin proxy, like the ask page.
- An unknown id shows a "Document not found" page, with a link back to all documents (B5).
- Each citation has an "Open this section in the document" link, which jumps to and outlines
  the section.
