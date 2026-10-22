import asyncio
import dataclasses
import time

import httpx
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import FailingProbe, SlowProbe


def get_healthz(settings, probes):
    client = TestClient(create_app(settings=settings, probes=probes))
    response = client.get("/healthz")
    assert response.status_code == 200
    return response.json()


def test_root_answers(make_settings, healthy_probes):
    client = TestClient(create_app(settings=make_settings(), probes=healthy_probes))
    assert client.get("/").json() == {"service": "policy-assistant-api"}


def test_all_components_ok(make_settings, healthy_probes):
    body = get_healthz(make_settings(APP_VERSION="abc123"), healthy_probes)
    assert body == {
        "status": "ok",
        "components": {"postgres": "ok", "qdrant": "ok", "generation": "ok"},
        "version": "abc123",
    }


def test_database_down_still_answers(make_settings, healthy_probes):
    probes = dataclasses.replace(healthy_probes, postgres=FailingProbe())
    body = get_healthz(make_settings(), probes)
    assert body["status"] == "degraded"
    assert body["components"] == {"postgres": "unreachable", "qdrant": "ok", "generation": "ok"}


def test_vector_store_down_still_answers(make_settings, healthy_probes):
    probes = dataclasses.replace(healthy_probes, qdrant=FailingProbe())
    body = get_healthz(make_settings(), probes)
    assert body["status"] == "degraded"
    assert body["components"]["qdrant"] == "unreachable"
    assert body["components"]["postgres"] == "ok"


def test_failing_model_reported_unreachable(make_settings, healthy_probes, failing_model):
    probes = dataclasses.replace(healthy_probes, generation=failing_model)
    body = get_healthz(make_settings(), probes)
    assert body["status"] == "degraded"
    assert body["components"]["generation"] == "unreachable"


def test_generation_disabled_does_not_call_model(make_settings, healthy_probes, fake_model):
    body = get_healthz(make_settings(generation_enabled=False), healthy_probes)
    assert body["status"] == "ok"
    assert body["components"]["generation"] == "disabled"
    assert fake_model.calls == 0


def test_everything_down_still_answers(make_settings, failing_model):
    from app.health import Probes

    probes = Probes(postgres=FailingProbe(), qdrant=FailingProbe(), generation=failing_model)
    body = get_healthz(make_settings(), probes)
    assert body["status"] == "degraded"
    assert set(body["components"].values()) == {"unreachable"}


def test_slow_dependency_times_out(make_settings, healthy_probes):
    """/healthz answers within its timeout even while a dependency hangs (NFR-3).

    Timed inside the running event loop, as a server sees it. TestClient would also count
    its own shutdown, which waits for the still-sleeping probe thread to finish.
    """
    probes = dataclasses.replace(healthy_probes, postgres=SlowProbe(seconds=2.0))
    app = create_app(settings=make_settings(healthz_timeout_seconds=0.2), probes=probes)

    async def timed_request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            started = time.monotonic()
            response = await client.get("/healthz")
            return response, time.monotonic() - started

    response, elapsed = asyncio.run(timed_request())
    assert response.status_code == 200
    assert response.json()["components"]["postgres"] == "unreachable"
    assert elapsed < 1.0


def test_missing_settings_reported_unreachable(make_settings):
    from app.health import build_probes

    settings = make_settings()  # no DATABASE_URL, QDRANT_URL or OPENROUTER_API_KEY
    body = get_healthz(settings, build_probes(settings))
    assert body["components"] == {
        "postgres": "unreachable",
        "qdrant": "unreachable",
        "generation": "unreachable",
    }
