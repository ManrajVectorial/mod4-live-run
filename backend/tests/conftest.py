"""Shared fixtures. Nothing here touches the network or reads the real .env.

- an in-memory vector store (qdrant-client's local mode)
- an in-memory database (SQLite, which SQLAlchemy supports with no extra library)
- a fake model that answers, and a failing model that raises
- a fake embedder: deterministic bag-of-words vectors, so similar text scores similarly
"""

import hashlib
import math
import re
import time
from collections.abc import Iterator

import pytest
from qdrant_client import QdrantClient
from sqlalchemy import create_engine

from app.health import DatabaseProbe, Probes, VectorStoreProbe
from app.settings import Settings, load_settings


class FakeModel:
    """Stands in for the model provider: every check succeeds."""

    def __init__(self) -> None:
        self.calls = 0

    def check(self) -> None:
        self.calls += 1


class FailingModel:
    """Stands in for an unavailable model provider."""

    def check(self) -> None:
        raise ConnectionError("model provider unavailable (test fake)")


class FailingProbe:
    def check(self) -> None:
        raise ConnectionError("dependency down (test fake)")


class SlowProbe:
    def __init__(self, seconds: float) -> None:
        self.seconds = seconds

    def check(self) -> None:
        time.sleep(self.seconds)


TEST_DIMENSIONS = 64


class FakeEmbedder:
    """Hashes each word into one of `dimensions` buckets and normalises: shared words, high
    cosine similarity. Deterministic across runs, and never calls the network."""

    def __init__(self, dimensions: int = TEST_DIMENSIONS) -> None:
        self.dimensions = dimensions
        self.calls = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [self._vector(t) for t in texts]

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for word in re.findall(r"[a-z0-9£]+", text.lower()):
            bucket = int(hashlib.sha256(word.encode()).hexdigest(), 16) % self.dimensions
            vector[bucket] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


class FailingEmbedder:
    """Stands in for an embedding provider that fails part-way through."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise ConnectionError("embedding provider failed (test fake)")


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def make_settings():
    def _make(**overrides) -> Settings:
        values = {
            "generation_enabled": True,
            "healthz_timeout_seconds": 0.5,
            # The API refuses to start without these (REQ-R7, REQ-A3).
            "refusal_threshold": 0.5,
            "max_question_chars": 500,
            "conversation_context_messages": 5,  # D8
            "history_enabled": True,  # FND-9: required at startup, no default in code
            **overrides,
        }
        return load_settings(_env_file=None, **values)

    return _make


@pytest.fixture
def in_memory_vector_store() -> Iterator[QdrantClient]:
    client = QdrantClient(":memory:")
    yield client
    client.close()


@pytest.fixture
def in_memory_database() -> DatabaseProbe:
    return DatabaseProbe(create_engine("sqlite://"))


@pytest.fixture
def fake_model() -> FakeModel:
    return FakeModel()


@pytest.fixture
def failing_model() -> FailingModel:
    return FailingModel()


@pytest.fixture
def healthy_probes(in_memory_database, in_memory_vector_store, fake_model) -> Probes:
    return Probes(
        postgres=in_memory_database,
        qdrant=VectorStoreProbe(in_memory_vector_store),
        generation=fake_model,
    )
