"""Postgres record of every exchange (PRD §6; REQ-C1, C2). Tables are created with
create_all on first use: the plan has no migration tool."""

import threading
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Engine,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "seq"),
        CheckConstraint(
            "status IS NULL OR status <> 'answered' OR "
            "(prompt_version IS NOT NULL AND model IS NOT NULL)",
            name="answered_records_prompt_and_model",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    seq: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    refusal_reason: Mapped[str | None] = mapped_column(Text)
    refusal_message: Mapped[str | None] = mapped_column(Text)
    degraded_reason: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    top_score: Mapped[float | None] = mapped_column(Float)
    threshold: Mapped[float | None] = mapped_column(Float)
    retrieved: Mapped[int | None] = mapped_column(Integer)
    corpus_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"))
    marker: Mapped[int] = mapped_column(Integer)
    passage_id: Mapped[str] = mapped_column(Text)
    document_id: Mapped[str] = mapped_column(Text)
    policy_id: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)  # document status at answer time
    section: Mapped[str] = mapped_column(Text)
    section_title: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)  # as shown, so history survives a re-index


@dataclass(frozen=True)
class AssistantRecord:
    message_id: uuid.UUID
    status: str
    content: str | None
    refusal_reason: str | None
    refusal_message: str | None
    degraded_reason: str | None
    prompt_version: str | None
    model: str | None
    top_score: float | None
    threshold: float
    retrieved: int
    corpus_indexed_at: datetime | None
    latency_ms: int
    created_at: datetime
    citations: Sequence[dict]


class ConversationNotFound(LookupError):
    pass


class Store:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._ready = False
        self._lock = threading.Lock()

    def _ensure_schema(self) -> None:
        if not self._ready:
            with self._lock:
                if not self._ready:
                    Base.metadata.create_all(self.engine)
                    self._ready = True

    @contextmanager
    def session(self) -> Iterator[Session]:
        self._ensure_schema()
        with Session(self.engine) as session:
            yield session

    def recent_messages(self, conversation_id: uuid.UUID, limit: int) -> list[Message]:
        """The last `limit` messages (questions and answers counted separately), oldest first."""
        with self.session() as s:
            rows = s.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.seq.desc())
                .limit(limit)
            ).all()
            s.expunge_all()
        return list(reversed(rows))

    def conversation_exists(self, conversation_id: uuid.UUID) -> bool:
        with self.session() as s:
            return s.get(Conversation, conversation_id) is not None

    def record(
        self, conversation_id: uuid.UUID | None, question: str, reply: AssistantRecord
    ) -> uuid.UUID:
        """Store the question and the reply (any status) in one transaction."""
        with self.session() as s, s.begin():
            if conversation_id is None:
                conversation = Conversation(
                    id=uuid.uuid4(), created_at=reply.created_at, updated_at=reply.created_at
                )
                s.add(conversation)
                next_seq = 1
            else:
                conversation = s.get(Conversation, conversation_id)
                if conversation is None:
                    raise ConversationNotFound(str(conversation_id))
                conversation.updated_at = reply.created_at
                last = s.scalar(
                    select(func.max(Message.seq)).where(Message.conversation_id == conversation_id)
                )
                next_seq = (last or 0) + 1
            s.add(
                Message(
                    id=uuid.uuid4(),
                    conversation_id=conversation.id,
                    seq=next_seq,
                    role="user",
                    content=question,
                    created_at=reply.created_at,
                )
            )
            s.add(
                Message(
                    id=reply.message_id,
                    conversation_id=conversation.id,
                    seq=next_seq + 1,
                    role="assistant",
                    content=reply.content,
                    status=reply.status,
                    refusal_reason=reply.refusal_reason,
                    refusal_message=reply.refusal_message,
                    degraded_reason=reply.degraded_reason,
                    prompt_version=reply.prompt_version,
                    model=reply.model,
                    top_score=reply.top_score,
                    threshold=reply.threshold,
                    retrieved=reply.retrieved,
                    corpus_indexed_at=reply.corpus_indexed_at,
                    latency_ms=reply.latency_ms,
                    created_at=reply.created_at,
                )
            )
            s.flush()
            for c in reply.citations:
                s.add(Citation(message_id=reply.message_id, **c))
            return conversation.id
