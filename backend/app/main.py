"""FastAPI app. Run with: uvicorn --factory app.main:create_app

The factory pattern keeps settings from loading at import time, so tests build the app
with their own settings, probes and services and never read the real .env.
"""

import json
import logging
import threading
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient
from sqlalchemy import create_engine
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.ask import ApiError, AskConfig, RetrieverLike, handle_ask
from app.conflicts import known_conflicts
from app.db import Store
from app.embeddings import OpenRouterEmbedder
from app.generation import OpenRouterGenerator
from app.health import Probes, build_probes, check_components
from app.logging import configure_logging
from app.prompts import load_answer_prompt
from app.retrieval import Retriever
from app.schemas import AskResponse
from app.settings import Settings, load_settings, require

log = logging.getLogger("app.main")


@dataclass
class Services:
    retriever: RetrieverLike
    store: Store
    generator: Any = None  # the chat model (F4); None means generation is off


def build_services(settings: Settings) -> Services:
    cfg = require(
        settings,
        "qdrant_url",
        "qdrant_collection",
        "openrouter_api_key",
        "openrouter_base_url",
        "embedding_model",
        "embedding_timeout_seconds",
        "retrieval_top_k",
        "database_url",
    )
    qdrant_key = settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None
    retriever = Retriever(
        client=QdrantClient(url=cfg["qdrant_url"], api_key=qdrant_key),
        collection=cfg["qdrant_collection"],
        embedder=OpenRouterEmbedder(
            api_key=cfg["openrouter_api_key"].get_secret_value(),
            base_url=cfg["openrouter_base_url"],
            model=cfg["embedding_model"],
            timeout=cfg["embedding_timeout_seconds"],
        ),
        top_k=cfg["retrieval_top_k"],
    )
    engine = create_engine(cfg["database_url"].get_secret_value(), pool_pre_ping=True)
    generator = None
    if settings.generation_enabled:
        chat = require(
            settings,
            "chat_model",
            "chat_temperature",
            "chat_max_tokens",
            "chat_reasoning_enabled",
            "generation_timeout_seconds",
        )
        prompt = load_answer_prompt()
        generator = OpenRouterGenerator(
            api_key=cfg["openrouter_api_key"].get_secret_value(),
            base_url=cfg["openrouter_base_url"],
            model=chat["chat_model"],
            temperature=chat["chat_temperature"],
            max_tokens=chat["chat_max_tokens"],
            timeout=chat["generation_timeout_seconds"],
            reasoning_enabled=chat["chat_reasoning_enabled"],
            prompt_version=prompt.version,
            system_prompt=prompt.text,
        )
    return Services(retriever=retriever, store=Store(engine), generator=generator)


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def create_app(
    settings: Settings | None = None,
    probes: Probes | None = None,
    services: Services | None = None,
) -> FastAPI:
    cfg = settings or load_settings()
    configure_logging(cfg.log_level)
    # REQ-R7: no threshold, no API. Checked at startup, not on the first question.
    required = require(cfg, "refusal_threshold", "max_question_chars")
    ask_config = AskConfig(
        threshold=required["refusal_threshold"],
        max_question_chars=required["max_question_chars"],
        generation_enabled=cfg.generation_enabled,
        conflicts=known_conflicts(cfg.corpus_dir) if cfg.corpus_dir else [],
    )

    app = FastAPI(title="Policy Assistant API")
    app.state.probes = probes or build_probes(cfg)
    app.state.services = services
    services_lock = threading.Lock()

    def get_services() -> Services:
        # Built on first use, so /healthz answers even if a store is down at startup.
        if app.state.services is None:
            with services_lock:
                if app.state.services is None:
                    app.state.services = build_services(cfg)
        return app.state.services

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def bad_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error(422, "question_blank", "Enter a question.")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "internal_error")
        return error(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Only the type is logged: messages and SQL parameters can carry the question.
        log.error("unhandled error: %s", type(exc).__name__)
        return error(500, "internal_error", "Something went wrong. Try again shortly.")

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "policy-assistant-api"}

    @app.get("/healthz")
    async def healthz(request: Request) -> dict[str, object]:
        components = await check_components(
            request.app.state.probes, cfg.generation_enabled, cfg.healthz_timeout_seconds
        )
        healthy = all(value in ("ok", "disabled") for value in components.values())
        return {
            "status": "ok" if healthy else "degraded",
            "components": components,
            "version": cfg.app_version or "unknown",
        }

    @app.post("/api/ask", response_model=AskResponse)
    async def ask(request: Request) -> AskResponse:
        # Parsed here, not by FastAPI, so a body that isn't UTF-8 JSON gets the agreed
        # 422 question_blank instead of a framework 400.
        try:
            body = json.loads((await request.body()).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            body = None
        if not isinstance(body, dict):
            raise ApiError(422, "question_blank", "Enter a question.")
        current = get_services()
        conversation = body.get("conversation_id")
        return await run_in_threadpool(  # the ask path blocks on the network and database
            handle_ask,
            body.get("question"),
            None if conversation is None else str(conversation),
            current.retriever,
            current.store,
            ask_config,
            current.generator,
        )

    return app
