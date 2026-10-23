"""F6 — Follow-up questions (REQ-C3 to C6), with D9 amendment 2: a follow-up is rewritten
by the model into a standalone question, which is searched and gated by the same rule.
The first question of a conversation is never rewritten. No network."""

import hashlib
import json
import logging
import uuid

from app.generation import GenerationResult
from app.prompts import PROMPTS_DIR, load_rewrite_prompt
from app.retrieval import Retrieval
from app.rewrite import RewriteFailed
from tests.api_support import ANSWERABLE, UNANSWERABLE, make_client


class TextRetriever:
    """Answerable hits for any text, unless it mentions a must-refuse topic."""

    REFUSE_WORDS = ("partner", "parental", "cryptocurrency")

    def __init__(self) -> None:
        self.texts: list[str] = []

    def retrieve(self, text):
        self.texts.append(text)
        hits = UNANSWERABLE if any(w in text.lower() for w in self.REFUSE_WORDS) else ANSWERABLE
        hits = sorted(hits, key=lambda h: (-h.score, h.passage_id))
        return Retrieval(
            hits=hits,
            current=[h for h in hits if h.payload["status"] == "current"],
            superseded=[h for h in hits if h.payload["status"] == "superseded"],
        )


class FakeRewriter:
    def __init__(self, rewrites=None, error=None) -> None:
        self.rewrites = rewrites or {}
        self.error = error
        self.calls: list[tuple[str, list[dict]]] = []

    def rewrite(self, question, history):
        self.calls.append((question, history))
        if self.error:
            raise self.error
        return self.rewrites.get(question, f"Standalone: {question}")


class FakeGenerator:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate(self, question, passages, conflict_note=None, context=None):
        self.calls.append({"question": question, "context": context})
        return GenerationResult(
            text=f"Answer {len(self.calls)} [1].",
            model="test/fake",
            prompt_version="answer-test",
            prompt_tokens=1,
            completion_tokens=1,
        )


def setup(make_settings, rewriter=None, **settings):
    retriever, generator = TextRetriever(), FakeGenerator()
    rewriter = rewriter or FakeRewriter()
    client, services = make_client(
        make_settings,
        ANSWERABLE,
        retriever=retriever,
        generator=generator,
        rewriter=rewriter,
        **settings,
    )
    return client, retriever, generator, rewriter


def ask(client, question, conversation_id=None):
    body = {"question": question} | (
        {"conversation_id": conversation_id} if conversation_id else {}
    )
    return client.post("/api/ask", json=body)


def test_follow_up_appends_and_unknown_conversation_is_404(make_settings):
    client, *_ = setup(make_settings)
    first = ask(client, "What is the approval threshold?").json()
    second = ask(client, "And for exactly £75?", first["conversation_id"]).json()
    assert second["conversation_id"] == first["conversation_id"]
    missing = ask(client, "q", str(uuid.uuid4()))
    assert (
        missing.status_code == 404 and missing.json()["error"]["code"] == "conversation_not_found"
    )


def test_first_question_is_never_rewritten(make_settings):
    client, retriever, _, rewriter = setup(make_settings)
    ask(client, "What is the approval threshold?")
    assert rewriter.calls == []
    assert retriever.texts == ["What is the approval threshold?"]


def test_follow_up_is_rewritten_with_the_conversation_and_searched_as_rewritten(make_settings):
    rewriter = FakeRewriter({"And for Singapore?": "What is the accommodation cap for Singapore?"})
    client, retriever, _, _ = setup(make_settings, rewriter=rewriter)
    first = ask(client, "What is the accommodation cap for London?").json()
    ask(client, "And for Singapore?", first["conversation_id"])
    ((question, history),) = rewriter.calls
    assert question == "And for Singapore?"
    assert history == [
        {"role": "user", "content": "What is the accommodation cap for London?"},
        {"role": "assistant", "content": "Answer 1."},  # old citation markers dropped
    ]
    assert retriever.texts[-1] == "What is the accommodation cap for Singapore?"


def test_refusal_rule_judges_the_rewritten_question(make_settings):
    partner = "Can I expense my partner's flight?"
    rewriter = FakeRewriter({partner: f"{partner[:-1]} on business travel?"})
    client, _, generator, rewriter = setup(make_settings, rewriter=rewriter)
    first = ask(client, "What is the approval threshold?").json()
    follow_up = ask(client, "Can I expense my partner's flight?", first["conversation_id"]).json()
    assert follow_up["status"] == "refused" and follow_up["sources"] == []
    assert len(rewriter.calls) == 1  # the one model call D9 allows before the rule
    assert len(generator.calls) == 1  # no answering call for the refused follow-up


def test_answer_model_sees_the_last_five_messages(make_settings):
    client, _, generator, _ = setup(make_settings)
    conversation = None
    for n in range(1, 5):
        conversation = ask(client, f"Question {n}?", conversation).json()["conversation_id"]
    ask(client, "Question 5?", conversation)
    assert generator.calls[0]["context"] in (None, [])
    context = generator.calls[-1]["context"]
    assert [m["content"] for m in context] == [
        "Answer 2.",
        "Question 3?",
        "Answer 3.",
        "Question 4?",
        "Answer 4.",
    ]
    assert generator.calls[-1]["question"] == "Standalone: Question 5?"


def test_rewrite_failure_falls_back_to_the_question_as_asked(make_settings, caplog):
    caplog.set_level(logging.WARNING)
    client, retriever, _, _ = setup(
        make_settings, rewriter=FakeRewriter(error=RewriteFailed("down"))
    )
    first = ask(client, "What is the approval threshold?").json()
    response = ask(client, "Can I expense my partner's flight?", first["conversation_id"])
    assert response.status_code == 200 and response.json()["status"] == "refused"
    assert retriever.texts[-1] == "Can I expense my partner's flight?"
    assert "RewriteFailed" in caplog.text


def test_model_down_on_a_follow_up_shows_passages_not_a_refusal(make_settings):
    """FND-1 and T1's Error criterion: with the model down, a follow-up is searched joined
    with the question before it and comes back degraded with passages, never 'not covered'
    just because the bare follow-up finds nothing."""
    for provider, reason in (("timeout", "provider_timeout"), ("error", "provider_error")):
        down = FakeRewriter(error=RewriteFailed("APITimeoutError", provider=provider))
        client, retriever, generator, _ = setup(make_settings, rewriter=down)
        first = ask(client, "What is the accommodation cap for London?").json()
        response = ask(client, "And for Singapore?", first["conversation_id"]).json()
        assert response["status"] == "degraded"
        assert response["degraded"] == {"reason": reason}
        assert response["sources"], "the passages are shown"
        assert retriever.texts[-1] == (
            "What is the accommodation cap for London? And for Singapore?"
        )
        assert len(generator.calls) == 1  # the model just failed: no second attempt


def test_model_down_joined_follow_up_is_still_judged_by_the_rule(make_settings):
    down = FakeRewriter(error=RewriteFailed("APIConnectionError", provider="error"))
    client, _, generator, _ = setup(make_settings, rewriter=down)
    first = ask(client, "What is the approval threshold?").json()
    response = ask(client, "Can I expense my partner's flight?", first["conversation_id"]).json()
    assert response["status"] == "refused" and response["sources"] == []
    assert len(generator.calls) == 1


def test_no_rewrite_when_generation_is_switched_off(make_settings):
    client, retriever, _, rewriter = setup(make_settings, generation_enabled=False)
    first = ask(client, "What is the approval threshold?").json()
    ask(client, "And for £75?", first["conversation_id"])
    assert rewriter.calls == []
    assert retriever.texts[-1] == "And for £75?"


def test_reset_starts_a_conversation_with_nothing_earlier(make_settings):
    client, retriever, generator, rewriter = setup(make_settings)
    first = ask(client, "What is the approval threshold?").json()
    ask(client, "Follow-up?", first["conversation_id"])
    fresh = ask(client, "A new question?").json()  # Reset drops the conversation_id
    assert fresh["conversation_id"] != first["conversation_id"]
    assert len(rewriter.calls) == 1 and retriever.texts[-1] == "A new question?"
    assert generator.calls[-1]["context"] in (None, [])


def test_rewrite_prompt_is_versioned_and_registered():
    prompt = load_rewrite_prompt()
    registry = json.loads((PROMPTS_DIR / "versions.json").read_text(encoding="utf-8"))
    assert registry[prompt.version] == hashlib.sha256(prompt.text.encode("utf-8")).hexdigest()
    assert prompt.version.startswith("rewrite-")
