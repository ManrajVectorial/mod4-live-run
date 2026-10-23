"""Deployment: an API that starts with an empty index loads the documents in the background,
and /healthz shows the passage count, answering 200 throughout so the platform's health
check passes while it indexes. In-memory Qdrant and a fake embedder; no network."""

import logging
import threading

from fastapi.testclient import TestClient

from app.index_bootstrap import IndexStatus, count_passages, ensure_index, ingest_corpus
from app.main import create_app
from app.settings import REPO_ROOT
from tests.conftest import TEST_DIMENSIONS, FakeEmbedder

CORPUS = REPO_ROOT / "backend" / "corpus"
COLLECTION = "boot_passages"


def test_empty_index_is_loaded_and_counted(in_memory_vector_store):
    status = IndexStatus()
    calls = []

    def ingest() -> int:
        calls.append(1)
        return ingest_corpus(
            client=in_memory_vector_store,
            collection=COLLECTION,
            corpus_dir=CORPUS,
            embedder=FakeEmbedder(),
            embedding_model="fake-embedding",
            dimensions=TEST_DIMENSIONS,
            chunk_size=1200,
            chunk_overlap=0,
        )

    ensure_index(lambda: count_passages(in_memory_vector_store, COLLECTION), ingest, status)
    stored = count_passages(in_memory_vector_store, COLLECTION)
    assert calls == [1]
    assert stored > 0
    assert status.snapshot() == {"status": "ready", "passages": stored}


def test_a_filled_index_is_not_loaded_again():
    status = IndexStatus()
    ensure_index(lambda: 130, lambda: (_ for _ in ()).throw(AssertionError("no ingest")), status)
    assert status.snapshot() == {"status": "ready", "passages": 130}


def test_a_failed_load_is_reported_and_logged_by_type_only(caplog):
    caplog.set_level(logging.ERROR)
    status = IndexStatus()

    def ingest() -> int:
        raise RuntimeError("secret-ish detail that must not be logged")

    ensure_index(lambda: 0, ingest, status)
    assert status.snapshot() == {"status": "failed", "passages": 0}
    assert "RuntimeError" in caplog.text
    assert "secret-ish" not in caplog.text


def test_missing_collection_counts_as_empty(in_memory_vector_store):
    assert count_passages(in_memory_vector_store, "never_created") == 0


def test_healthz_answers_200_and_shows_progress_while_indexing(make_settings, healthy_probes):
    release = threading.Event()

    def bootstrap(settings, status: IndexStatus) -> None:
        ensure_index(lambda: 0, lambda: (release.wait(5), 42)[1], status)

    app = create_app(settings=make_settings(), probes=healthy_probes, index_bootstrap=bootstrap)
    with TestClient(app) as client:  # the context runs the startup hook
        during = client.get("/healthz")
        assert during.status_code == 200
        assert during.json()["index"] == {"status": "indexing", "passages": 0}
        assert during.json()["status"] == "degraded"  # not ready to answer yet
        release.set()
        for _ in range(50):
            body = client.get("/healthz").json()
            if body["index"]["status"] == "ready":
                break
            threading.Event().wait(0.05)
        assert body["index"] == {"status": "ready", "passages": 42}
        assert body["status"] == "ok"


def test_without_a_bootstrap_the_index_is_reported_unchecked(make_settings, healthy_probes):
    body = (
        TestClient(create_app(settings=make_settings(), probes=healthy_probes))
        .get("/healthz")
        .json()
    )
    assert body["index"] == {"status": "not_checked", "passages": None}


def test_the_container_starts_the_app_that_loads_the_index():
    dockerfile = (REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "app.main:serve" in dockerfile
