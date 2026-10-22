"""The eval command, with the API replaced by in-process fakes (no network)."""

import urllib.error
from email.message import Message

from app.eval import format_rows, load_questions, run
from app.settings import REPO_ROOT

EVALUATION_FILE = REPO_ROOT / "backend" / "corpus" / "EVALUATION.md"  # read only


def test_reads_all_thirteen_questions():
    questions = load_questions(EVALUATION_FILE)
    assert [q.qid for q in questions] == [f"Q{n}" for n in range(1, 14)]
    assert questions[0].text == "What is the approval threshold for a travel expense claim?"
    assert questions[9].text.startswith("A provider holds our client correspondence")
    assert questions[12].text == "How many days of paid parental leave am I entitled to?"


def test_one_row_per_question():
    questions = load_questions(EVALUATION_FILE)

    def fake_ask(base_url, question, timeout):
        return {
            "status": "answered",
            "meta": {"top_score": 0.5},
            "sources": [{"document_id": "doc-v1", "section": "1.1"}],
        }

    rows = run(questions, "http://api.test", 1.0, ask=fake_ask)
    assert len(rows) == 13
    assert all(r.status == "answered" and r.top_score == "0.500" for r in rows)
    assert rows[0].source == "doc-v1 §1.1"
    assert len(format_rows(rows).splitlines()) == 14  # header + 13


def test_errors_are_reported_per_row_not_hidden():
    questions = load_questions(EVALUATION_FILE)[:2]

    def failing_ask(base_url, question, timeout):
        raise urllib.error.HTTPError(base_url, 404, "Not Found", Message(), None)

    rows = run(questions, "http://api.test", 1.0, ask=failing_ask)
    assert [r.status for r in rows] == ["error: HTTP 404", "error: HTTP 404"]


def test_refusal_row_with_no_sources():
    questions = load_questions(EVALUATION_FILE)[12:]

    def refusing_ask(base_url, question, timeout):
        return {"status": "refused", "meta": {"top_score": 0.1}, "sources": []}

    (row,) = run(questions, "http://api.test", 1.0, ask=refusing_ask)
    assert row.status == "refused"
    assert row.source == "—"
