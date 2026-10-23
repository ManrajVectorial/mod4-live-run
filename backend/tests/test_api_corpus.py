"""F7 — Browse the documents (REQ-A6, A7, B1, B2, B5). The real corpus, ingested with the
fake embedder into an in-memory Qdrant (read only)."""

import pytest

from app.corpus_index import CorpusIndex
from app.ingest import run_ingest
from app.settings import REPO_ROOT
from tests.api_support import ANSWERABLE, make_client
from tests.conftest import TEST_DIMENSIONS, FakeEmbedder

COLLECTION = "test_passages"


@pytest.fixture
def corpus_index(in_memory_vector_store):
    report = run_ingest(
        corpus_dir=REPO_ROOT / "backend" / "corpus",
        embedder=FakeEmbedder(),
        client=in_memory_vector_store,
        collection=COLLECTION,
        embedding_model="fake-embedding",
        dimensions=TEST_DIMENSIONS,
        chunk_size=1200,
        chunk_overlap=0,
    )
    index = CorpusIndex(in_memory_vector_store, COLLECTION)
    index.report = report  # for assertions
    return index


@pytest.fixture
def client(make_settings, corpus_index):
    client, _ = make_client(make_settings, ANSWERABLE, corpus=corpus_index)
    return client


def test_lists_all_five_documents_with_prd_fields(client, corpus_index):
    body = client.get("/api/corpus").json()
    docs = {d["document_id"]: d for d in body["documents"]}
    assert set(docs) == {
        "travel-expense-policy-v3.1",
        "travel-expense-policy-v3.0",
        "client-onboarding-kyc-v2.4",
        "records-retention-v4.0",
        "outsourcing-third-party-v1.8",
    }
    old = docs["travel-expense-policy-v3.0"]
    assert set(old) == {
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
        "passage_count",
        "indexed_at",
    }
    assert (old["status"], old["superseded_by"], old["superseded_on"]) == (
        "superseded",
        "3.1",
        "2026-04-01",
    )
    assert docs["travel-expense-policy-v3.1"]["status"] == "current"
    assert sum(d["passage_count"] for d in docs.values()) == corpus_index.report.passages


def test_document_comes_back_section_by_section_in_order(client):
    body = client.get("/api/corpus/travel-expense-policy-v3.1").json()
    assert set(body) == {"document", "current_document_id", "sections"}
    assert body["document"]["title"] == "Travel and Expense Policy"
    assert body["current_document_id"] == "travel-expense-policy-v3.1"
    numbers = [s["section"] for s in body["sections"]]
    assert numbers[:3] == ["1.1", "1.2", "1.3"]
    approval = next(s for s in body["sections"] if s["section"] == "4.2")
    assert approval["section_title"] == "Approval thresholds"
    assert approval["heading_path"] == ["4. Approval", "4.2 Approval thresholds"]
    assert "£75 or more" in approval["passages"][0]["text"]
    assert set(approval["passages"][0]) == {"passage_id", "text"}


def test_superseded_document_points_to_its_current_version(client):
    body = client.get("/api/corpus/travel-expense-policy-v3.0").json()
    assert body["document"]["status"] == "superseded"
    assert body["current_document_id"] == "travel-expense-policy-v3.1"


def test_unknown_document_is_404(client):
    response = client.get("/api/corpus/no-such-policy-v9")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "document_not_found", "message": "That document isn't in the corpus."}
    }
