"""FastAPI app. Run with: uvicorn --factory app.main:create_app

The factory pattern keeps settings from loading at import time, so tests build the app
with their own settings and probes and never read the real .env.
"""

import logging

from fastapi import FastAPI

from app.health import Probes, build_probes, check_components
from app.settings import Settings, load_settings


def create_app(settings: Settings | None = None, probes: Probes | None = None) -> FastAPI:
    cfg = settings or load_settings()
    deps = probes or build_probes(cfg)
    if cfg.log_level:
        logging.basicConfig(level=cfg.log_level.upper())

    app = FastAPI(title="Policy Assistant API")

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "policy-assistant-api"}

    @app.get("/healthz")
    async def healthz() -> dict[str, object]:
        components = await check_components(
            deps, cfg.generation_enabled, cfg.healthz_timeout_seconds
        )
        healthy = all(value in ("ok", "disabled") for value in components.values())
        return {
            "status": "ok" if healthy else "degraded",
            "components": components,
            "version": cfg.app_version or "unknown",
        }

    return app
