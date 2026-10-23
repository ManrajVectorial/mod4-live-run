"""F8 — History (REQ-A8, A9, C7, C8). Stub retriever and fake model, in-memory store."""

import uuid

from app.generation import GenerationResult
from tests.api_support import ANSWERABLE, UNANSWERABLE, StubRetriever, make_client, passage


class Generator:
    def generate(self, question, passages, conflict_note=None, context=None):
        return GenerationResult(
            text="A claim of £75 or more needs approval [1].",
            model="test/fake",
            prompt_version="answer-test",
            prompt_tokens=1,
            completion_tokens=1,
        )


class SwappableRetriever(StubRetriever):
    def __init__(self) -> None:
        super().__init__(ANSWERABLE)

    def swap(self, hits) -> None:
        self.hits = sorted(hits, key=lambda h: (-h.score, h.passage_id))


def setup(make_settings):
    retriever = SwappableRetriever()
    client, _ = make_client(make_settings, ANSWERABLE, retriever=retriever, generator=Generator())
    return client, retriever


def ask(client, question, conversation_id=None):
    body = {"question": question} | (
        {"conversation_id": conversation_id} if conversation_id else {}
    )
    return client.post("/api/ask", json=body).json()


def test_lists_conversations_most_recent_first_with_prd_fields(make_settings):
    client, retriever = setup(make_settings)
    older = ask(client, "What is the approval threshold?")
    retriever.swap(UNANSWERABLE)
    newer = ask(client, "Parental leave?")
    body = client.get("/api/conversations").json()
    assert set(body) == {"conversations"}
    first, second = body["conversations"][:2]
    assert set(first) == {
        "conversation_id",
        "created_at",
        "updated_at",
        "first_question",
        "message_count",
        "statuses",
    }
    assert (first["conversation_id"], first["first_question"], first["statuses"]) == (
        newer["conversation_id"],
        "Parental leave?",
        ["refused"],
    )
    assert (second["conversation_id"], second["statuses"], second["message_count"]) == (
        older["conversation_id"],
        ["answered"],
        2,
    )


def test_follow_up_moves_its_conversation_to_the_top(make_settings):
    client, _ = setup(make_settings)
    first = ask(client, "First conversation?")
    ask(client, "Second conversation?")
    ask(client, "A follow-up?", first["conversation_id"])
    top = client.get("/api/conversations").json()["conversations"][0]
    assert top["conversation_id"] == first["conversation_id"]
    assert top["message_count"] == 4 and top["statuses"] == ["answered", "answered"]


def test_conversation_detail_has_prd_message_shapes(make_settings):
    client, _ = setup(make_settings)
    answered = ask(client, "What is the approval threshold?")
    body = client.get(f"/api/conversations/{answered['conversation_id']}").json()
    assert set(body) == {"conversation_id", "created_at", "messages"}
    user, assistant = body["messages"]
    assert set(user) == {"message_id", "role", "content", "created_at"}
    assert (user["role"], user["content"]) == ("user", "What is the approval threshold?")
    assert set(assistant) == {
        "message_id",
        "role",
        "status",
        "answer",
        "refusal",
        "degraded",
        "sources",
        "meta",
        "created_at",
    }
    assert assistant["message_id"] == answered["message_id"]
    assert assistant["answer"] == answered["answer"]
    assert (
        assistant["meta"]["prompt_version"] == "answer-test"
        and assistant["meta"]["model"] == "test/fake"
    )


def test_history_shows_the_citations_stored_at_answer_time(make_settings):
    client, retriever = setup(make_settings)
    answered = ask(client, "What is the approval threshold?")
    shown = [(s["document_id"], s["section"], s["text"]) for s in answered["sources"]]
    # The index changes afterwards: history must not re-run retrieval.
    retriever.swap([passage("travel-expense-policy-v3.1", "4.2", 0.9, text="REINDEXED TEXT")])
    stored = client.get(f"/api/conversations/{answered['conversation_id']}").json()["messages"][1][
        "sources"
    ]
    assert [(s["document_id"], s["section"], s["text"]) for s in stored] == shown
    assert all("REINDEXED" not in s["text"] for s in stored)


def test_refusal_is_kept_with_its_message(make_settings):
    client, retriever = setup(make_settings)
    retriever.swap(UNANSWERABLE)
    refused = ask(client, "Parental leave?")
    assistant = client.get(f"/api/conversations/{refused['conversation_id']}").json()["messages"][1]
    assert assistant["status"] == "refused" and assistant["sources"] == []
    assert assistant["refusal"] == refused["refusal"]


def test_unknown_conversation_is_404(make_settings):
    client, _ = setup(make_settings)
    for raw in (str(uuid.uuid4()), "not-a-uuid"):
        response = client.get(f"/api/conversations/{raw}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "conversation_not_found"
