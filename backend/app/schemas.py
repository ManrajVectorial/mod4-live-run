"""Response shapes from PRD §5.1 and §5.7. Unknown fields are refused, so the API can't
drift from the contract without a test noticing."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(Strict):
    marker: int
    passage_id: str
    document_id: str
    policy_id: str
    title: str
    version: str
    status: Literal["current", "superseded"]
    effective: str
    superseded_by: str | None
    section: str
    section_title: str
    text: str
    score: float


class Refusal(Strict):
    reason: Literal["below_threshold"]
    message: str


class Degraded(Strict):
    reason: Literal[
        "generation_disabled", "provider_error", "provider_timeout", "invalid_citations"
    ]


class Meta(Strict):
    prompt_version: str | None
    model: str | None
    top_score: float | None
    threshold: float
    retrieved: int
    corpus_indexed_at: datetime | None
    latency_ms: int


class AskResponse(Strict):
    status: Literal["answered", "refused", "degraded"]
    conversation_id: UUID
    message_id: UUID
    answer: str | None
    refusal: Refusal | None
    degraded: Degraded | None
    sources: list[Source]
    meta: Meta
    created_at: datetime


class ErrorBody(Strict):
    code: str
    message: str


class ErrorResponse(Strict):
    error: ErrorBody
