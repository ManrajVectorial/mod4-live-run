"""POST /api/ask: retrieve, gate, then answer or refuse (PRD §1, §5.1).

Order matters (ADR-001): validation, then retrieval, then the refusal rule, and only then
anything that could call a chat model. Every response, of any status, is recorded.
"""

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from app.db import AssistantRecord, ConversationNotFound, Store
from app.refusal import clears, refusal_message
from app.retrieval import Hit, Retrieval
from app.schemas import AskResponse, Degraded, Meta, Refusal, Source

log = logging.getLogger("app.ask")


class RetrieverLike(Protocol):
    def retrieve(self, text: str) -> Retrieval: ...


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(code)
        self.status, self.code, self.message = status, code, message


@dataclass(frozen=True)
class AskConfig:
    threshold: float
    max_question_chars: int


def _source(marker: int, hit: Hit) -> Source:
    p = hit.payload
    return Source(
        marker=marker,
        passage_id=p["passage_id"],
        document_id=p["document_id"],
        policy_id=p["policy_id"],
        title=p["title"],
        version=p["version"],
        status=p["status"],
        effective=p["effective"],
        superseded_by=p["superseded_by"],
        section=p["section"],
        section_title=p["section_title"],
        text=p["text"],
        score=float(hit.score),
    )


def earlier_versions(current: list[Hit], superseded: list[Hit], threshold: float) -> list[Hit]:
    """D4: superseded passages appear only as labelled notes beside the current version of
    the same policy, and never reach the model."""
    policies = {h.payload["policy_id"] for h in current}
    return [h for h in superseded if h.score > threshold and h.payload["policy_id"] in policies]


def _parse_conversation(raw: str | None, store: Store) -> uuid.UUID | None:
    if raw is None:
        return None
    try:
        conversation_id = uuid.UUID(raw)
    except ValueError:
        conversation_id = None
    if conversation_id is None or not store.conversation_exists(conversation_id):
        raise ApiError(404, "conversation_not_found", "That conversation doesn't exist.")
    return conversation_id


def validate_question(question: object, max_chars: int) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ApiError(422, "question_blank", "Enter a question.")
    if len(question) > max_chars:
        raise ApiError(422, "question_too_long", f"Keep the question under {max_chars} characters.")
    return question.strip()


def handle_ask(
    question_raw: object,
    conversation_raw: str | None,
    retriever: RetrieverLike,
    store: Store,
    config: AskConfig,
) -> AskResponse:
    started = time.perf_counter()
    request_id = uuid.uuid4().hex[:12]
    question = validate_question(question_raw, config.max_question_chars)
    conversation_id = _parse_conversation(conversation_raw, store)

    retrieval = retriever.retrieve(question)
    top = retrieval.top_current_score
    stamps = [h.payload["indexed_at"] for h in retrieval.hits if h.payload.get("indexed_at")]
    indexed_at = datetime.fromisoformat(max(stamps)) if stamps else None

    answer = refusal = degraded = None
    if not clears(top, config.threshold):
        status, sources = "refused", []
        refusal = Refusal(reason="below_threshold", message=refusal_message())
    else:
        cleared = [h for h in retrieval.current if h.score > config.threshold]
        notes = earlier_versions(cleared, retrieval.superseded, config.threshold)
        status = "degraded"
        degraded = Degraded(reason="generation_disabled")
        sources = [_source(i, h) for i, h in enumerate([*cleared, *notes], start=1)]

    message_id = uuid.uuid4()
    created_at = datetime.now(UTC)
    latency_ms = int((time.perf_counter() - started) * 1000)
    meta = Meta(
        prompt_version=None,
        model=None,
        top_score=top,
        threshold=config.threshold,
        retrieved=len(retrieval.hits),
        corpus_indexed_at=indexed_at,
        latency_ms=latency_ms,
    )
    record = AssistantRecord(
        message_id=message_id,
        status=status,
        content=answer,
        refusal_reason=refusal.reason if refusal else None,
        refusal_message=refusal.message if refusal else None,
        degraded_reason=degraded.reason if degraded else None,
        prompt_version=meta.prompt_version,
        model=meta.model,
        top_score=top,
        threshold=config.threshold,
        retrieved=meta.retrieved,
        corpus_indexed_at=indexed_at,
        latency_ms=latency_ms,
        created_at=created_at,
        citations=[
            s.model_dump(
                include={
                    "marker",
                    "passage_id",
                    "document_id",
                    "policy_id",
                    "title",
                    "version",
                    "status",
                    "section",
                    "section_title",
                    "score",
                    "text",
                }
            )
            for s in sources
        ],
    )
    try:
        conversation_id = store.record(conversation_id, question, record)
    except ConversationNotFound as exc:
        raise ApiError(404, "conversation_not_found", "That conversation doesn't exist.") from exc

    log.info(
        "ask request_id=%s status=%s top_score=%s retrieved=%d latency_ms=%d",
        request_id,
        status,
        "none" if top is None else f"{top:.3f}",
        meta.retrieved,
        latency_ms,
    )
    return AskResponse(
        status=status,
        conversation_id=conversation_id,
        message_id=message_id,
        answer=answer,
        refusal=refusal,
        degraded=degraded,
        sources=sources,
        meta=meta,
        created_at=created_at,
    )
