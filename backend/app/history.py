"""F8 — history (PRD §5.4, §5.5; REQ-A8, A9, C7, C8).

History reads only what was stored at answer time: it never re-runs retrieval or the model,
so a conversation shows the same answer and citations after the corpus is re-indexed.
"""

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select

from app.db import Citation, Conversation, Message, Store


class HistoryNotFound(LookupError):
    pass


def _utc(value: datetime | None) -> datetime | None:
    # SQLite (tests) drops the zone that Postgres keeps; both were written in UTC.
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def list_conversations(store: Store) -> list[dict]:
    """Newest first (§5.4): a follow-up moves its conversation to the top."""
    with store.session() as s:
        conversations = s.scalars(
            select(Conversation).order_by(
                Conversation.updated_at.desc(), Conversation.created_at.desc()
            )
        ).all()
        messages = s.scalars(select(Message).order_by(Message.conversation_id, Message.seq)).all()
        by_conversation: dict[uuid.UUID, list[Message]] = defaultdict(list)
        for m in messages:
            by_conversation[m.conversation_id].append(m)
        rows = []
        for c in conversations:
            own = by_conversation[c.id]
            rows.append(
                {
                    "conversation_id": c.id,
                    "created_at": _utc(c.created_at),
                    "updated_at": _utc(c.updated_at),
                    "first_question": next((m.content for m in own if m.role == "user"), None),
                    "message_count": len(own),
                    "statuses": [m.status for m in own if m.role == "assistant"],
                }
            )
        return rows


def _source(c: Citation) -> dict:
    # Only the fields stored at answer time (PRD §6): `effective` and `superseded_by` are
    # not in the citation snapshot, so history leaves them out rather than look them up.
    return {
        "marker": c.marker,
        "passage_id": c.passage_id,
        "document_id": c.document_id,
        "policy_id": c.policy_id,
        "title": c.title,
        "version": c.version,
        "status": c.status,
        "section": c.section,
        "section_title": c.section_title,
        "score": c.score,
        "text": c.text,
    }


def _message(m: Message, citations: list[Citation]) -> dict:
    if m.role == "user":
        return {
            "message_id": m.id,
            "role": "user",
            "content": m.content,
            "created_at": _utc(m.created_at),
        }
    return {
        "message_id": m.id,
        "role": "assistant",
        "status": m.status,
        "answer": m.content,
        "refusal": (
            {"reason": m.refusal_reason, "message": m.refusal_message} if m.refusal_reason else None
        ),
        "degraded": {"reason": m.degraded_reason} if m.degraded_reason else None,
        "sources": [_source(c) for c in sorted(citations, key=lambda c: c.marker)],
        "meta": {
            "prompt_version": m.prompt_version,
            "model": m.model,
            "top_score": m.top_score,
            "threshold": m.threshold,
            "retrieved": m.retrieved,
            "corpus_indexed_at": _utc(m.corpus_indexed_at),
            "latency_ms": m.latency_ms,
        },
        "created_at": _utc(m.created_at),
    }


def conversation_detail(store: Store, raw_id: str) -> dict:
    try:
        conversation_id = uuid.UUID(raw_id)
    except ValueError as exc:
        raise HistoryNotFound(raw_id) from exc
    with store.session() as s:
        conversation = s.get(Conversation, conversation_id)
        if conversation is None:
            raise HistoryNotFound(raw_id)
        messages = s.scalars(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.seq)
        ).all()
        ids = [m.id for m in messages if m.role == "assistant"]
        by_message: dict[uuid.UUID, list[Citation]] = defaultdict(list)
        if ids:
            for c in s.scalars(select(Citation).where(Citation.message_id.in_(ids))).all():
                by_message[c.message_id].append(c)
        return {
            "conversation_id": conversation.id,
            "created_at": _utc(conversation.created_at),
            "messages": [_message(m, by_message[m.id]) for m in messages],
        }
