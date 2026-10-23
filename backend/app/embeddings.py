"""Embeddings through OpenRouter (D0), behind a small interface so tests use a fake."""

from typing import Protocol

from openai import OpenAI

from app.openrouter import HEADERS


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenRouterEmbedder:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: float) -> None:
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=0,
            default_headers=HEADERS,
        )
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        ordered = sorted(response.data, key=lambda item: item.index)
        return [list(item.embedding) for item in ordered]
