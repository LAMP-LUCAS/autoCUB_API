from types import SimpleNamespace

import pytest

from autocub_mcp.auth import resolve_api_key
from autocub_mcp.client import AuthError


class FakeHeaders(dict):
    def getlist(self, name):
        value = self.get(name.lower())
        if value is None:
            return []
        return value if isinstance(value, list) else [value]


class FakeRequest:
    def __init__(self, headers):
        self.headers = FakeHeaders({k.lower(): v for k, v in headers.items()})


def context_for(headers):
    return SimpleNamespace(request_context=SimpleNamespace(request=FakeRequest(headers)))


def test_http_requires_one_key():
    with pytest.raises(AuthError):
        resolve_api_key(context_for({}))
    with pytest.raises(AuthError):
        resolve_api_key(context_for({"X-API-KEY": ["a", "b"]}))
    assert resolve_api_key(context_for({"x-api-key": "caller"}), "ignored") == "caller"


def test_stdio_keeps_explicit_compatibility_key():
    assert resolve_api_key(None, "local-key") == "local-key"
