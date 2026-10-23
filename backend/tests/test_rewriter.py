"""The OpenRouter rewriter against a stub client (no network)."""

from types import SimpleNamespace

import httpx2
import openai
import pytest

from app.rewrite import OpenRouterRewriter, RewriteFailed


def completion(content, finish_reason="stop"):
    return SimpleNamespace(
        model="m",
        choices=[
            SimpleNamespace(finish_reason=finish_reason, message=SimpleNamespace(content=content))
        ],
        usage=None,
    )


def rewriter(content, finish_reason="stop", max_chars=200):
    r = OpenRouterRewriter(
        api_key="k",
        base_url="http://127.0.0.1:1",
        model="m",
        max_tokens=100,
        timeout=1.0,
        reasoning_enabled=False,
        prompt_version="rewrite-test",
        system_prompt="rewrite rules",
        max_chars=max_chars,
    )
    calls = []
    r.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kw: calls.append(kw) or completion(content, finish_reason)
            )
        )
    )
    return r, calls


HISTORY = [
    {"role": "user", "content": "Cap for London?"},
    {"role": "assistant", "content": "£250."},
]


def test_sends_history_then_the_question_and_cleans_the_reply():
    r, calls = rewriter('"What is the accommodation cap for Singapore?"\n')
    assert (
        r.rewrite("And for Singapore?", HISTORY) == "What is the accommodation cap for Singapore?"
    )
    (kw,) = calls
    assert kw["messages"][0] == {"role": "system", "content": "rewrite rules"}
    assert kw["messages"][1:3] == HISTORY
    assert (
        kw["messages"][-1]["role"] == "user"
        and "And for Singapore?" in kw["messages"][-1]["content"]
    )
    assert kw["temperature"] == 0 and kw["extra_body"] == {"reasoning": {"enabled": False}}


def test_keeps_only_the_first_line():
    r, _ = rewriter("Can I expense my partner's flight?\nNote: off topic.")
    assert r.rewrite("Partner?", HISTORY) == "Can I expense my partner's flight?"


def test_a_reply_that_is_not_a_question_fails():
    r, _ = rewriter("I don't have the earlier conversation, so I can't tell what that refers to.")
    with pytest.raises(RewriteFailed, match="not a question"):
        r.rewrite("And that amount?", HISTORY)


def failing_rewriter(error):
    r, _ = rewriter("unused")

    def create(**kw):
        raise error

    r.client.chat.completions.create = create
    return r


def test_provider_timeout_and_error_are_told_apart_from_an_unusable_reply():
    """FND-1: a provider failure means the model is down, not that the reply was bad."""
    request = httpx2.Request("POST", "http://127.0.0.1:1/chat/completions")
    with pytest.raises(RewriteFailed) as timeout:
        failing_rewriter(openai.APITimeoutError(request=request)).rewrite("q", HISTORY)
    assert timeout.value.provider == "timeout"
    with pytest.raises(RewriteFailed) as error:
        failing_rewriter(openai.APIConnectionError(request=request)).rewrite("q", HISTORY)
    assert error.value.provider == "error"


def test_an_unusable_reply_is_not_a_provider_failure():
    r, _ = rewriter("That is not a question.")
    with pytest.raises(RewriteFailed) as failed:
        r.rewrite("And that amount?", HISTORY)
    assert failed.value.provider is None


@pytest.mark.parametrize(
    "content, finish",
    [("", "stop"), ("   ", "stop"), ("What is the cap", "length"), ("x" * 300, "stop")],
)
def test_empty_truncated_or_overlong_replies_fail(content, finish):
    r, _ = rewriter(content, finish)
    with pytest.raises(RewriteFailed):
        r.rewrite("q", HISTORY)
