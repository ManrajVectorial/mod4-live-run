"""Shared fixtures. Nothing here touches the network or reads the real .env.

- an in-memory vector store (qdrant-client's local mode)
- an in-memory database (SQLite, which SQLAlchemy supports with no extra library)
- a fake model that answers, and a failing model that raises
"""

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


@pytest.fixture
def make_settings():
    def _make(**overrides) -> Settings:
        values = {"generation_enabled": True, "healthz_timeout_seconds": 0.5, **overrides}
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
