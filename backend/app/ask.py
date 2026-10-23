"""POST /api/ask: retrieve, gate, then answer or refuse (PRD §1, §5.1).

Order matters (ADR-001): validation, then retrieval, then the refusal rule, and only then
anything that could call a chat model. Every response, of any status, is recorded.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.citations import cited_markers, valid_citations
from app.conflicts import Conflict, conflict_note, find_conflict
from app.db import AssistantRecord, ConversationNotFound, Store
from app.generation import GenerationFailed, GenerationTimeout, Generator
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
    generation_enabled: bool = False
    conflicts: list[Conflict] = field(default_factory=list)


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
    generator: Generator | None = None,
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
    prompt_version = model = None
    tokens: tuple[int | None, int | None] = (None, None)
    if not clears(top, config.threshold):
        # The gate: refused before any chat-model call (REQ-R6).
        status, sources = "refused", []
        refusal = Refusal(reason="below_threshold", message=refusal_message())
    else:
        cleared = [h for h in retrieval.current if h.score > config.threshold]
        notes = earlier_versions(cleared, retrieval.superseded, config.threshold)
        markers = {h.passage_id: i for i, h in enumerate(cleared, start=1)}
        conflict = find_conflict(cleared, config.conflicts)
        note = conflict_note(conflict, markers) if conflict else None

        def all_sources() -> list[Source]:
            return [_source(i, h) for i, h in enumerate([*cleared, *notes], start=1)]

        if generator is None or not config.generation_enabled:
            status, sources = "degraded", all_sources()
            degraded = Degraded(reason="generation_disabled")
        else:
            try:
                result = generator.generate(question, cleared, note)
            except GenerationTimeout as exc:
                log.warning(
                    "ask request_id=%s generation timed out (%s)", request_id, type(exc).__name__
                )
                status, sources = "degraded", all_sources()
                degraded = Degraded(reason="provider_timeout")
            except GenerationFailed as exc:
                log.warning(
                    "ask request_id=%s generation failed (%s)", request_id, type(exc).__name__
                )
                status, sources = "degraded", all_sources()
                degraded = Degraded(reason="provider_error")
            else:
                prompt_version, model = result.prompt_version, result.model
                tokens = (result.prompt_tokens, result.completion_tokens)
                if not valid_citations(result.text, len(cleared)):
                    status, sources = "degraded", all_sources()
                    degraded = Degraded(reason="invalid_citations")
                else:
                    status = "answered"
                    answer = f"{result.text}\n\n{note}" if note else result.text
                    used = set(cited_markers(result.text))
                    if conflict:
                        used |= {markers[h.passage_id] for h in conflict}  # D6: both sides
                    chosen = [h for h in cleared if markers[h.passage_id] in used]
                    sources = [_source(markers[h.passage_id], h) for h in chosen]
                    policies = {h.payload["policy_id"] for h in chosen}
                    old = [h for h in notes if h.payload["policy_id"] in policies]
                    sources += [_source(len(cleared) + i, h) for i, h in enumerate(old, start=1)]

    message_id = uuid.uuid4()
    created_at = datetime.now(UTC)
    latency_ms = int((time.perf_counter() - started) * 1000)
    meta = Meta(
        prompt_version=prompt_version,
        model=model,
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
        "ask request_id=%s status=%s top_score=%s retrieved=%d latency_ms=%d "
        "prompt_tokens=%s completion_tokens=%s",
        request_id,
        status,
        "none" if top is None else f"{top:.3f}",
        meta.retrieved,
        latency_ms,
        tokens[0],
        tokens[1],
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
