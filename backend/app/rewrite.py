"""Follow-up rewriting (D9 amendment 2, decided by the product owner).

On a follow-up, the chat model rewrites the new question as one standalone question, using
the conversation so far. It only rewrites; it never answers, and it decides nothing: the
rewritten question is searched and judged by the same refusal rule and threshold as any other.
"""

from typing import Literal, Protocol

import openai
from openai import OpenAI

from app.openrouter import HEADERS


class RewriteFailed(Exception):
    """No usable rewrite.

    `provider` says why: "timeout" or "error" when the model provider failed (the model is
    down, so no answer can be composed either), or None when the model replied with
    something unusable. The caller decides what to search on (FND-1).
    """

    def __init__(self, message: str, provider: Literal["timeout", "error"] | None = None):
        super().__init__(message)
        self.provider = provider


class Rewriter(Protocol):
    def rewrite(self, question: str, history: list[dict]) -> str: ...


class OpenRouterRewriter:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        max_tokens: int,
        timeout: float,
        reasoning_enabled: bool,
        prompt_version: str,
        system_prompt: str,
        max_chars: int,
    ) -> None:
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=0,
            default_headers=HEADERS,
        )
        self.model, self.max_tokens, self.max_chars = model, max_tokens, max_chars
        self.reasoning_enabled = reasoning_enabled
        self.prompt_version, self.system_prompt = prompt_version, system_prompt

    def rewrite(self, question: str, history: list[dict]) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            *history,
            {"role": "user", "content": f"Latest question to rewrite: {question}"},
        ]
        extra_body = None if self.reasoning_enabled else {"reasoning": {"enabled": False}}
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,  # a rewrite should be as repeatable as possible
                max_tokens=self.max_tokens,
                extra_body=extra_body,
            )
        except openai.APITimeoutError as exc:  # before OpenAIError: it is a subclass
            raise RewriteFailed(type(exc).__name__, provider="timeout") from exc
        except openai.OpenAIError as exc:
            raise RewriteFailed(type(exc).__name__, provider="error") from exc
        choice = response.choices[0] if response.choices else None
        if choice is None or choice.finish_reason == "length":
            raise RewriteFailed("no complete rewrite")
        lines = (choice.message.content or "").strip().splitlines()
        rewritten = lines[0].strip().strip("\"'“”").strip() if lines else ""
        if not rewritten or len(rewritten) > self.max_chars:
            raise RewriteFailed("empty or overlong rewrite")
        if not rewritten.endswith("?"):
            # A sentence instead of a question (a refusal, a remark): don't search on it.
            raise RewriteFailed("reply is not a question")
        return rewritten
