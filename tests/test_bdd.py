"""pytest-bdd layer mirroring random-server's Cucumber features.

The REST server describes its behavior with Gherkin `.feature` files driven by
Cucumber. This mirrors that suite for the MCP server: the `/v1/<kind>` endpoints
map to the ``list_records`` tool and the root health check maps to
``server_info``. Steps drive the tools through an in-memory FastMCP client — the
same approach as ``test_server.py``.

(random-server's ``auth.feature`` is intentionally not mirrored: the optional
``x-api-key`` guard is not ported to the MCP server.)
"""

from __future__ import annotations

import asyncio

import pytest
from fastmcp import Client
from pytest_bdd import given, parsers, scenarios, then, when

from random_mcp_server import server

# Bind every .feature file under tests/features/.
scenarios("features")


def _call(tool: str, **args):
    """Invoke a tool through an in-memory client and return its structured data."""

    async def run():
        async with Client(server.mcp) as client:
            return (await client.call_tool(tool, args)).data

    return asyncio.run(run())


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@pytest.fixture
def context() -> dict:
    return {}


# --- Given -----------------------------------------------------------------


@given("the MCP server is available")
def server_available(context):
    assert server.mcp is not None


# --- When ------------------------------------------------------------------


@when("the server_info tool is called")
def call_server_info(context):
    context["result"] = _call("server_info")


@when(parsers.parse('the "{kind}" records are listed'))
def list_kind(context, kind):
    context["result"] = _call("list_records", kind=kind)


# --- Then ------------------------------------------------------------------


@then(parsers.parse('the result should contain a "{prop}" property'))
def result_contains_property(context, prop):
    result = context["result"]
    assert prop in result
    assert result[prop] not in (None, "")


@then("the result should be a list with at least one item")
def result_nonempty_list(context):
    result = context["result"]
    assert isinstance(result, list)
    assert len(result) >= 1


@then("the result should be an empty list")
def result_empty_list(context):
    assert context["result"] == []


@then(parsers.parse('each item should have "{first}" and "{second}" properties'))
def each_item_has_properties(context, first, second):
    for item in context["result"]:
        assert first in item, f"missing '{first}' in {item}"
        assert second in item, f"missing '{second}' in {item}"


@then(parsers.parse('the "{prop}" property of each item should be "{value}"'))
def each_item_property_equals(context, prop, value):
    for item in context["result"]:
        assert item[prop] == value


@then(parsers.parse('the "{prop}" property of each item should be numeric'))
def each_item_property_numeric(context, prop):
    for item in context["result"]:
        assert _is_number(item[prop]), f"{prop}={item[prop]!r} is not numeric"


@then(parsers.parse('the "{prop}" property of each item should be a non-empty string'))
def each_item_property_nonempty_string(context, prop):
    for item in context["result"]:
        assert isinstance(item[prop], str) and item[prop] != ""
