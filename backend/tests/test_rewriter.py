"""The OpenRouter rewriter against a stub client (no network)."""

from types import SimpleNamespace

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


@pytest.mark.parametrize(
    "content, finish",
    [("", "stop"), ("   ", "stop"), ("What is the cap", "length"), ("x" * 300, "stop")],
)
def test_empty_truncated_or_overlong_replies_fail(content, finish):
    r, _ = rewriter(content, finish)
    with pytest.raises(RewriteFailed):
        r.rewrite("q", HISTORY)
