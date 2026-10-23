"""Index the corpus into Qdrant (F1).

    python -m app.ingest

Every vector is computed before anything is written, so a failed run leaves the previous
index searchable and unchanged (REQ-I9). The corpus is only ever read (REQ-I10).
"""

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from qdrant_client import QdrantClient

from app.chunking import split_passages
from app.corpus import CorpusError, load_corpus
from app.embeddings import Embedder, OpenRouterEmbedder
from app.settings import SettingsError, load_settings, require
from app.vector_store import ensure_collection, replace_passages


class IngestError(RuntimeError):
    """Ingestion stopped. Nothing was written."""


@dataclass(frozen=True)
class IngestReport:
    documents: int
    passages: int
    superseded_passages: int
    indexed_at: str


def run_ingest(
    *,
    corpus_dir: Path,
    embedder: Embedder,
    client: QdrantClient,
    collection: str,
    embedding_model: str,
    dimensions: int,
    chunk_size: int,
    chunk_overlap: int,
) -> IngestReport:
    try:
        documents = load_corpus(corpus_dir)
        passages = [p for d in documents for p in split_passages(d, chunk_size, chunk_overlap)]
    except (CorpusError, ValueError) as exc:
        raise IngestError(str(exc)) from exc

    try:
        vectors = embedder.embed([p.embedding_text for p in passages])
    except Exception as exc:  # any provider failure stops the run before writing
        raise IngestError(f"embedding failed ({type(exc).__name__}); nothing written") from exc
    if len(vectors) != len(passages):
        raise IngestError(f"embedder returned {len(vectors)} vectors for {len(passages)} passages")
    wrong = {len(v) for v in vectors if len(v) != dimensions}
    if wrong:
        raise IngestError(
            f"embedder returned vectors of length {sorted(wrong)}, but EMBEDDING_DIMENSIONS "
            f"is {dimensions}; nothing written"
        )

    indexed_at = datetime.now(UTC).isoformat(timespec="seconds")
    try:
        ensure_collection(client, collection, dimensions)
    except ValueError as exc:
        raise IngestError(str(exc)) from exc
    replace_passages(client, collection, passages, vectors, embedding_model, indexed_at)
    return IngestReport(
        documents=len(documents),
        passages=len(passages),
        superseded_passages=sum(p.document.status == "superseded" for p in passages),
        indexed_at=indexed_at,
    )


def main() -> int:
    try:
        settings = load_settings()
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
        print(exc, file=sys.stderr)
        return 2

    api_key = settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None
    client = QdrantClient(url=cfg["qdrant_url"], api_key=api_key)
    embedder = OpenRouterEmbedder(
        api_key=cfg["openrouter_api_key"].get_secret_value(),
        base_url=cfg["openrouter_base_url"],
        model=cfg["embedding_model"],
        timeout=cfg["embedding_timeout_seconds"],
    )
    try:
        report = run_ingest(
            corpus_dir=cfg["corpus_dir"],
            embedder=embedder,
            client=client,
            collection=cfg["qdrant_collection"],
            embedding_model=cfg["embedding_model"],
            dimensions=cfg["embedding_dimensions"],
            chunk_size=cfg["chunk_size"],
            chunk_overlap=cfg["chunk_overlap"],
        )
    except IngestError as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Indexed {report.documents} documents as {report.passages} passages "
        f"({report.superseded_passages} from superseded documents) into "
        f"{cfg['qdrant_collection']!r} at {report.indexed_at}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
