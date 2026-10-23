"""The real services are built from settings alone. Construction only: no network calls."""

import pytest

from app.generation import OpenRouterGenerator
from app.main import build_services
from app.settings import SettingsError

FULL = {
    "qdrant_url": "http://127.0.0.1:1",
    "qdrant_collection": "c",
    "openrouter_api_key": "sk-test",
    "openrouter_base_url": "http://127.0.0.1:1/api/v1",
    "embedding_model": "openai/text-embedding-3-small",
    "embedding_timeout_seconds": 5,
    "retrieval_top_k": 5,
    "database_url": "sqlite://",
    "chat_model": "anthropic/claude-haiku-5.5",
    "chat_temperature": 0,
    "chat_max_tokens": 600,
    "chat_reasoning_enabled": False,
    "generation_timeout_seconds": 6,
}


def test_builds_generator_from_every_chat_setting(make_settings):
    services = build_services(make_settings(**FULL))
    generator = services.generator
    assert isinstance(generator, OpenRouterGenerator)
    assert generator.model == "anthropic/claude-haiku-5.5"
    assert generator.max_tokens == 600 and generator.reasoning_enabled is False
    assert generator.prompt_version == "answer-v1"


def test_no_generator_when_generation_disabled(make_settings):
    assert build_services(make_settings(**FULL, generation_enabled=False)).generator is None


@pytest.mark.parametrize(
    "missing",
    [
        "chat_model",
        "chat_temperature",
        "chat_max_tokens",
        "chat_reasoning_enabled",
        "generation_timeout_seconds",
    ],
)
def test_each_missing_chat_setting_is_named(make_settings, missing):
    values = {**FULL, missing: None}
    with pytest.raises(SettingsError, match=missing.upper()):
        build_services(make_settings(**values))
