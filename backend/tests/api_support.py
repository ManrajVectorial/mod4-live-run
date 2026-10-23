"""Builders for API tests: a stub retriever with fixed scores, an in-memory store."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.db import Store
from app.main import Services, create_app
from app.retrieval import Hit, Retrieval

THRESHOLD = 0.5
INDEXED_AT = "2026-10-23T00:00:00+00:00"


def passage(document_id, section, score, status="current", **extra):
    policy_id, _, version = document_id.rpartition("-v")
    payload = {
        "passage_id": f"{document_id}:{section}:0",
        "document_id": document_id,
        "policy_id": policy_id,
        "title": extra.pop("title", "Travel and Expense Policy"),
        "version": version,
        "status": status,
        "effective": "2026-04-01",
        "supersedes": None,
        "superseded_by": "3.1" if status == "superseded" else None,
        "superseded_on": "2026-04-01" if status == "superseded" else None,
        "owner": "Group Finance",
        "source_file": f"{document_id}.md",
        "section": section,
        "section_title": extra.pop("section_title", "Approval thresholds"),
        "heading_path": ["4. Approval", f"{section} Approval thresholds"],
        "chunk_index": 0,
        "order": 0,
        "text": extra.pop("text", f"Text of {document_id} §{section}."),
        "content_hash": "x",
        "embedding_model": "fake-embedding",
        "indexed_at": INDEXED_AT,
    }
    return Hit(score=score, payload=payload)


class StubRetriever:
    """Returns fixed hits; records every text it was asked to search."""

    def __init__(self, hits) -> None:
        self.hits = sorted(hits, key=lambda h: (-h.score, h.passage_id))
        self.texts: list[str] = []

    def retrieve(self, text: str) -> Retrieval:
        self.texts.append(text)
        return Retrieval(
            hits=self.hits,
            current=[h for h in self.hits if h.payload["status"] == "current"],
            superseded=[h for h in self.hits if h.payload["status"] == "superseded"],
        )


class SpyGenerator:
    """Counts chat-model calls. F3 never calls it; F4 wires it in."""

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("the chat model must not be called here")


def memory_store() -> Store:
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    return Store(engine)


ANSWERABLE = [
    passage("travel-expense-policy-v3.1", "4.2", 0.72),
    passage("travel-expense-policy-v3.1", "4.1", 0.64, section_title="General principle"),
    passage("travel-expense-policy-v3.0", "4.1", 0.66, status="superseded"),
    passage("travel-expense-policy-v3.1", "2.4", 0.31, section_title="Transparency"),
]
UNANSWERABLE = [
    passage("travel-expense-policy-v3.1", "6.3", 0.27, section_title="Subsistence"),
    passage(
        "records-retention-v4.0",
        "4.1",
        0.25,
        title="Records Retention",
        section_title="General table",
    ),
]


def make_client(
    make_settings, hits, store=None, generator=None, retriever=None, corpus=None, **settings
):
    values = {"refusal_threshold": THRESHOLD, "max_question_chars": 500, **settings}
    services = Services(
        retriever=retriever or StubRetriever(hits),
        store=store or memory_store(),
        generator=generator,
        corpus=corpus,
    )
    app = create_app(settings=make_settings(**values), probes=None, services=services)
    return TestClient(app, raise_server_exceptions=False), services
