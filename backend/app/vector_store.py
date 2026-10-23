"""The Qdrant collection of passages and its payload (PRD §7; REQ-I5, I7, I8, I9, I11)."""

import hashlib
import uuid
from collections.abc import Sequence

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointIdsList, PointStruct, VectorParams

from app.chunking import Passage

# Point IDs are a UUIDv5 of passage_id, so re-ingesting unchanged text reuses the same IDs.
POINT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "policy-assistant/passages")


def point_id(passage_id: str) -> str:
    return str(uuid.uuid5(POINT_NAMESPACE, passage_id))


def payload(passage: Passage, embedding_model: str, indexed_at: str) -> dict:
    doc = passage.document
    return {
        "passage_id": passage.passage_id,
        "document_id": doc.document_id,
        "policy_id": doc.policy_id,
        "title": doc.title,
        "version": doc.version,
        "status": doc.status,
        "effective": doc.effective,
        "supersedes": doc.supersedes,
        "superseded_by": doc.superseded_by,
        "superseded_on": doc.superseded_on,
        "owner": doc.owner,
        "source_file": doc.source_file,
        "section": passage.section,
        "section_title": passage.section_title,
        "heading_path": list(passage.heading_path),
        "chunk_index": passage.chunk_index,
        "order": passage.order,
        "text": passage.text,
        "content_hash": hashlib.sha256(passage.text.encode("utf-8")).hexdigest(),
        "embedding_model": embedding_model,
        "indexed_at": indexed_at,
    }


def ensure_collection(client: QdrantClient, collection: str, dimensions: int) -> None:
    if client.collection_exists(collection):
        info = client.get_collection(collection)
        size = info.config.params.vectors.size  # type: ignore[union-attr]
        if size != dimensions:
            raise ValueError(
                f"collection {collection!r} holds {size}-dimension vectors, but "
                f"EMBEDDING_DIMENSIONS is {dimensions}; re-create it to change D0"
            )
        return
    client.create_collection(
        collection, vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE)
    )


def replace_passages(
    client: QdrantClient,
    collection: str,
    passages: Sequence[Passage],
    vectors: Sequence[list[float]],
    embedding_model: str,
    indexed_at: str,
) -> None:
    """Upsert every passage, then delete points that are no longer in the corpus."""
    points = [
        PointStruct(
            id=point_id(p.passage_id), vector=v, payload=payload(p, embedding_model, indexed_at)
        )
        for p, v in zip(passages, vectors, strict=True)
    ]
    client.upsert(collection, points=points, wait=True)
    keep = {str(p.id) for p in points}
    stale, offset = [], None
    while True:
        batch, offset = client.scroll(collection, limit=256, offset=offset, with_payload=False)
        stale += [p.id for p in batch if str(p.id) not in keep]
        if offset is None:
            break
    if stale:
        client.delete(collection, points_selector=PointIdsList(points=stale), wait=True)
