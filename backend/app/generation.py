"""Compose an answer from the passages that cleared the gate (F4; REQ-G1, G2, G6, G7).

The model gets the versioned system prompt, the numbered current passages, the question and
(when one applies) the D6 conflict note. Nothing else: no other policy source (REQ-G2).
"""

from dataclasses import dataclass
from typing import Protocol

import openai
from openai import OpenAI

from app.retrieval import Hit


class GenerationTimeout(Exception):
    pass


class GenerationFailed(Exception):
    pass


@dataclass(frozen=True)
class GenerationResult:
    text: str
    model: str
    prompt_version: str
    prompt_tokens: int | None
    completion_tokens: int | None


class Generator(Protocol):
    def generate(
        self,
        question: str,
        passages: list[Hit],
        conflict_note: str | None = None,
        context: list[dict] | None = None,
    ) -> GenerationResult: ...


def format_passages(passages: list[Hit]) -> str:
    blocks = []
    for number, hit in enumerate(passages, start=1):
        p = hit.payload
        heading = f"[{number}] {p['title']} v{p['version']}, §{p['section']} {p['section_title']}"
        blocks.append(f"{heading}\n{p['text']}")
    return "\n\n".join(blocks)


def build_messages(
    question: str, passages: list[Hit], conflict_note: str | None, system_prompt: str
) -> list[dict]:
    user = f"Policy passages:\n\n{format_passages(passages)}\n\n"
    if conflict_note:
        user += f"Conflict note: {conflict_note}\n\n"
    user += f"Question: {question}"
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}]


class OpenRouterGenerator:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
        reasoning_enabled: bool,
        prompt_version: str,
        system_prompt: str,
    ) -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)
        self.model, self.temperature, self.max_tokens = model, temperature, max_tokens
        self.reasoning_enabled = reasoning_enabled
        self.prompt_version, self.system_prompt = prompt_version, system_prompt

    def generate(self, question, passages, conflict_note=None, context=None) -> GenerationResult:
        messages = build_messages(question, passages, conflict_note, self.system_prompt)
        if context:
            messages = [messages[0], *context, messages[1]]
        # A reasoning model can spend the whole token budget thinking and return nothing.
        # CHAT_REASONING_ENABLED=false asks OpenRouter to switch reasoning off.
        extra_body = None if self.reasoning_enabled else {"reasoning": {"enabled": False}}
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                extra_body=extra_body,
            )
        except openai.APITimeoutError as exc:  # before APIConnectionError: it is a subclass
            raise GenerationTimeout(type(exc).__name__) from exc
        except openai.OpenAIError as exc:
            raise GenerationFailed(type(exc).__name__) from exc
        if not response.choices or not response.choices[0].message.content:
            raise GenerationFailed("empty completion")
        if response.choices[0].finish_reason == "length":
            # Cut off at CHAT_MAX_TOKENS: a half answer can drop its citations, never show it.
            raise GenerationFailed("truncated completion")
        usage = getattr(response, "usage", None)
        return GenerationResult(
            text=response.choices[0].message.content.strip(),
            model=response.model or self.model,
            prompt_version=self.prompt_version,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
        )
