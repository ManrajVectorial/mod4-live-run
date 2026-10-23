"""Read the indexed corpus back out of Qdrant for browsing (F7; PRD §5.2, §5.3).

Built from the passage payloads (PRD §7), so the corpus pages show exactly what retrieval
searches, superseded documents included and labelled (REQ-I7, B1, B3).
"""

from collections.abc import Iterator

from qdrant_client import QdrantClient

DOCUMENT_FIELDS = (
    "document_id",
    "policy_id",
    "title",
    "version",
    "status",
    "effective",
    "owner",
    "supersedes",
    "superseded_by",
    "superseded_on",
)


class DocumentNotFound(LookupError):
    pass


class CorpusIndex:
    def __init__(self, client: QdrantClient, collection: str) -> None:
        self.client = client
        self.collection = collection

    def _payloads(self) -> Iterator[dict]:
        offset = None
        while True:
            batch, offset = self.client.scroll(
                self.collection, limit=256, offset=offset, with_payload=True, with_vectors=False
            )
            for point in batch:
                yield dict(point.payload or {})
            if offset is None:
                return

    def documents(self) -> list[dict]:
        found: dict[str, dict] = {}
        for p in self._payloads():
            doc = found.setdefault(
                p["document_id"],
                {
                    **{f: p.get(f) for f in DOCUMENT_FIELDS},
                    "passage_count": 0,
                    "indexed_at": p.get("indexed_at"),
                },
            )
            doc["passage_count"] += 1
            doc["indexed_at"] = max(doc["indexed_at"] or "", p.get("indexed_at") or "") or None
        # Current versions first within a policy, then by title.
        return sorted(
            found.values(), key=lambda d: (d["title"], d["status"] != "current", d["version"])
        )

    def document(self, document_id: str) -> dict:
        docs = {d["document_id"]: d for d in self.documents()}
        if document_id not in docs:
            raise DocumentNotFound(document_id)
        doc = docs[document_id]
        current = next(
            (
                d["document_id"]
                for d in docs.values()
                if d["policy_id"] == doc["policy_id"] and d["status"] == "current"
            ),
            document_id,
        )
        passages = sorted(
            (p for p in self._payloads() if p["document_id"] == document_id),
            key=lambda p: p["order"],
        )
        sections: list[dict] = []
        for p in passages:
            if not sections or sections[-1]["section"] != p["section"]:
                sections.append(
                    {
                        "section": p["section"],
                        "section_title": p["section_title"],
                        "heading_path": p["heading_path"],
                        "passages": [],
                    }
                )
            sections[-1]["passages"].append({"passage_id": p["passage_id"], "text": p["text"]})
        return {"document": doc, "current_document_id": current, "sections": sections}
