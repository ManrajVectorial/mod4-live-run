"""Search the indexed passages (F2; REQ-R1 to R3).

The question is embedded with the same model as the passages and the RETRIEVAL_TOP_K most
similar passages come back, highest score first, ties broken by passage_id so the same
question always gives the same order. Every hit keeps its document status. D4: only
current passages reach the model; superseded ones are kept apart for "earlier version" notes.
"""

from dataclasses import dataclass, field

from qdrant_client import QdrantClient

from app.embeddings import Embedder


@dataclass(frozen=True)
class Hit:
    score: float
    payload: dict

    @property
    def passage_id(self) -> str:
        return self.payload["passage_id"]


@dataclass(frozen=True)
class Retrieval:
    hits: list[Hit]
    current: list[Hit] = field(default_factory=list)
    superseded: list[Hit] = field(default_factory=list)

    @property
    def top_current_score(self) -> float | None:
        return self.current[0].score if self.current else None


class Retriever:
    def __init__(
        self, client: QdrantClient, collection: str, embedder: Embedder, top_k: int
    ) -> None:
        self.client = client
        self.collection = collection
        self.embedder = embedder
        self.top_k = top_k

    def search(self, text: str) -> list[Hit]:
        (vector,) = self.embedder.embed([text])
        response = self.client.query_points(
            self.collection, query=vector, limit=self.top_k, with_payload=True
        )
        hits = [Hit(score=float(p.score), payload=dict(p.payload or {})) for p in response.points]
        return sorted(hits, key=lambda h: (-h.score, h.passage_id))

    def retrieve(self, text: str) -> Retrieval:
        hits = self.search(text)
        return Retrieval(
            hits=hits,
            current=[h for h in hits if h.payload.get("status") == "current"],
            superseded=[h for h in hits if h.payload.get("status") == "superseded"],
        )
