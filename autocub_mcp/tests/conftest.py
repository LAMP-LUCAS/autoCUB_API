import socket

import pytest

from autocub_mcp.config import Settings, get_config


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    for name in Settings.model_fields:
        monkeypatch.delenv(f"AUTOCUB_{name.upper()}", raising=False)
    get_config.cache_clear()
    monkeypatch.setenv("AUTOCUB_BASE_URL", "https://gateway.example")
    monkeypatch.setenv("AUTOCUB_RETRIES", "3")

    def no_network(*args, **kwargs):
        raise AssertionError("Network is forbidden in unit tests")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    yield
    get_config.cache_clear()
