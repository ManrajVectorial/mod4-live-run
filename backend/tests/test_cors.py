"""REQ-A10: browsers may call the API only from origins in CORS_ALLOWED_ORIGINS.
The web app uses a same-origin proxy, so in practice the list is empty."""

from tests.api_support import UNANSWERABLE, make_client

PREFLIGHT = {
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type",
}


def test_no_origin_allowed_when_list_is_empty(make_settings):
    client, _ = make_client(make_settings, UNANSWERABLE)
    response = client.options("/api/ask", headers={"Origin": "https://evil.example", **PREFLIGHT})
    assert "access-control-allow-origin" not in response.headers
    response = client.post(
        "/api/ask", json={"question": "q"}, headers={"Origin": "https://evil.example"}
    )
    assert "access-control-allow-origin" not in response.headers


def test_listed_origin_allowed_and_others_not(make_settings):
    client, _ = make_client(
        make_settings,
        UNANSWERABLE,
        cors_allowed_origins="https://web.example, https://other.example",
    )
    ok = client.options("/api/ask", headers={"Origin": "https://web.example", **PREFLIGHT})
    assert ok.headers.get("access-control-allow-origin") == "https://web.example"
    bad = client.options("/api/ask", headers={"Origin": "https://evil.example", **PREFLIGHT})
    assert "access-control-allow-origin" not in bad.headers
