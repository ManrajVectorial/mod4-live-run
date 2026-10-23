"""Settings, read from environment variables and the repo-root .env (PRD §8).

Nothing here has a default value for a model name, URL or threshold (AGENTS.md rule 5).
Settings a later feature needs are optional until that feature makes them required.
Secrets are SecretStr, so they never appear in a repr, a log line or an error message.
"""

from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".env"


class SettingsError(RuntimeError):
    """Raised when settings are missing or invalid. Names the variables, never the values."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Model provider
    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str | None = None
    chat_model: str | None = None
    chat_temperature: float | None = None
    chat_max_tokens: int | None = None
    chat_reasoning_enabled: bool | None = None
    generation_enabled: bool
    generation_timeout_seconds: float | None = None

    # Retrieval (D0, D1, D2, D3)
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    embedding_timeout_seconds: float | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    refusal_threshold: float | None = None
    retrieval_top_k: int | None = None

    # Conversation (D8, D9)
    conversation_context_messages: int | None = None

    # API
    max_question_chars: int | None = None
    cors_allowed_origins: str | None = None
    healthz_timeout_seconds: float = Field(gt=0)

    # Stores
    database_url: SecretStr | None = None
    qdrant_url: str | None = None
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str | None = None

    # Corpus and tooling
    corpus_dir: Path | None = None
    eval_api_base_url: str | None = None
    eval_timeout_seconds: float | None = None
    log_level: str | None = None

    # Release identifier shown by /healthz. Railway sets RAILWAY_GIT_COMMIT_SHA itself.
    app_version: str | None = Field(
        default=None, validation_alias=AliasChoices("APP_VERSION", "RAILWAY_GIT_COMMIT_SHA")
    )

    @field_validator("corpus_dir")
    @classmethod
    def _relative_to_repo_root(cls, value: Path | None) -> Path | None:
        """A relative CORPUS_DIR means relative to the repo root, wherever the command runs."""
        if value is None or value.is_absolute():
            return value
        return REPO_ROOT / value


def require(settings: Settings, *fields: str) -> dict[str, Any]:
    """The named settings, or a SettingsError listing every one that is unset."""
    missing = [f.upper() for f in fields if getattr(settings, f) is None]
    if missing:
        raise SettingsError("Missing settings: " + ", ".join(missing) + ". See .env.example.")
    return {f: getattr(settings, f) for f in fields}


def load_settings(**overrides: Any) -> Settings:
    """Load settings, turning a validation failure into an error that names fields only."""
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in err["loc"]).upper() for err in exc.errors()})
        raise SettingsError(
            "Missing or invalid settings: " + ", ".join(fields) + ". See .env.example."
        ) from None
