"""Every OpenRouter call carries X-Title: Policy Assistant sample. No network."""

from app.embeddings import OpenRouterEmbedder
from app.generation import OpenRouterGenerator
from app.health import ModelProbe

TITLE = "Policy Assistant sample"


def test_embedding_client_sends_x_title():
    embedder = OpenRouterEmbedder(api_key="k", base_url="http://127.0.0.1:1", model="m", timeout=1)
    assert embedder.client.default_headers["X-Title"] == TITLE


def test_chat_client_sends_x_title():
    generator = OpenRouterGenerator(
        api_key="k",
        base_url="http://127.0.0.1:1",
        model="m",
        temperature=0.0,
        max_tokens=10,
        timeout=1.0,
        reasoning_enabled=False,
        prompt_version="v",
        system_prompt="s",
    )
    assert generator.client.default_headers["X-Title"] == TITLE


def test_health_probe_sends_x_title():
    sent = []
    ModelProbe(
        "http://127.0.0.1:1/api/v1", "k", timeout=0.5, fetch=lambda r, t: sent.append(r)
    ).check()
    assert sent[0].get_header("X-title") == TITLE  # urllib stores header names capitalised
