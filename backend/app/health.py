"""Dependency probes for /healthz (PRD §5.6).

Each probe's check() returns normally when its dependency answers, and raises otherwise.
/healthz runs them with a timeout and keeps answering whatever they do (NFR-3).
"""

import asyncio
import logging
import math
from dataclasses import dataclass
from typing import Literal, Protocol

from openai import OpenAI
from qdrant_client import QdrantClient
from sqlalchemy import Engine, create_engine, text

from app.settings import Settings

log = logging.getLogger(__name__)

ComponentStatus = Literal["ok", "unreachable", "disabled"]


class Probe(Protocol):
    def check(self) -> None: ...


class NotConfigured:
    """Stands in for a dependency whose settings are missing. Always unreachable."""

    def __init__(self, *missing: str) -> None:
        self.missing = missing

    def check(self) -> None:
        raise RuntimeError("not configured: " + ", ".join(self.missing))


class DatabaseProbe:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def check(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))


class VectorStoreProbe:
    def __init__(self, client: QdrantClient) -> None:
        self.client = client

    def check(self) -> None:
        self.client.get_collections()


class ModelProbe:
    """Lists the provider's models: proves it is reachable without generating anything."""

    def __init__(self, client: OpenAI) -> None:
        self.client = client

    def check(self) -> None:
        self.client.models.list()


@dataclass
class Probes:
    postgres: Probe
    qdrant: Probe
    generation: Probe


def build_probes(settings: Settings) -> Probes:
    timeout = settings.healthz_timeout_seconds

    if settings.database_url is None:
        postgres: Probe = NotConfigured("DATABASE_URL")
    else:
        engine = create_engine(
            settings.database_url.get_secret_value(),
            connect_args={"timeout": timeout},
            pool_pre_ping=True,
        )
        postgres = DatabaseProbe(engine)

    if settings.qdrant_url is None:
        qdrant: Probe = NotConfigured("QDRANT_URL")
    else:
        api_key = settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None
        qdrant = VectorStoreProbe(
            QdrantClient(url=settings.qdrant_url, api_key=api_key, timeout=math.ceil(timeout))
        )

    missing = [
        name
        for name, value in (
            ("OPENROUTER_API_KEY", settings.openrouter_api_key),
            ("OPENROUTER_BASE_URL", settings.openrouter_base_url),
        )
        if value is None
    ]
    if missing:
        generation: Probe = NotConfigured(*missing)
    else:
        generation = ModelProbe(
            OpenAI(
                api_key=settings.openrouter_api_key.get_secret_value(),
                base_url=settings.openrouter_base_url,
                timeout=timeout,
                max_retries=0,
            )
        )

    return Probes(postgres=postgres, qdrant=qdrant, generation=generation)


async def run_probe(name: str, probe: Probe, timeout: float) -> ComponentStatus:
    try:
        await asyncio.wait_for(asyncio.to_thread(probe.check), timeout=timeout)
    except TimeoutError:
        log.warning("healthz: %s did not answer within %ss", name, timeout)
        return "unreachable"
    except Exception as exc:  # any failure means unreachable; the type is logged, never hidden
        # Only the exception type is logged: messages can carry connection details.
        log.warning("healthz: %s unreachable (%s)", name, type(exc).__name__)
        return "unreachable"
    return "ok"


async def check_components(
    probes: Probes, generation_enabled: bool, timeout: float
) -> dict[str, ComponentStatus]:
    postgres, qdrant = await asyncio.gather(
        run_probe("postgres", probes.postgres, timeout),
        run_probe("qdrant", probes.qdrant, timeout),
    )
    if generation_enabled:
        generation = await run_probe("generation", probes.generation, timeout)
    else:
        generation = "disabled"
    return {"postgres": postgres, "qdrant": qdrant, "generation": generation}
