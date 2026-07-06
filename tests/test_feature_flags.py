"""Behavior of the ALLOW_REGENERATE feature flag.

The flag decides whether the ``regenerate`` tool is exposed. It is read at
import time, so these tests reload the server module with the environment set
each way. The rest of the suite runs with the flag on (see ``conftest.py``), so
each test restores the enabled state before returning.
"""

from __future__ import annotations

import asyncio
import importlib

from fastmcp import Client

from random_mcp_server import server

ALWAYS_ON = {"server_info", "list_records", "get_record", "count_records"}


def _tool_names(module) -> set[str]:
    async def run():
        async with Client(module.mcp) as client:
            return {t.name for t in await client.list_tools()}

    return asyncio.run(run())


def _reload_with(monkeypatch, value: str | None):
    if value is None:
        monkeypatch.delenv("ALLOW_REGENERATE", raising=False)
    else:
        monkeypatch.setenv("ALLOW_REGENERATE", value)
    return importlib.reload(server)


def test_regenerate_hidden_by_default(monkeypatch):
    try:
        module = _reload_with(monkeypatch, None)
        assert module.ALLOW_REGENERATE is False
        names = _tool_names(module)
        assert "regenerate" not in names
        assert ALWAYS_ON <= names
        # server_info advertises the flag so clients can tell reseeding is off.
        async def info():
            async with Client(module.mcp) as client:
                return (await client.call_tool("server_info", {})).data

        assert asyncio.run(info())["allow_regenerate"] is False
    finally:
        _reload_with(monkeypatch, "1")


def test_regenerate_exposed_when_enabled(monkeypatch):
    for truthy in ("1", "true", "on"):
        module = _reload_with(monkeypatch, truthy)
        assert module.ALLOW_REGENERATE is True
        assert "regenerate" in _tool_names(module)
    _reload_with(monkeypatch, "1")
