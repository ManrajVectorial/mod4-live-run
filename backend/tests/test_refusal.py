"""F3 — the refusal rule (REQ-R5, R6, R7; ADR-001; D2: strictly above the threshold)."""

import pytest

from app.refusal import clears, refusal_message
from app.settings import SettingsError
from tests.api_support import ANSWERABLE, UNANSWERABLE, SpyGenerator, make_client


def test_score_must_be_strictly_above_threshold():
    assert clears(0.51, 0.5) is True
    assert clears(0.5, 0.5) is False  # equal does not clear: "nothing above threshold" refuses
    assert clears(0.49, 0.5) is False
    assert clears(None, 0.5) is False  # nothing retrieved


def test_below_threshold_is_refused(make_settings):
    client, _ = make_client(make_settings, UNANSWERABLE)
    body = client.post("/api/ask", json={"question": "parental leave?"}).json()
    assert body["status"] == "refused"
    assert body["refusal"]["reason"] == "below_threshold"


def test_refusal_makes_no_chat_model_call(make_settings):
    spy = SpyGenerator()
    client, _ = make_client(make_settings, UNANSWERABLE, generator=spy)
    assert (
        client.post("/api/ask", json={"question": "parental leave?"}).json()["status"] == "refused"
    )
    assert spy.calls == 0


def test_refusal_says_not_covered_names_teams_and_cites_nothing(make_settings):
    client, _ = make_client(make_settings, UNANSWERABLE)
    body = client.post("/api/ask", json={"question": "parental leave?"}).json()
    message = body["refusal"]["message"]
    assert "don't cover" in message
    for team in ("Group Finance", "HR", "Compliance"):
        assert team in message
    assert body["sources"] == []  # T1 "Not allowed": cites no policy at all
    assert message == refusal_message()


def test_api_will_not_start_without_threshold(make_settings):
    with pytest.raises(SettingsError, match="REFUSAL_THRESHOLD"):
        make_client(make_settings, ANSWERABLE, refusal_threshold=None)
