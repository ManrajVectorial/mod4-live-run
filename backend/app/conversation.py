"""The conversation so far, as the models see it (F6; D8: the last 5 messages, questions
and answers counted separately). Used for the follow-up rewrite and for the answer."""

import re
import uuid

from app.db import Message, Store

MARKER = re.compile(r"\s*\[\d+\]")
NO_ANSWER = "No answer was composed; only policy passages were shown."


def as_context(message: Message) -> dict:
    if message.role == "user":
        return {"role": "user", "content": message.content or ""}
    if message.status == "answered":
        # Old markers point at old passages; drop them so they can't be cited again.
        text = MARKER.sub("", message.content or "")
    elif message.status == "refused":
        text = message.refusal_message or ""
    else:
        text = NO_ANSWER
    return {"role": "assistant", "content": text}


def context_for(store: Store, conversation_id: uuid.UUID | None, messages: int) -> list[dict]:
    if conversation_id is None or messages <= 0:
        return []
    return [as_context(m) for m in store.recent_messages(conversation_id, messages)]
