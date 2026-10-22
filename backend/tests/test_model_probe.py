"""The model probe must prove the key works, not just that the provider is up."""

import urllib.error
from email.message import Message

import pytest

from app.health import ModelProbe


class Recorder:
    def __init__(self, status: int = 200) -> None:
        self.status = status
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        if self.status != 200:
            raise urllib.error.HTTPError(request.full_url, self.status, "x", Message(), None)
        return self.status


def test_probe_calls_authenticated_endpoint_with_key():
    fetch = Recorder()
    ModelProbe("https://provider.test/api/v1/", "sk-test", timeout=0.5, fetch=fetch).check()
    ((request, timeout),) = fetch.requests
    assert request.full_url == "https://provider.test/api/v1/key"
    assert request.get_header("Authorization") == "Bearer sk-test"
    assert timeout == 0.5


def test_probe_fails_when_key_is_rejected():
    with pytest.raises(urllib.error.HTTPError):
        ModelProbe("https://provider.test/api/v1", "bad", timeout=0.5, fetch=Recorder(401)).check()


def test_probe_refuses_non_http_url():
    with pytest.raises(ValueError):
        ModelProbe("file:///etc", "k", timeout=0.5, fetch=Recorder()).check()
