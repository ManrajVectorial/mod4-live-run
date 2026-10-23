"""Load the documents at startup when the index is empty (deployment).

A fresh deployment starts with an empty Qdrant. Rather than a separate ingest step, the API
checks the index when it starts and, if it is empty, runs the F1 ingest in a background
thread. /healthz keeps answering 200 throughout and shows the progress and the passage
count, so the platform's health check passes while it indexes.
"""

import logging
import threading
from collections.abc import Callable
from pathlib import Path

from qdrant_client import QdrantClient

from app.embeddings import Embedder, OpenRouterEmbedder
from app.ingest import run_ingest
from app.settings import Settings, SettingsError, require

log = logging.getLogger("app.index")


class IndexStatus:
    """Thread-safe: written by the bootstrap thread, read by /healthz."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status = "not_checked"
        self._passages: int | None = None

    def set(self, status: str, passages: int | None) -> None:
        with self._lock:
            self._status, self._passages = status, passages

    def snapshot(self) -> dict:
        with self._lock:
            return {"status": self._status, "passages": self._passages}

    @property
    def ready(self) -> bool:
        return self.snapshot()["status"] in ("ready", "not_checked")


def count_passages(client: QdrantClient, collection: str) -> int:
    if not client.collection_exists(collection):
        return 0
    return client.count(collection, exact=True).count


def ingest_corpus(
    *,
    client: QdrantClient,
    collection: str,
    corpus_dir: Path,
    embedder: Embedder,
    embedding_model: str,
    dimensions: int,
    chunk_size: int,
    chunk_overlap: int,
) -> int:
    report = run_ingest(
        corpus_dir=corpus_dir,
        embedder=embedder,
        client=client,
        collection=collection,
        embedding_model=embedding_model,
        dimensions=dimensions,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return report.passages


def ensure_index(count: Callable[[], int], ingest: Callable[[], int], status: IndexStatus) -> None:
    """Count; if empty, ingest. Every failure is logged (by type) and shown on /healthz."""
    status.set("checking", None)
    try:
        existing = count()
        if existing > 0:
            status.set("ready", existing)
            log.info("index: %d passages already indexed", existing)
            return
        status.set("indexing", 0)
        log.info("index: empty; loading the documents in the background")
        loaded = ingest()
    except Exception as exc:  # never silent: logged by type, and failed on /healthz
        # Only the type: provider and connection messages can carry details.
        log.error("index: could not load the documents (%s)", type(exc).__name__)
        status.set("failed", 0)
        return
    status.set("ready", loaded)
    log.info("index: loaded %d passages", loaded)


def bootstrap_from_settings(settings: Settings, status: IndexStatus) -> None:
    """The real bootstrap, from .env / platform settings (used by `serve`)."""
    try:
        cfg = require(
            settings,
            "corpus_dir",
            "qdrant_url",
            "qdrant_collection",
            "openrouter_api_key",
            "openrouter_base_url",
            "embedding_model",
            "embedding_dimensions",
            "embedding_timeout_seconds",
            "chunk_size",
            "chunk_overlap",
        )
    except SettingsError as exc:
        log.error("index: not loaded. %s", exc)  # names the settings, never their values
        status.set("failed", 0)
        return
    api_key = settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None
    client = QdrantClient(url=cfg["qdrant_url"], api_key=api_key)
    embedder = OpenRouterEmbedder(
        api_key=cfg["openrouter_api_key"].get_secret_value(),
        base_url=cfg["openrouter_base_url"],
        model=cfg["embedding_model"],
        timeout=cfg["embedding_timeout_seconds"],
    )
    ensure_index(
        lambda: count_passages(client, cfg["qdrant_collection"]),
        lambda: ingest_corpus(
            client=client,
            collection=cfg["qdrant_collection"],
            corpus_dir=cfg["corpus_dir"],
            embedder=embedder,
            embedding_model=cfg["embedding_model"],
            dimensions=cfg["embedding_dimensions"],
            chunk_size=cfg["chunk_size"],
            chunk_overlap=cfg["chunk_overlap"],
        ),
        status,
    )
