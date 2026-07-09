"""FastMCP server exposing the random-server API as MCP tools.

The original REST server seeds a fixed pool of records at start-up and serves
them through ``/v1/<kind>``, ``/v1/<kind>/count`` and ``/v1/<kind>/:id`` routes.
This server mirrors that: it builds seeded pools once at start-up and exposes
``list_records`` / ``get_record`` / ``count_records`` (parameterized by ``kind``),
plus ``server_info`` (the ``/`` health check) and ``regenerate`` (restarting the
REST server to reseed).

Environment variables (mirroring the REST server where sensible):
  APP_NAME          display name reported by ``server_info`` (default: random-mcp-server)
  RANDOM_COUNT      records generated per kind at start-up (default: 25)
  RANDOM_SEED       fixed seed for reproducible pools (default: random)
  ALLOW_REGENERATE  expose the ``regenerate`` tool (default: off). It reseeds the
                    pool shared by every client on the instance, so it stays off
                    by default to keep one user from reshuffling records out from
                    under others on a shared deployment.
  MCP_TRANSPORT     transport for ``main``: stdio (default), http, or sse
  HOST, PORT        bind address for http/sse transports (default: 127.0.0.1:8000)
"""

from __future__ import annotations

import os
import time
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# Absolute import (not `from .generators`) so the module also loads when the
# FastMCP CLI (`fastmcp inspect`/`list`/`call`, i.e. `make inspect`) imports this
# file by path rather than as part of the installed package.
from random_mcp_server.generators import KINDS, RandomFactory

def _env_flag(name: str, default: bool = False) -> bool:
    """Parse a boolean-ish environment variable (1/true/yes/on ⇒ True)."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


APP_NAME = os.environ.get("APP_NAME", "random-mcp-server")
DEFAULT_COUNT = int(os.environ.get("RANDOM_COUNT", "25"))
_SEED_ENV = os.environ.get("RANDOM_SEED")
# Off by default: `regenerate` reseeds the pool shared by every client on this
# instance, so a shared deployment shouldn't let one caller reshuffle everyone
# else's records. Set ALLOW_REGENERATE=1 for single-user / per-session setups.
ALLOW_REGENERATE = _env_flag("ALLOW_REGENERATE", default=False)

try:
    APP_VERSION = _pkg_version("random-mcp-server")
except PackageNotFoundError:  # running from source without an install
    APP_VERSION = "0.0.0"

# Literal drives the tool schema so clients see the valid kinds as an enum.
Kind = Literal["people", "words", "values", "coords", "empty"]

_START = time.monotonic()
_factory = RandomFactory(int(_SEED_ENV) if _SEED_ENV else None)
_pools: dict[str, list[dict[str, Any]]] = {}


def _build_pools() -> None:
    """(Re)build the seeded record pool for every kind."""
    global _pools
    _pools = {kind: _factory.build_pool(kind, DEFAULT_COUNT) for kind in KINDS}


_build_pools()


def _uptime_hhmmss() -> str:
    """Server uptime as HH:MM:SS, mirroring @mitchallen/uptime.toHHMMSS()."""
    total = int(time.monotonic() - _START)
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


mcp = FastMCP(
    name=APP_NAME,
    # Report the package version; without this FastMCP falls back to its own
    # framework version in the MCP handshake / `fastmcp inspect`.
    version=APP_VERSION,
    instructions=(
        "Returns random JSON things. Use list_records / get_record / count_records "
        "with a kind of people, words, values, coords, or empty. Records are seeded "
        "at start-up so a given id is stable until you call regenerate."
    ),
)


@mcp.tool
def server_info() -> dict[str, Any]:
    """Health/status of the server (the REST server's ``GET /`` route)."""
    return {
        "status": "OK",
        "app": APP_NAME,
        "version": APP_VERSION,
        "uptime": _uptime_hhmmss(),
        "kinds": list(KINDS),
        "count": DEFAULT_COUNT,
        "seed": _factory.seed,
        "allow_regenerate": ALLOW_REGENERATE,
        "source": "https://github.com/mitchallen/random-mcp-server",
        "author": "Mitch Allen (https://mitchallen.com)",
    }


@mcp.tool
def list_records(kind: Kind, count: int | None = None) -> list[dict[str, Any]]:
    """Return the seeded pool of records for ``kind``.

    Pass ``count`` to cap how many are returned (from the front of the pool);
    omit it to return the whole pool. ``empty`` always returns ``[]``.
    """
    pool = _pools[kind]
    if count is None:
        return pool
    if count < 0:
        raise ToolError("count must be >= 0")
    return pool[:count]


@mcp.tool
def get_record(kind: Kind, id: int) -> dict[str, Any]:
    """Return a single record from ``kind`` by 1-based ``id`` (the ``/:id`` route)."""
    pool = _pools[kind]
    if id < 1 or id > len(pool):
        raise ToolError(f"id {id} out of range [1 - {len(pool)}] for kind '{kind}'")
    return pool[id - 1]


@mcp.tool
def count_records(kind: Kind) -> dict[str, int]:
    """Return the number of records available for ``kind`` (the ``/count`` route)."""
    return {"count": len(_pools[kind])}


def regenerate(seed: int | None = None) -> dict[str, Any]:
    """Reseed and rebuild every pool (like restarting the REST server).

    Pass a fixed ``seed`` for reproducible pools, or omit it for a random seed.
    """
    _factory.reseed(seed)
    _build_pools()
    return {"status": "regenerated", "seed": _factory.seed, "count": DEFAULT_COUNT}


# `regenerate` rebuilds the pool shared by every client on this instance, so it
# is registered only when ALLOW_REGENERATE is set. When off, the tool is absent
# from the schema entirely — clients can't list or call it — so one user can't
# reshuffle records out from under others on a shared server. Enable it for
# single-user or per-session (client-launched stdio) deployments.
if ALLOW_REGENERATE:
    regenerate = mcp.tool(regenerate)


def main() -> None:
    """Console-script entry point. Honors MCP_TRANSPORT / HOST / PORT."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport in ("http", "sse"):
        mcp.run(
            transport=transport,
            host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "8000")),
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
