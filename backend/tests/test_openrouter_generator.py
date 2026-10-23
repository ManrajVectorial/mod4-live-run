"""The OpenRouter generator against a stub client (no network)."""

from types import SimpleNamespace

import pytest

from app.generation import GenerationFailed, OpenRouterGenerator
from tests.api_support import ANSWERABLE


def completion(content, finish_reason="stop", model="anthropic/claude-haiku-5.5"):
    return SimpleNamespace(
        model=model,
        choices=[
            SimpleNamespace(finish_reason=finish_reason, message=SimpleNamespace(content=content))
        ],
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20),
    )


class StubCompletions:
    def __init__(self, response):
        self.response = response
        self.kwargs: dict = {}

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def generator(response, reasoning_enabled=False):
    g = OpenRouterGenerator(
        api_key="k",
        base_url="http://127.0.0.1:1",
        model="anthropic/claude-haiku-5.5",
        temperature=0.0,
        max_tokens=600,
        timeout=6.0,
        reasoning_enabled=reasoning_enabled,
        prompt_version="answer-v1",
        system_prompt="rules",
    )
    stub = StubCompletions(response)
    g.client = SimpleNamespace(chat=SimpleNamespace(completions=stub))
    return g, stub


def test_reasoning_off_is_requested_when_disabled():
    g, stub = generator(completion("Yes [1]."), reasoning_enabled=False)
    result = g.generate("Q?", ANSWERABLE[:1])
    assert stub.kwargs["extra_body"] == {"reasoning": {"enabled": False}}
    assert stub.kwargs["max_tokens"] == 600 and stub.kwargs["temperature"] == 0.0
    assert (result.text, result.model, result.prompt_version) == (
        "Yes [1].",
        "anthropic/claude-haiku-5.5",
        "answer-v1",
    )
    assert (result.prompt_tokens, result.completion_tokens) == (100, 20)


def test_reasoning_left_to_model_default_when_enabled():
    g, stub = generator(completion("Yes [1]."), reasoning_enabled=True)
    g.generate("Q?", ANSWERABLE[:1])
    assert stub.kwargs["extra_body"] is None  # no reasoning option sent


def test_truncated_completion_is_a_failure_not_an_answer():
    g, _ = generator(completion("A claim of £75 or more needs line-manag", finish_reason="length"))
    with pytest.raises(GenerationFailed, match="truncated"):
        g.generate("Q?", ANSWERABLE[:1])


def test_empty_completion_is_a_failure():
    g, _ = generator(completion("", finish_reason="length"))
    with pytest.raises(GenerationFailed):
        g.generate("Q?", ANSWERABLE[:1])
