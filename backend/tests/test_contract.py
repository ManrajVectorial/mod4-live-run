"""Contract: every /api/ask response matches PRD §5.1 and says answered, refused or degraded.

Written from the PRD, independently of the app's own response models, so a change to those
models can't quietly change the contract too.
"""

import re
import uuid
from datetime import datetime

from tests.api_support import ANSWERABLE, UNANSWERABLE, make_client

TOP_KEYS = {
    "status",
    "conversation_id",
    "message_id",
    "answer",
    "refusal",
    "degraded",
    "sources",
    "meta",
    "created_at",
}
SOURCE_KEYS = {
    "marker",
    "passage_id",
    "document_id",
    "policy_id",
    "title",
    "version",
    "status",
    "effective",
    "superseded_by",
    "section",
    "section_title",
    "text",
    "score",
}
META_KEYS = {
    "prompt_version",
    "model",
    "top_score",
    "threshold",
    "retrieved",
    "corpus_indexed_at",
    "latency_ms",
}
DEGRADED_REASONS = {
    "generation_disabled",
    "provider_error",
    "provider_timeout",
    "invalid_citations",
}


def is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    return True


def is_iso_time(value) -> bool:
    return (
        isinstance(value, str) and datetime.fromisoformat(value.replace("Z", "+00:00")) is not None
    )


def check_contract(body: dict) -> None:
    assert set(body) == TOP_KEYS
    assert body["status"] in {"answered", "refused", "degraded"}
    assert is_uuid(body["conversation_id"]) and is_uuid(body["message_id"])
    assert is_iso_time(body["created_at"])

    assert isinstance(body["sources"], list)
    for source in body["sources"]:
        assert set(source) == SOURCE_KEYS
        assert isinstance(source["marker"], int) and source["marker"] >= 1
        assert source["status"] in {"current", "superseded"}
        assert isinstance(source["score"], float)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["effective"])

    meta = body["meta"]
    assert set(meta) == META_KEYS
    assert isinstance(meta["latency_ms"], int) and isinstance(meta["retrieved"], int)

    if body["status"] == "answered":
        assert isinstance(body["answer"], str) and body["answer"]
        assert body["refusal"] is None and body["degraded"] is None
        assert body["sources"], "an answer always cites something"
        assert meta["prompt_version"] and meta["model"]  # REQ-G5
    elif body["status"] == "refused":
        assert body["answer"] is None and body["degraded"] is None
        assert set(body["refusal"]) == {"reason", "message"}
        assert body["refusal"]["reason"] == "below_threshold"
        assert meta["model"] is None
    else:
        assert body["answer"] is None and body["refusal"] is None
        assert set(body["degraded"]) == {"reason"}
        assert body["degraded"]["reason"] in DEGRADED_REASONS


def test_refused_response_matches_contract(make_settings):
    client, _ = make_client(make_settings, UNANSWERABLE)
    response = client.post("/api/ask", json={"question": "parental leave"})
    assert response.status_code == 200
    check_contract(response.json())


def test_degraded_response_matches_contract(make_settings):
    client, _ = make_client(make_settings, ANSWERABLE)
    response = client.post("/api/ask", json={"question": "approval threshold"})
    assert response.status_code == 200
    check_contract(response.json())


def test_error_responses_match_error_shape(make_settings):
    client, _ = make_client(make_settings, ANSWERABLE)
    for payload in ({"question": ""}, {"question": "q", "conversation_id": str(uuid.uuid4())}):
        body = client.post("/api/ask", json=payload).json()
        assert set(body) == {"error"} and set(body["error"]) == {"code", "message"}
