"""Tests for the MCP tool layer, driven through an in-memory FastMCP client."""

from __future__ import annotations

import asyncio

from fastmcp import Client

from random_mcp_server import server


def _call(tool: str, **args):
    """Invoke a tool through an in-memory client and return its structured data."""

    async def run():
        async with Client(server.mcp) as client:
            result = await client.call_tool(tool, args)
            return result.data

    return asyncio.run(run())


def test_tools_are_registered():
    async def run():
        async with Client(server.mcp) as client:
            return {t.name for t in await client.list_tools()}

    names = asyncio.run(run())
    assert {
        "server_info", "list_records", "get_record", "count_records", "regenerate",
    } <= names


def test_server_info():
    info = _call("server_info")
    assert info["status"] == "OK"
    assert info["app"] == server.APP_NAME
    assert "people" in info["kinds"]
    assert info["source"] == "https://github.com/mitchallen/random-mcp-server"
    assert info["author"] == "Mitch Allen (https://mitchallen.com)"


def test_count_matches_default():
    assert _call("count_records", kind="people")["count"] == server.DEFAULT_COUNT
    assert _call("count_records", kind="empty")["count"] == 0


def test_get_record_is_stable():
    first = _call("get_record", kind="people", id=1)
    again = _call("get_record", kind="people", id=1)
    assert first == again
    assert first["type"] == "people"


def test_list_records_respects_count():
    assert len(_call("list_records", kind="words", count=3)) == 3
    assert len(_call("list_records", kind="words")) == server.DEFAULT_COUNT


def test_get_record_out_of_range_errors():
    try:
        _call("get_record", kind="people", id=9999)
    except Exception as exc:  # ToolError surfaces as a client-side error
        assert "out of range" in str(exc)
        return
    raise AssertionError("expected an out-of-range error")


def test_regenerate_with_seed_is_reproducible():
    a = _call("regenerate", seed=123)
    first = _call("get_record", kind="people", id=1)
    b = _call("regenerate", seed=123)
    assert a["seed"] == b["seed"] == 123
    assert _call("get_record", kind="people", id=1) == first
