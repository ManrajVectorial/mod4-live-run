"""Dependency probes for /healthz (PRD §5.6).

Each probe's check() returns normally when its dependency answers, and raises otherwise.
/healthz runs them with a timeout and keeps answering whatever they do (NFR-3).
"""

import asyncio
import logging
import math
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import urlparse

from qdrant_client import QdrantClient
from sqlalchemy import Engine, create_engine, text

from app.openrouter import HEADERS
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


def _urlopen(request: urllib.request.Request, timeout: float) -> int:
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        return response.status


class ModelProbe:
    """Calls the provider's authenticated key endpoint: proves the provider is reachable AND
    accepts our key, without generating anything. (Listing models would not: it is public.)
    The response describes the key, so it is never read or logged."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float,
        fetch: Callable[[urllib.request.Request, float], int] = _urlopen,
    ) -> None:
        self.url = base_url.rstrip("/") + "/key"
        self.api_key = api_key
        self.timeout = timeout
        self.fetch = fetch

    def check(self) -> None:
        if urlparse(self.url).scheme not in ("http", "https"):
            raise ValueError("OPENROUTER_BASE_URL must be http(s)")
        request = urllib.request.Request(  # noqa: S310 - scheme checked above
            self.url, headers={"Authorization": f"Bearer {self.api_key}", **HEADERS}
        )
        self.fetch(request, self.timeout)


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

    key, base_url = settings.openrouter_api_key, settings.openrouter_base_url
    if key is None or base_url is None:
        missing = [
            n
            for n, v in (("OPENROUTER_API_KEY", key), ("OPENROUTER_BASE_URL", base_url))
            if v is None
        ]
        generation: Probe = NotConfigured(*missing)
    else:
        generation = ModelProbe(base_url, key.get_secret_value(), timeout=timeout)

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
