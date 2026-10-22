# T1-F8 — History *(optional)*

**Status:** todo
**Optional:** yes. First to be dropped if time runs short
**Blocked by:** brief Q3 (who may see a user's question). Not started until Q3 is answered (A33)
**Parent:** [T1](T1.md)
**Depends on:** F6
**Decisions it waits on:** none of D0–D9

`/history`: past conversations newest first, each reopening with the citations stored at
answer time, and a History link in the top bar.

## Requirements

REQ-C7, C8 · REQ-A8, A9 · REQ-U15

## Done when (from `features.md`)

After the F6 run, `curl -s localhost:8000/api/conversations` lists that conversation first, and opening it at `http://localhost:3000/history` shows the same answers and citations as were shown originally

## Command that checks it

```
cd backend && python -m pytest tests/test_api_conversations.py
cd frontend && npm run build && npm run dev
```

Then the manual check in the Done-when line, recorded below.

## Files it will touch

- `backend/app/main.py`: changed. Adds `GET /api/conversations` and
  `GET /api/conversations/{id}` (A8, A9)
- `backend/tests/test_api_conversations.py`: new
- `frontend/app/history/page.tsx`: new (C7, C8)
- `frontend/app/layout.tsx`: changed. Adds the History link (U15)

## Not in it

- Authentication or per-user filtering
- Retention or deletion policy (brief Q2 and Q3, owned outside the team)
- Re-running retrieval for past answers: C8 shows the stored citations

## Evidence
