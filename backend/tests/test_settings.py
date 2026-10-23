from pathlib import Path

import pytest

from app.settings import REPO_ROOT, SettingsError, load_settings

SECRET = "sk-test-not-a-real-key-123456"


def test_required_settings_missing_names_them(monkeypatch):
    monkeypatch.delenv("GENERATION_ENABLED", raising=False)
    monkeypatch.delenv("HEALTHZ_TIMEOUT_SECONDS", raising=False)
    with pytest.raises(SettingsError) as info:
        load_settings(_env_file=None)
    message = str(info.value)
    assert "GENERATION_ENABLED" in message
    assert "HEALTHZ_TIMEOUT_SECONDS" in message


def test_invalid_value_error_does_not_echo_the_value():
    with pytest.raises(SettingsError) as info:
        load_settings(_env_file=None, generation_enabled=True, healthz_timeout_seconds=SECRET)
    assert SECRET not in str(info.value)
    assert "HEALTHZ_TIMEOUT_SECONDS" in str(info.value)


def test_secrets_never_appear_in_repr(make_settings):
    settings = make_settings(openrouter_api_key=SECRET, database_url=f"postgresql://u:{SECRET}@h/d")
    assert SECRET not in repr(settings)
    assert SECRET not in str(settings)
    assert settings.openrouter_api_key.get_secret_value() == SECRET


def test_reads_env_file(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GENERATION_ENABLED=false\nHEALTHZ_TIMEOUT_SECONDS=0.8\nRETRIEVAL_TOP_K=5\nCHAT_MODEL=\n",
        encoding="utf-8",
    )
    settings = load_settings(_env_file=env_file)
    assert settings.generation_enabled is False
    assert settings.healthz_timeout_seconds == 0.8
    assert settings.retrieval_top_k == 5
    assert settings.chat_model is None  # blank in .env means unset


def test_relative_corpus_dir_resolves_from_repo_root(make_settings):
    settings = make_settings(corpus_dir="backend/corpus")
    assert settings.corpus_dir == REPO_ROOT / "backend" / "corpus"
