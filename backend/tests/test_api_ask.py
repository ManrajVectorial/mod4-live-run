"""F3 — POST /api/ask: refused and degraded paths, the record, and errors.
REQ-R8 is proved by the real evaluation run (see the F3 ticket)."""

import uuid

from sqlalchemy import select

from app.db import Citation, Conversation, Message
from tests.api_support import ANSWERABLE, THRESHOLD, UNANSWERABLE, make_client


def ask(client, question, **extra):
    return client.post("/api/ask", json={"question": question, **extra})


def test_cleared_question_is_degraded_with_passages_before_f4(make_settings):
    client, _ = make_client(make_settings, ANSWERABLE)
    body = ask(client, "What is the approval threshold?").json()
    assert body["status"] == "degraded"
    assert body["degraded"] == {"reason": "generation_disabled"}
    assert body["answer"] is None
    first = body["sources"][0]
    assert (first["document_id"], first["section"]) == ("travel-expense-policy-v3.1", "4.2")


def test_degraded_sources_clear_threshold_and_superseded_is_labelled(make_settings):
    client, _ = make_client(make_settings, ANSWERABLE)
    sources = ask(client, "approval threshold").json()["sources"]
    current = [s for s in sources if s["status"] == "current"]
    assert all(s["score"] > THRESHOLD for s in current)  # §2.4 at 0.31 is left out
    assert [s["section"] for s in current] == ["4.2", "4.1"]
    old = [s for s in sources if s["status"] == "superseded"]
    assert [(s["document_id"], s["superseded_by"]) for s in old] == [
        ("travel-expense-policy-v3.0", "3.1")
    ]
    assert [s["marker"] for s in sources] == list(range(1, len(sources) + 1))


def test_meta_reports_gate_and_no_model(make_settings):
    client, _ = make_client(make_settings, UNANSWERABLE)
    meta = ask(client, "parental leave").json()["meta"]
    assert meta["prompt_version"] is None and meta["model"] is None
    assert meta["top_score"] == 0.27 and meta["threshold"] == THRESHOLD
    assert meta["retrieved"] == 2
    assert meta["corpus_indexed_at"] == "2026-10-23T00:00:00Z"  # PRD §5.1 format
    assert isinstance(meta["latency_ms"], int)


def test_every_exchange_is_recorded_with_citations(make_settings):
    client, services = make_client(make_settings, ANSWERABLE)
    body = ask(client, "approval threshold").json()
    with services.store.session() as s:
        messages = s.scalars(select(Message).order_by(Message.seq)).all()
        citations = s.scalars(select(Citation)).all()
    assert [(m.role, m.status) for m in messages] == [("user", None), ("assistant", "degraded")]
    assert messages[0].content == "approval threshold"
    assert str(messages[1].id) == body["message_id"]
    assert messages[1].degraded_reason == "generation_disabled"
    assert len(citations) == len(body["sources"])
    assert {c.version for c in citations} == {"3.1", "3.0"}


def test_refusal_is_recorded_too(make_settings):
    client, services = make_client(make_settings, UNANSWERABLE)
    body = ask(client, "parental leave").json()
    with services.store.session() as s:
        assistant = s.scalars(select(Message).where(Message.role == "assistant")).one()
    assert assistant.status == "refused" and assistant.refusal_reason == "below_threshold"
    assert assistant.refusal_message == body["refusal"]["message"]


def test_without_conversation_id_a_new_conversation_starts(make_settings):
    client, services = make_client(make_settings, UNANSWERABLE)
    first = ask(client, "one").json()["conversation_id"]
    second = ask(client, "two").json()["conversation_id"]
    assert first != second
    with services.store.session() as s:
        assert s.scalars(select(Conversation)).all().__len__() == 2


def test_blank_question_is_422_before_retrieval(make_settings):
    client, services = make_client(make_settings, ANSWERABLE)
    for payload in ({"question": "   "}, {"question": ""}, {}):
        response = client.post("/api/ask", json=payload)
        assert response.status_code == 422
        assert response.json() == {
            "error": {"code": "question_blank", "message": "Enter a question."}
        }
    assert services.retriever.texts == []


def test_malformed_body_is_422_question_blank(make_settings):
    client, services = make_client(make_settings, ANSWERABLE)
    bad_bodies = (
        b'{"question": "Does a claim of exactly \xa375 need approval?"}',  # not UTF-8
        b'{"question": ',  # not JSON
        b'["question"]',  # JSON, but not an object
    )
    for raw in bad_bodies:
        response = client.post(
            "/api/ask", content=raw, headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422, raw
        assert response.json() == {
            "error": {"code": "question_blank", "message": "Enter a question."}
        }
    assert services.retriever.texts == []


def test_too_long_question_is_422(make_settings):
    client, services = make_client(make_settings, ANSWERABLE, max_question_chars=20)
    response = ask(client, "x" * 21)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "question_too_long"
    assert services.retriever.texts == []


def test_unknown_conversation_is_404(make_settings):
    client, _ = make_client(make_settings, ANSWERABLE)
    response = ask(client, "q", conversation_id=str(uuid.uuid4()))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"


class ExplodingRetriever:
    texts: list = []

    def retrieve(self, text):
        raise RuntimeError(f"boom with {text}")


def test_internal_error_uses_error_shape_without_trace(make_settings):
    client, _ = make_client(make_settings, ANSWERABLE, retriever=ExplodingRetriever())
    response = ask(client, "secret question text")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Something went wrong. Try again shortly."}
    }
    assert "Traceback" not in response.text and "boom" not in response.text


def test_healthz_still_answers_with_services(make_settings):
    from app.health import Probes
    from tests.conftest import FailingProbe

    client, _ = make_client(make_settings, ANSWERABLE)
    client.app.state.probes = Probes(FailingProbe(), FailingProbe(), FailingProbe())
    assert client.get("/healthz").status_code == 200
