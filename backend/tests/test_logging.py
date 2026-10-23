"""F3 — logs never hold question text (NFR-4) or secrets (NFR-6)."""

import logging

from app.logging import configure_logging
from tests.api_support import ANSWERABLE, UNANSWERABLE, make_client
from tests.test_api_ask import ExplodingRetriever

MARKER = "zebra-quokka-7731 how many days of leave"
SECRET = "sk-or-test-secret-should-never-be-logged"


def all_log_text(caplog) -> str:
    return "\n".join(r.getMessage() + " " + str(r.args) for r in caplog.records) + caplog.text


def test_question_text_never_logged(make_settings, caplog):
    caplog.set_level(logging.DEBUG)
    for hits in (UNANSWERABLE, ANSWERABLE):
        client, _ = make_client(make_settings, hits)
        client.post("/api/ask", json={"question": MARKER})
    client, _ = make_client(make_settings, ANSWERABLE, retriever=ExplodingRetriever())
    client.post("/api/ask", json={"question": MARKER})
    assert caplog.records, "the ask path should log something"
    assert MARKER not in all_log_text(caplog)


def test_one_line_per_ask_with_status_score_and_latency(make_settings, caplog):
    caplog.set_level(logging.INFO, logger="app.ask")
    client, _ = make_client(make_settings, UNANSWERABLE)
    client.post("/api/ask", json={"question": "anything"})
    lines = [r.getMessage() for r in caplog.records if r.name == "app.ask"]
    assert len(lines) == 1
    assert (
        "status=refused" in lines[0] and "top_score=0.270" in lines[0] and "latency_ms=" in lines[0]
    )
    assert "request_id=" in lines[0]


def test_secrets_never_logged(make_settings, caplog):
    caplog.set_level(logging.DEBUG)
    client, _ = make_client(
        make_settings,
        ANSWERABLE,
        openrouter_api_key=SECRET,
        database_url=f"postgresql+pg8000://u:{SECRET}@127.0.0.1:1/x",
    )
    client.post("/api/ask", json={"question": "approval threshold"})
    client.get("/healthz")
    assert SECRET not in all_log_text(caplog)


def test_provider_client_loggers_held_at_warning():
    """openai and httpx log request bodies (the question) at DEBUG; keep them quiet."""
    configure_logging("DEBUG")
    for name in ("openai", "httpx", "httpcore"):
        assert logging.getLogger(name).getEffectiveLevel() >= logging.WARNING
