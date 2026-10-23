"""F2 — Search them (REQ-R1 to R4). In-memory Qdrant, fake embedder, real corpus (read only)."""

import re

import pytest

from app.eval import EXPECTED, Row, load_questions, outcome, results_table, top_three_hits
from app.ingest import run_ingest
from app.retrieval import Hit, Retriever
from app.settings import REPO_ROOT
from tests.conftest import TEST_DIMENSIONS, FakeEmbedder

CORPUS = REPO_ROOT / "backend" / "corpus"
COLLECTION = "test_passages"


@pytest.fixture
def indexed(in_memory_vector_store):
    run_ingest(
        corpus_dir=CORPUS,
        embedder=FakeEmbedder(),
        client=in_memory_vector_store,
        collection=COLLECTION,
        embedding_model="fake-embedding",
        dimensions=TEST_DIMENSIONS,
        chunk_size=1200,
        chunk_overlap=0,
    )
    return in_memory_vector_store


class CountingEmbedder(FakeEmbedder):
    def __init__(self) -> None:
        super().__init__()
        self.texts: list[str] = []

    def embed(self, texts):
        self.texts += texts
        return super().embed(texts)


def make_retriever(client, embedder=None, top_k=5):
    return Retriever(
        client=client, collection=COLLECTION, embedder=embedder or FakeEmbedder(), top_k=top_k
    )


def test_question_embedded_once_with_same_embedder_and_top_k_returned(indexed):
    embedder = CountingEmbedder()
    hits = make_retriever(indexed, embedder, top_k=5).search("What is the approval threshold?")
    assert embedder.texts == ["What is the approval threshold?"]
    assert len(hits) == 5


def test_hits_in_descending_score_order_with_payload(indexed):
    hits = make_retriever(indexed).search("accommodation cap Singapore per night")
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)
    for hit in hits:
        assert hit.payload["passage_id"] and hit.payload["document_id"] and hit.payload["section"]


def test_same_question_same_order_ties_broken_by_passage_id(indexed):
    retriever = make_retriever(indexed, top_k=20)
    first = [h.passage_id for h in retriever.search("approval")]
    second = [h.passage_id for h in retriever.search("approval")]
    assert first == second
    hits = retriever.search("approval")
    for a, b in zip(hits, hits[1:], strict=False):
        assert a.score > b.score or (a.score == b.score and a.passage_id < b.passage_id)


def test_every_hit_carries_status_and_superseded_kept_apart(indexed):
    result = make_retriever(indexed, top_k=10).retrieve("approval threshold travel expense claim")
    assert all(h.payload["status"] in ("current", "superseded") for h in result.hits)
    assert all(
        h.payload["status"] == "current" for h in result.current
    )  # D4: only these reach the model
    assert all(h.payload["status"] == "superseded" for h in result.superseded)
    assert len(result.current) + len(result.superseded) == len(result.hits)


def test_eval_knows_expected_sections_for_all_thirteen():
    questions = load_questions(CORPUS / "EVALUATION.md")
    assert [q.qid for q in questions] == list(EXPECTED)
    assert EXPECTED["Q1"] == [{("travel-expense-policy-v3.1", "4.2")}]
    assert EXPECTED["Q10"] == [
        {("outsourcing-third-party-v1.8", "6.4")},
        {("records-retention-v4.0", "4.1")},
    ]
    assert all(EXPECTED[q] == [] for q in ("Q11", "Q12", "Q13"))  # must refuse


def hit(document_id, section, score):
    return Hit(
        score=score,
        payload={
            "document_id": document_id,
            "section": section,
            "passage_id": f"{document_id}:{section}:0",
            "status": "current",
        },
    )


def test_top_three_hits_are_current_passages_only(indexed):
    hits = top_three_hits(make_retriever(indexed, top_k=10), "approval threshold travel claim")
    assert len(hits) == 3
    assert all(h.payload["status"] == "current" for h in hits)


def test_results_table_checks_expected_section_in_top_three():
    questions = load_questions(CORPUS / "EVALUATION.md")
    hits = {
        "Q1": [
            hit("travel-expense-policy-v3.1", "4.2", 0.81),
            hit("records-retention-v4.0", "4.1", 0.5),
        ],
        "Q10": [hit("outsourcing-third-party-v1.8", "6.4", 0.7)],  # missing Records Retention §4.1
        "Q13": [hit("records-retention-v4.0", "4.1", 0.2)],
    }
    table = results_table(questions, hits, api_rows=None)
    rows = {
        line.split(" | ")[0][2:]: line
        for line in table.splitlines()
        if re.match(r"\| Q\d+ \|", line)
    }
    assert list(rows) == [f"Q{n}" for n in range(1, 14)]
    assert "| Q1 | 0.810 | yes |" in rows["Q1"]
    assert "travel-expense-policy-v3.1 §4.2 (0.810)" in rows["Q1"]
    assert "| Q10 | 0.700 | NO |" in rows["Q10"]
    assert "| Q13 | 0.200 | must refuse |" in rows["Q13"]
    assert rows["Q2"].startswith("| Q2 | — |")


def test_outcome_needs_answer_with_expected_section_or_refusal():
    def row(qid, status, cited=()):
        return Row(qid, status, "—", "—", "q", cited)

    assert outcome("Q1", row("Q1", "answered", (("travel-expense-policy-v3.1", "4.2"),))) == "PASS"
    assert outcome("Q1", row("Q1", "answered", (("records-retention-v4.0", "4.1"),))) == "FAIL"
    assert outcome("Q1", row("Q1", "degraded", (("travel-expense-policy-v3.1", "4.2"),))) == "FAIL"
    q10 = (("outsourcing-third-party-v1.8", "6.4"), ("records-retention-v4.0", "4.1"))
    assert outcome("Q10", row("Q10", "answered", q10)) == "PASS"
    assert outcome("Q10", row("Q10", "answered", q10[:1])) == "FAIL"
    assert outcome("Q13", row("Q13", "refused")) == "PASS"
    assert outcome("Q13", row("Q13", "answered")) == "FAIL"
    assert outcome("Q13", row("Q13", "error: HTTP 404")) == "—"
