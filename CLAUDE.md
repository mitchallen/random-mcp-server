# random-mcp-server — notes for Claude

An MCP server that returns random JSON data (people, words, values, coords, and
an always-empty kind). It is a Python / FastMCP adaptation of the sibling
Node/Express REST API [`random-server`](../random-server): each REST route
family becomes an MCP tool. Built with **uv**, **FastMCP**, **pytest**, and
**make**; multi-stage Docker on a distroless Chainguard/Wolfi Python base
(`cgr.dev/chainguard/python`) for a near-zero-CVE image.

## Layout

- `src/random_mcp_server/generators.py` — `RandomFactory`, deterministic/seedable
  record builders that mirror the shapes chance.js produces in the REST server.
- `src/random_mcp_server/server.py` — the FastMCP server (`mcp`), its tools, and
  the `main()` console-script entry point (`random-mcp-server`).
- `tests/` — pytest suite. `test_server.py` drives the tools through an
  **in-memory FastMCP `Client`** (no network, no subprocess).

## Conventions

- **Dependencies / venv:** managed by uv. `make install` runs `uv sync` (creates
  `.venv`). `uv.lock` is committed and the Dockerfile installs `--frozen` from it,
  so run `make lock` (or `uv lock`) whenever `pyproject.toml` deps change.
- **Running:** `make run` (stdio, the default MCP transport), `make run-http`
  (streamable HTTP on `PORT`, default 8000), `make dev` (FastMCP Inspector). The
  transport is chosen by `MCP_TRANSPORT` (`stdio` | `http` | `sse`).
- **Tests:** `make test` → `uv run pytest`.
- **Seeding:** pools are generated once at start-up from `RandomFactory`, so a
  given `id` is stable. `RANDOM_SEED` (or the `regenerate` tool's `seed` arg)
  makes output reproducible; `RANDOM_COUNT` sets pool size (default 25).
- **`regenerate` is opt-in.** It reseeds the single process-wide pool shared by
  every connected client, so it's gated behind `ALLOW_REGENERATE` (off by
  default) — when unset the tool isn't registered (absent from the schema), so
  one user can't reshuffle records out from under others on a shared instance.
  The test suite enables it via `tests/conftest.py`; `test_feature_flags.py`
  covers the default-off/hidden path by reloading the module with the env unset.
- **Docker:** the image defaults to HTTP transport (`MCP_TRANSPORT=http`,
  `HOST=0.0.0.0`, `PORT=8000`) so it's reachable on a published port. The base is
  distroless Chainguard/Wolfi Python (`cgr.dev/chainguard/python`), which already
  runs as the non-root `nonroot` user (uid 65532) and has no shell / package
  manager. The venv is built on the matching `-dev` image so its interpreter
  symlink resolves at runtime. `make scan` should report 0 CRITICAL/HIGH.
- **Releasing:** `make release` (`BUMP=patch|minor|major`, default patch) bumps
  the version, commits, tags `vX.Y.Z`, and pushes — the tag triggers the GHCR +
  Docker Hub publish workflows. `make release` does **not** touch `CHANGELOG.md`,
  so add the new version's entry (Keep a Changelog format, top of the file)
  **before** running it, so the release commit/tag captures the changelog. If
  you forget, land it as a follow-up doc commit — don't re-tag.

## Tool ↔ REST mapping

| REST route             | MCP tool                       |
| ---------------------- | ------------------------------ |
| `GET /`                | `server_info()`                |
| `GET /v1/<kind>`       | `list_records(kind, count?)`   |
| `GET /v1/<kind>/count` | `count_records(kind)`          |
| `GET /v1/<kind>/:id`   | `get_record(kind, id)` (1-based) |
| _(restart to reseed)_  | `regenerate(seed?)` (opt-in — `ALLOW_REGENERATE`) |

`kind` ∈ {`people`, `words`, `values`, `coords`, `empty`}.

## Gotchas

- `@mcp.tool` replaces the module-level function with a Tool object; unit-test
  tools through the in-memory `Client`, not by calling the name directly.
- The REST server's optional `x-api-key` auth is **not** ported — MCP transports
  handle auth differently. Add FastMCP auth if a networked deployment needs it.
