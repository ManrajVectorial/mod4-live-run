# T1-F6 — Follow-up questions *(optional)*

**Status:** todo
**Optional:** yes. Dropped from the back if time runs short (after F8 and F7)
**Parent:** [T1](T1.md)
**Depends on:** F5
**Decisions it waits on:** D8, D9

Continue a conversation: context per D8, retrieval per D9, the refusal rule on every turn, and
Reset starting afresh.

## Requirements

REQ-C3, C4, C5, C6

## Done when (from `features.md`)

`curl` Q1 to `/api/ask` and keep its `conversation_id`; sending `"And does a claim of exactly that amount need it?"` with that ID prints `"status":"answered"` citing v3.1 §4.2, then `"Can I expense my partner's flight?"` with the same ID prints `"status":"refused"`

## Command that checks it

```
cd backend && python -m pytest tests/test_conversation.py
```

Then run the Done-when sequence above.

## Files it will touch

- `backend/app/conversation.py`: new. Loads earlier turns per D8 and builds the follow-up
  retrieval query per D9 (C4, C5)
- `backend/app/main.py`: changed. Accepts `conversation_id`, returns 404 for unknown IDs (C3)
- `frontend/app/page.tsx`: changed. Keeps `conversation_id` across turns, and Reset drops it (C6)
- `backend/tests/test_conversation.py`: new

## Not in it

- Viewing past conversations (F8)
- Any chat-model call before the refusal rule (REQ-R6 still holds)
- Choosing D8 or D9

## Evidence
