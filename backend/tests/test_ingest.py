"""F1 — Load the documents (REQ-I1 to I11). Real corpus, read only; in-memory Qdrant."""

import hashlib
import shutil

import pytest

from app.chunking import split_passages
from app.corpus import CorpusError, Document, load_corpus
from app.ingest import IngestError, run_ingest
from app.settings import REPO_ROOT
from tests.conftest import TEST_DIMENSIONS, FailingEmbedder, FakeEmbedder

CORPUS = REPO_ROOT / "backend" / "corpus"
COLLECTION = "test_passages"
MANIFEST_FILES = {
    "travel-expense-policy-v3.1.md",
    "travel-expense-policy-v3.0.md",
    "client-onboarding-kyc-v2.4.md",
    "records-retention-v4.0.md",
    "outsourcing-third-party-v1.8.md",
}
PRD_PAYLOAD_FIELDS = {  # PRD §7
    "passage_id",
    "document_id",
    "policy_id",
    "title",
    "version",
    "status",
    "effective",
    "supersedes",
    "superseded_by",
    "superseded_on",
    "owner",
    "source_file",
    "section",
    "section_title",
    "heading_path",
    "chunk_index",
    "order",
    "text",
    "content_hash",
    "embedding_model",
    "indexed_at",
}
CHUNK_SIZE = 4000  # large enough that no real section is split in these tests


def ingest(client, embedder=None, corpus=CORPUS, chunk_size=CHUNK_SIZE):
    return run_ingest(
        corpus_dir=corpus,
        embedder=embedder or FakeEmbedder(),
        client=client,
        collection=COLLECTION,
        embedding_model="fake-embedding",
        dimensions=TEST_DIMENSIONS,
        chunk_size=chunk_size,
        chunk_overlap=0,
    )


def all_points(client):
    points, _ = client.scroll(COLLECTION, limit=10_000, with_payload=True)
    return {str(p.id): p.payload for p in points}


def test_indexes_exactly_the_manifest_documents(in_memory_vector_store):
    report = ingest(in_memory_vector_store)
    files = {p["source_file"] for p in all_points(in_memory_vector_store).values()}
    assert report.documents == 5
    assert files == MANIFEST_FILES  # EVALUATION.md, FICTION-AUDIT.md, MANIFEST.yaml excluded


def test_front_matter_mismatch_names_the_file(tmp_path):
    corpus = tmp_path / "corpus"
    shutil.copytree(CORPUS, corpus)  # a modified copy, outside backend/corpus
    target = corpus / "records-retention-v4.0.md"
    target.write_text(
        target.read_text(encoding="utf-8").replace('version: "4.0"', 'version: "4.1"', 1),
        encoding="utf-8",
    )
    with pytest.raises(CorpusError, match="records-retention-v4.0.md"):
        load_corpus(corpus)


def test_passages_never_span_two_sections(in_memory_vector_store):
    ingest(in_memory_vector_store)
    for payload in all_points(in_memory_vector_store).values():
        assert "\n## " not in payload["text"] and "\n### " not in payload["text"]
    approval = next(
        p
        for p in all_points(in_memory_vector_store).values()
        if p["document_id"] == "travel-expense-policy-v3.1" and p["section"] == "4.2"
    )
    assert "£2,500 or more" in approval["text"]  # the whole table, in one passage
    assert "4.3" not in approval["section"]


def test_long_section_splits_at_paragraphs_and_keeps_table_whole():
    body = (
        "### 9.1 Long section\n\n"
        + "First paragraph. " * 20
        + "\n\n"
        + "| a | b |\n|---|---|\n"
        + "".join(f"| row {i} | value {i} |\n" for i in range(30))
        + "\n"
        + "Last paragraph. " * 20
        + "\n"
    )
    doc = Document(
        document_id="x-v1",
        policy_id="x",
        title="X",
        version="1",
        status="current",
        effective="2026-01-01",
        supersedes=None,
        superseded_by=None,
        superseded_on=None,
        owner="Owner",
        source_file="x.md",
        body=body,
    )
    passages = split_passages(doc, chunk_size=400, chunk_overlap=0)
    assert len(passages) == 3
    table = [p for p in passages if "| row 0 |" in p.text]
    assert len(table) == 1 and "| row 29 |" in table[0].text  # table never split
    assert [p.chunk_index for p in passages] == [0, 1, 2]
    assert all(p.section == "9.1" for p in passages)


def test_passage_records_section_number_and_title(in_memory_vector_store):
    ingest(in_memory_vector_store)
    payloads = {p["passage_id"]: p for p in all_points(in_memory_vector_store).values()}
    passage = payloads["travel-expense-policy-v3.1:4.2:0"]
    assert passage["section"] == "4.2"
    assert passage["section_title"] == "Approval thresholds"
    assert passage["heading_path"] == ["4. Approval", "4.2 Approval thresholds"]


def test_every_payload_has_the_prd_fields(in_memory_vector_store):
    ingest(in_memory_vector_store)
    for payload in all_points(in_memory_vector_store).values():
        assert set(payload) == PRD_PAYLOAD_FIELDS


def test_wrong_vector_length_stops_ingestion(in_memory_vector_store):
    with pytest.raises(IngestError, match="EMBEDDING_DIMENSIONS"):
        ingest(in_memory_vector_store, embedder=FakeEmbedder(dimensions=TEST_DIMENSIONS + 1))


def test_superseded_document_indexed_with_status(in_memory_vector_store):
    ingest(in_memory_vector_store)
    old = [p for p in all_points(in_memory_vector_store).values() if p["version"] == "3.0"]
    assert old
    assert {(p["status"], p["superseded_by"], p["superseded_on"]) for p in old} == {
        ("superseded", "3.1", "2026-04-01")
    }
    current = [p for p in all_points(in_memory_vector_store).values() if p["version"] == "3.1"]
    assert {p["status"] for p in current} == {"current"}


def test_rerun_is_idempotent(in_memory_vector_store):
    first = ingest(in_memory_vector_store)
    ids_first = set(all_points(in_memory_vector_store))
    second = ingest(in_memory_vector_store)
    assert set(all_points(in_memory_vector_store)) == ids_first
    assert in_memory_vector_store.count(COLLECTION, exact=True).count == len(ids_first)
    assert first.passages == second.passages == len(ids_first)


def test_failed_run_leaves_previous_index_intact(in_memory_vector_store):
    ingest(in_memory_vector_store)
    before = all_points(in_memory_vector_store)
    with pytest.raises(IngestError):
        ingest(in_memory_vector_store, embedder=FailingEmbedder())
    assert all_points(in_memory_vector_store) == before  # same ids, same payloads


def test_corpus_files_are_never_written(in_memory_vector_store):
    def snapshot():
        return {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(CORPUS.iterdir())
        }

    before = snapshot()
    ingest(in_memory_vector_store)
    assert snapshot() == before


def test_indexed_at_recorded_on_every_passage(in_memory_vector_store):
    report = ingest(in_memory_vector_store)
    stamps = {p["indexed_at"] for p in all_points(in_memory_vector_store).values()}
    assert stamps == {report.indexed_at}
    assert report.indexed_at.endswith("+00:00")
