"""F4 — Write the answer (REQ-A1, G1 to G11, NFR-5). Fake chat model, never the network."""

import hashlib
import json
import logging

from sqlalchemy import select

from app.citations import cited_markers
from app.conflicts import known_conflicts
from app.db import Message
from app.generation import GenerationFailed, GenerationResult, GenerationTimeout, build_messages
from app.prompts import PROMPTS_DIR, load_answer_prompt
from app.settings import REPO_ROOT
from tests.api_support import ANSWERABLE, UNANSWERABLE, make_client, passage
from tests.test_contract import check_contract


class FakeGenerator:
    """Answers with fixed text; records what it was sent."""

    def __init__(self, text="A claim of £75 or more needs line-manager approval [1].", error=None):
        self.text, self.error = text, error
        self.calls: list[dict] = []

    def generate(self, question, passages, conflict_note=None, context=None):
        self.calls.append(
            {"question": question, "passages": passages, "conflict_note": conflict_note}
        )
        if self.error:
            raise self.error
        return GenerationResult(
            text=self.text,
            model="test/fake-model",
            prompt_version="answer-test",
            prompt_tokens=120,
            completion_tokens=30,
        )


def ask(client, question="What is the approval threshold?"):
    return client.post("/api/ask", json={"question": question}).json()


def test_answered_with_cited_sources_prompt_version_and_model(make_settings):
    fake = FakeGenerator()
    client, services = make_client(make_settings, ANSWERABLE, generator=fake)
    body = ask(client)
    check_contract(body)
    assert body["status"] == "answered"
    assert body["answer"] == "A claim of £75 or more needs line-manager approval [1]."
    current = [s for s in body["sources"] if s["status"] == "current"]
    assert [(s["marker"], s["document_id"], s["section"]) for s in current] == [
        (1, "travel-expense-policy-v3.1", "4.2")
    ]  # only what the answer cites
    assert body["meta"]["prompt_version"] == "answer-test"
    assert body["meta"]["model"] == "test/fake-model"
    with services.store.session() as s:
        stored = s.scalars(select(Message).where(Message.role == "assistant")).one()
    assert (stored.status, stored.prompt_version, stored.model) == (
        "answered",
        "answer-test",
        "test/fake-model",
    )
    assert stored.content == body["answer"]


def test_model_called_only_when_gate_clears_and_generation_on(make_settings):
    fake = FakeGenerator()
    client, _ = make_client(make_settings, UNANSWERABLE, generator=fake)
    assert ask(client)["status"] == "refused"
    assert fake.calls == []
    client, _ = make_client(make_settings, ANSWERABLE, generator=fake, generation_enabled=False)
    body = ask(client)
    assert body["status"] == "degraded" and body["degraded"]["reason"] == "generation_disabled"
    assert fake.calls == []  # kill switch: zero chat-model calls
    assert body["sources"][0]["section"] == "4.2"  # passages still shown


def test_prompt_holds_only_current_passages_and_question(make_settings):
    fake = FakeGenerator()
    client, _ = make_client(make_settings, ANSWERABLE, generator=fake)
    ask(client, "What is the approval threshold?")
    (call,) = fake.calls
    assert call["question"] == "What is the approval threshold?"
    assert [p.payload["status"] for p in call["passages"]] == ["current", "current"]
    assert all(p.score > 0.5 for p in call["passages"])  # only those that cleared the gate
    system, user = build_messages("Q?", call["passages"], None, load_answer_prompt().text)
    assert system["role"] == "system" and user["role"] == "user"
    assert "travel-expense-policy-v3.0" not in json.dumps([system, user])  # superseded never sent
    assert "[1]" in user["content"] and "[2]" in user["content"] and "Q?" in user["content"]


def test_prompt_file_is_versioned_and_registered():
    prompt = load_answer_prompt()
    registry = json.loads((PROMPTS_DIR / "versions.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(prompt.text.encode("utf-8")).hexdigest()
    assert registry[prompt.version] == digest, (
        "answer.md changed without a new version: bump `version:` and register the new hash"
    )
    assert len(set(registry.values())) == len(registry)


def test_answer_citing_nothing_or_unknown_marker_is_degraded(make_settings):
    for text in ("The policy says claims need approval.", "Approval is needed [7]."):
        client, _ = make_client(make_settings, ANSWERABLE, generator=FakeGenerator(text=text))
        body = ask(client)
        assert body["status"] == "degraded"
        assert body["degraded"]["reason"] == "invalid_citations"
        assert body["answer"] is None and body["sources"]
    assert cited_markers("See [1] and [2], and [1] again.") == [1, 2]


def test_provider_timeout_and_error_degrade_and_are_logged(make_settings, caplog):
    caplog.set_level(logging.WARNING)
    for error, reason in (
        (GenerationTimeout("slow"), "provider_timeout"),
        (GenerationFailed("down"), "provider_error"),
    ):
        client, _ = make_client(make_settings, ANSWERABLE, generator=FakeGenerator(error=error))
        body = ask(client)
        check_contract(body)
        assert body["status"] == "degraded" and body["degraded"]["reason"] == reason
        assert body["sources"][0]["section"] == "4.2"
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "GenerationTimeout" in messages and "GenerationFailed" in messages


CONFLICT = [
    passage(
        "outsourcing-third-party-v1.8",
        "6.4",
        0.57,
        title="Outsourcing and Third-Party Risk Policy",
        section_title="Return and destruction on exit",
    ),
    passage(
        "records-retention-v4.0",
        "4.1",
        0.53,
        title="Records Retention and Data Handling Policy",
        section_title="General table",
    ),
]


def test_known_conflicts_come_from_manifest():
    assert known_conflicts(REPO_ROOT / "backend" / "corpus") == [
        {("records-retention", "4.1"), ("outsourcing-third-party", "6.4")}
    ]


def test_conflict_shown_with_both_sections_and_escalation(make_settings):
    fake = FakeGenerator(
        text="A provider must destroy copies within five years of termination [1]."
    )
    client, _ = make_client(make_settings, CONFLICT, generator=fake, corpus_dir="backend/corpus")
    body = ask(client, "How long can a provider keep client correspondence?")
    assert body["status"] == "answered"
    assert "conflict" in body["answer"].lower()
    assert "Group Legal and Group Operational Risk" in body["answer"]
    cited = {(s["document_id"], s["section"]) for s in body["sources"]}
    assert {("outsourcing-third-party-v1.8", "6.4"), ("records-retention-v4.0", "4.1")} <= cited
    assert fake.calls[0]["conflict_note"]  # the model is told too


def test_earlier_version_note_beside_cited_current_policy(make_settings):
    client, _ = make_client(make_settings, ANSWERABLE, generator=FakeGenerator())
    sources = ask(client)["sources"]
    old = [s for s in sources if s["status"] == "superseded"]
    assert [(s["document_id"], s["superseded_by"]) for s in old] == [
        ("travel-expense-policy-v3.0", "3.1")
    ]
    assert old[0]["marker"] > max(s["marker"] for s in sources if s["status"] == "current")


def test_token_counts_logged(make_settings, caplog):
    caplog.set_level(logging.INFO, logger="app.ask")
    client, _ = make_client(make_settings, ANSWERABLE, generator=FakeGenerator())
    ask(client)
    (line,) = [r.getMessage() for r in caplog.records if r.name == "app.ask"]
    assert (
        "status=answered" in line and "prompt_tokens=120" in line and "completion_tokens=30" in line
    )
