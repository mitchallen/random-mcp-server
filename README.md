# random-mcp-server

[![GitHub tag](https://img.shields.io/github/v/tag/mitchallen/random-mcp-server?sort=semver&label=version)](https://github.com/mitchallen/random-mcp-server/tags) [![Docker Hub](https://img.shields.io/docker/v/mitchallen/random-mcp-server?sort=semver&label=docker%20hub)](https://hub.docker.com/r/mitchallen/random-mcp-server) [![test](https://github.com/mitchallen/random-mcp-server/actions/workflows/test.yml/badge.svg)](https://github.com/mitchallen/random-mcp-server/actions/workflows/test.yml) [![bdd](https://github.com/mitchallen/random-mcp-server/actions/workflows/bdd.yml/badge.svg)](https://github.com/mitchallen/random-mcp-server/actions/workflows/bdd.yml)

An [MCP](https://modelcontextprotocol.io) server that returns random JSON
things — people, words, values, coordinates, and an always-empty list. It is a
Python / [FastMCP](https://gofastmcp.com) adaptation of the Node/Express
[`random-server`](../random-server) REST API: each REST route family becomes an
MCP tool.

Built with **Python**, **[uv](https://docs.astral.sh/uv/)**, **FastMCP**, and
**make**.

* * *

## How the REST API maps to MCP

The REST server seeds a fixed pool of records when it starts and serves them at
`/v1/<kind>`, `/v1/<kind>/count`, and `/v1/<kind>/:id`. This server does the
same, exposing the pool through a small set of tools parameterized by `kind`
(`people`, `words`, `values`, `coords`, `empty`):

| REST route                | MCP tool                              |
| ------------------------- | ------------------------------------- |
| `GET /`                   | `server_info()`                       |
| `GET /v1/<kind>`          | `list_records(kind, count?)`          |
| `GET /v1/<kind>/count`    | `count_records(kind)`                 |
| `GET /v1/<kind>/:id`      | `get_record(kind, id)` (1-based)      |
| _(restart to reseed)_     | `regenerate(seed?)` — **opt-in**      |

Records are **seeded at start-up**, so a given `id` is stable until you call
`regenerate`. Pass a fixed `seed` (tool arg or `RANDOM_SEED`) for reproducible
data.

The `regenerate` tool is **disabled by default** — see
[The `regenerate` tool is opt-in](#the-regenerate-tool-is-opt-in).

### Differences from `random-server`

- **No `x-api-key` auth.** The REST server's optional `API_KEY` guard on `/v1`
  routes is **not** ported — MCP transports handle authentication differently
  (add [FastMCP auth](https://gofastmcp.com/servers/auth/authentication) if a
  networked deployment needs it). The `APP_NAME`, seeding, and per-kind count
  behavior are preserved.
- **No Swagger UI.** The `/api-docs` explorer has no MCP equivalent; tool
  schemas are discoverable through the MCP protocol itself (e.g. `make dev`).

### Example records

```jsonc
// get_record(kind="people", id=1)
{ "type": "people", "prefix": "Mr.", "first": "Augustus", "last": "Gomez",
  "age": 42, "birthday": "7/8/1959", "gender": "male", "zip": "74948-0928",
  "ssnFour": "0791", "phone": "(509) 504-8066", "email": "zeti@tipe.cv" }

// get_record(kind="words", id=1)   -> { "type": "words", "value": "cezuwdi" }
// get_record(kind="values", id=1)  -> { "type": "values", "name": "dafe", "value": -415365907192.2176 }
// get_record(kind="coords", id=1)  -> { "type": "coords", "latitude": 88.43647, "longitude": -93.31203 }
```

* * *

## Determinism & idempotency of records

Each server **process** builds one pool of records per kind when it starts, then
serves that pool for the life of the process. What stays stable and what changes
follows from that:

- **Within a running instance, records are idempotent.** For as long as the
  process is up, `get_record(kind, id)` returns the same record, and
  `list_records` returns the same pool in the same order. Ask for person `1`
  today and it's identical on the next call — until the pool is rebuilt (below).
- **A reboot/restart reshuffles — unless you pin a seed.** With no `RANDOM_SEED`
  set, the factory picks a **random** seed at start-up, so restarting the server
  (or launching a fresh container) yields a **different** pool. Set
  `RANDOM_SEED` to a fixed value and every restart rebuilds the **same** pool, so
  records survive reboots.
- **A shared instance shows everyone the same records.** The pool lives in the
  process's memory, so all clients connected to the **same** long-running
  instance ([Option B / C](#using-a-published-image-or-a-remote-server)) see the
  same records — no seed required for them to agree, because they're reading one
  shared pool. Two *separate* unseeded instances (or two people each running
  their own) will **not** match unless both pin the same `RANDOM_SEED`.
- **Client-launched stdio gets a fresh pool per session.** When a client starts
  the server itself ([local dev](#using-with-an-mcp-client--local-development-from-source)
  or [Docker/stdio, Option A](#option-a--docker-image-client-launches-it-stdio)),
  each session is its own process with its own start-up seed. Unseeded, those
  sessions won't agree with each other; set `RANDOM_SEED` to make them line up.
- **`regenerate` rebuilds the shared pool for everyone on that instance.**
  `regenerate(seed=N)` is reproducible (same seed → same pool); `regenerate()`
  with no argument picks a new random seed. Either way it **mutates the shared
  state**, so on a multi-client instance it changes the records every other
  connected client sees too. Because of that it is **disabled by default**
  (see [below](#the-regenerate-tool-is-opt-in)).
- **`server_info` reports the active `seed`.** Capture that value and feed it
  back via `RANDOM_SEED` (at start-up) or `regenerate(seed=…)` to reproduce a
  pool you liked later.

| Scenario                                                        | Same records? |
| --------------------------------------------------------------- | ------------- |
| Same instance, repeated calls, no restart                       | ✅ Yes         |
| Same long-running instance, different clients                   | ✅ Yes         |
| After a restart / new container, **no** `RANDOM_SEED`           | ❌ No (reshuffled) |
| After a restart / new container, **fixed** `RANDOM_SEED`        | ✅ Yes         |
| Two separate unseeded instances                                 | ❌ No          |
| Two instances, both pinned to the same `RANDOM_SEED`            | ✅ Yes         |
| After `regenerate()` (no seed)                                  | ❌ No (reshuffled) |
| After `regenerate(seed=N)` with a seed you used before          | ✅ Yes         |

The two `regenerate` rows assume `ALLOW_REGENERATE` is set; otherwise the tool is
unavailable ([opt-in](#the-regenerate-tool-is-opt-in)) and only a restart rebuilds
the pool.

### The `regenerate` tool is opt-in

Because `regenerate` reseeds the **one shared pool** the whole process serves,
on a multi-user instance a single caller can reshuffle the records out from
under everyone else — no isolation, last-writer-wins. To prevent that, the tool
is **disabled by default**: when `ALLOW_REGENERATE` is unset the tool is not
registered at all, so it doesn't appear in the tool list and can't be called
(`server_info` reports `"allow_regenerate": false`).

Enable it only where reseeding is safe:

```sh
ALLOW_REGENERATE=1 make run        # single-user stdio
docker run --rm -p 8000:8000 -e ALLOW_REGENERATE=1 ghcr.io/mitchallen/random-mcp-server:latest
```

Guidance by deployment shape:

- **Shared long-running instance** ([Option B / C](#using-a-published-image-or-a-remote-server)) —
  leave it **off**. Pin `RANDOM_SEED` if you need a specific reproducible pool,
  and treat the data as read-only. This is why the Docker image (which defaults
  to shared HTTP) ships with `regenerate` off.
- **Per-session / single-user** (client-launched [stdio](#option-a--docker-image-client-launches-it-stdio)
  or [local dev](#using-with-an-mcp-client--local-development-from-source)) — each
  client gets its own process, so reseeding only affects that caller. Safe to set
  `ALLOW_REGENERATE=1`.

* * *

## Quick start

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
make install     # create .venv and sync deps
make test        # run the test suite
make run         # run the server over stdio
```

`make help` lists every target.

* * *

## Running the server

### stdio (default — for MCP clients that launch the server)

```sh
uv run random-mcp-server
# or
make run
```

### Streamable HTTP (for networked clients / containers)

```sh
make run-http            # PORT defaults to 8000
PORT=9000 make run-http
```

### Inspect the server

```sh
make inspect             # print a summary: name, version, tool count
make dev                 # launch the interactive FastMCP Inspector (web UI)
```

* * *

## Configuration

All configuration is via environment variables:

| Variable        | Default            | Purpose                                              |
| --------------- | ------------------ | ---------------------------------------------------- |
| `APP_NAME`         | `random-mcp-server`| Name reported by `server_info`                       |
| `RANDOM_COUNT`     | `25`               | Records generated per kind at start-up               |
| `RANDOM_SEED`      | _(random)_         | Fixed seed for reproducible pools                    |
| `ALLOW_REGENERATE` | _(off)_            | Expose the `regenerate` tool (see [below](#the-regenerate-tool-is-opt-in)) |
| `MCP_TRANSPORT`    | `stdio`            | `stdio`, `http`, or `sse`                            |
| `HOST`             | `127.0.0.1`        | Bind address for `http`/`sse`                        |
| `PORT`             | `8000`             | Bind port for `http`/`sse`                           |

`ALLOW_REGENERATE` accepts `1`/`true`/`yes`/`on` (case-insensitive) to enable.

* * *

## Using with an MCP client — local development (from source)

**This section is for developers working from a checkout of this repo.** It runs
the server straight from your local source via uv, so code changes take effect on
the next launch. If you only have the Docker image or a remote deployment, skip to
[Using a published image or a remote server](#using-a-published-image-or-a-remote-server).

Point a stdio-based client (e.g. Claude Desktop, Claude Code) at the console
script. Example `claude_desktop_config.json` entry using uv:

```jsonc
{
  "mcpServers": {
    "random": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/random-mcp-server", "random-mcp-server"]
    }
  }
}
```

With Claude Code:

```sh
claude mcp add random -- uv run --directory "$PWD" random-mcp-server
```

Confirm it's connected with `claude mcp list` (or `/mcp` inside a session).

### Example prompts (Claude Code)

Once the server is added, just ask in plain language — Claude picks the right
tool. The tool it invokes is shown in parentheses.

- "Is the random server up? What version is it?" → (`server_info`)
- "Give me 3 random people." → (`list_records` with `kind="people"`, `count=3`)
- "Show me the first random person." → (`get_record` with `kind="people"`, `id=1`)
- "How many random coordinates are available?" → (`count_records` with `kind="coords"`)
- "List all the random words." → (`list_records` with `kind="words"`)
- "Grab 5 random coordinates and drop them on a map." → (`list_records` with `kind="coords"`, `count=5`)
- "Reseed the random data with seed 42, then show me person 1." → (`regenerate` with `seed=42`, then `get_record`)
- "Reshuffle all the random records." → (`regenerate`)
- "Get random value number 4." → (`get_record` with `kind="values"`, `id=4`)

Handy because records are **seeded and stable**: ask for a person by id, use it
to seed a test fixture, and it stays the same until you ask Claude to reseed.
Pass a fixed seed (e.g. "reseed with 42") when you need reproducible data.

The two `regenerate` prompts only work when the server was started with
`ALLOW_REGENERATE=1` (the [opt-in](#the-regenerate-tool-is-opt-in) flag);
otherwise the tool isn't exposed and Claude won't have it to call.

* * *

## Using a published image or a remote server

**This section is for consumers who are not building from source** — you have the
published Docker image, or someone has deployed the server for you. No Python, uv,
or checkout required. Pick the option that matches how the server reaches you.

### Option A — Docker image, client launches it (stdio)

The client starts a fresh container per session and talks to it over stdio. Use
`-i` (keep stdin open) and force the stdio transport, since the image defaults to
HTTP. The image is published to two registries, so pick one:

```jsonc
// GitHub Container Registry (GHCR)
{
  "mcpServers": {
    "random": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "MCP_TRANSPORT=stdio",
               "ghcr.io/mitchallen/random-mcp-server:latest"]
    }
  }
}
```

```jsonc
// Docker Hub
{
  "mcpServers": {
    "random": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "MCP_TRANSPORT=stdio",
               "mitchallen/random-mcp-server:latest"]
    }
  }
}
```

Claude Code equivalent — again, pick a registry:

```sh
# GitHub Container Registry (GHCR)
claude mcp add random -- docker run -i --rm -e MCP_TRANSPORT=stdio ghcr.io/mitchallen/random-mcp-server:latest

# Docker Hub
claude mcp add random -- docker run -i --rm -e MCP_TRANSPORT=stdio mitchallen/random-mcp-server:latest
```

(Pin a version like `:0.1.3` in place of `:latest` for a reproducible setup.)

**Scope — `local` (default) vs `user`.** `claude mcp add` registers the server
in the current project only. Add `--scope user` (`-s user`) to register it once
for **every** project on your machine instead:

```sh
# GHCR, available across all your projects
claude mcp add --scope user random -- docker run -i --rm -e MCP_TRANSPORT=stdio ghcr.io/mitchallen/random-mcp-server:latest

# Docker Hub, available across all your projects
claude mcp add --scope user random -- docker run -i --rm -e MCP_TRANSPORT=stdio mitchallen/random-mcp-server:latest
```

(Scopes are `local` — this project, the default; `project` — shared via a
checked-in `.mcp.json`; and `user` — all your projects.)

### Option B — Long-running container over HTTP (local)

Start the container once (it serves HTTP by default) from either registry, then
point an HTTP-capable client at it:

```sh
# GitHub Container Registry (GHCR)
docker run -d --rm -p 8000:8000 --name random-mcp ghcr.io/mitchallen/random-mcp-server:latest

# Docker Hub
docker run -d --rm -p 8000:8000 --name random-mcp mitchallen/random-mcp-server:latest
```

Claude Code (native HTTP transport) — the client connects over HTTP, so the
command is the same regardless of which registry you pulled from:

```sh
claude mcp add --transport http random http://localhost:8000/mcp
```

Add `--scope user` (`-s user`) to register it for **every** project on your
machine instead of just the current one:

```sh
claude mcp add --scope user --transport http random http://localhost:8000/mcp
```

For clients that only speak **stdio**, bridge to the HTTP endpoint with
[`mcp-remote`](https://www.npmjs.com/package/mcp-remote):

```jsonc
{
  "mcpServers": {
    "random": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8000/mcp"]
    }
  }
}
```

### Option C — Remote deployment (HTTP)

If the server is hosted elsewhere, use its public URL — everything else matches
Option B. There's no image to pull here (the host already runs it, from
whichever registry they chose), so registry choice doesn't apply on your side:

```sh
claude mcp add --transport http random https://random-mcp.example.com/mcp
```

Add `--scope user` (`-s user`) to register it across all your projects:

```sh
claude mcp add --scope user --transport http random https://random-mcp.example.com/mcp
```

```jsonc
{
  "mcpServers": {
    "random": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://random-mcp.example.com/mcp"]
    }
  }
}
```

Notes for remote use:

- Prefer **HTTPS** so traffic (and any auth headers) are encrypted in transit.
- This server ships **no authentication** (the REST server's `x-api-key` guard
  isn't ported). If you expose it beyond localhost, put it behind a reverse proxy,
  gateway, or network policy that enforces access — or add
  [FastMCP auth](https://gofastmcp.com/servers/auth/authentication).
- **No built-in rate limiting** — by design (see below).
- The endpoint path is `/mcp` (no trailing slash). Requesting `/mcp/` works too
  but returns a 307 redirect to `/mcp`, so point clients at `/mcp` to skip the
  extra round-trip.

### Why there's no built-in rate limiting

FastMCP ships rate-limiting middleware and it would be a few lines to wire in,
but this server deliberately doesn't:

- **Nothing expensive to protect.** Every tool is an in-memory lookup against a
  pool built once at start-up — no database, external API, or real compute cost.
  Rate limiting shields scarce resources; this workload has none.
- **It only makes sense on the shared HTTP transport.** Over stdio each client
  launches its own process, so throttling your own single-user server is moot.
- **Without auth there's no per-client identity to key on.** In-memory limiting
  would fall back to a *global* limit, which recreates the shared-instance
  fairness problem (one noisy client starves everyone) rather than solving it.
  It also wouldn't coordinate across replicas behind a load balancer.
- **The edge is the right layer.** For a public deployment, enforce rate limits
  at the same reverse proxy / gateway that provides auth and TLS (nginx,
  Cloudflare, an API gateway) — it coordinates across replicas and can key on
  authenticated identity. App-level limiting becomes worthwhile mainly once you
  add auth (so `get_client_id` is meaningful).

The [example prompts](#example-prompts-claude-code) above work the same once the
server is connected by any of these methods.

* * *

## Verified client setups

The setups below were exercised against the published image (`:0.1.3`) with a
real client — connect, `initialize`, list tools, and call a tool — not just
assumed. Legend: ✅ connected end-to-end · ☑️ server/endpoint proven, that exact
client wiring not run here.

| Setup | Transport | How it was verified | Status |
| ----- | --------- | ------------------- | ------ |
| Docker image, client-launched ([Option A](#option-a--docker-image-client-launches-it-stdio)) | stdio | Piped an MCP `initialize` into `docker run -i -e MCP_TRANSPORT=stdio …`; got a valid response reporting `v0.1.3`. | ✅ |
| Long-running HTTP container ([Option B](#option-b--long-running-container-over-http-local)) | HTTP | FastMCP network client against `http://localhost:8000/mcp` (listed all 5 tools, called `get_record`/`count_records`). | ✅ |
| Long-running HTTP container, Claude Code | HTTP | `claude mcp add --transport http …` → `claude mcp list` reported **✔ Connected**. | ✅ |
| Local dev, console script ([from source](#using-with-an-mcp-client--local-development-from-source)) | stdio | Server proven through the in-memory FastMCP client and the test suite; the `uv run` stdio launch is the same entry point. | ☑️ |
| Remote deployment ([Option C](#option-c--remote-deployment-http)) | HTTP | Identical to Option B but with a public URL; the HTTP endpoint is proven, a hosted instance was not stood up. | ☑️ |
| stdio-only client via `mcp-remote` bridge | HTTP (bridged) | Documented from standard `mcp-remote` usage; not run here. | ☑️ |

* * *

## Docker

Published multi-platform (`linux/amd64`, `linux/arm64`) images are available
from two registries:

- **GitHub Container Registry:** `ghcr.io/mitchallen/random-mcp-server`
- **Docker Hub:** `mitchallen/random-mcp-server`

The image runs the server over **streamable HTTP** by default (`MCP_TRANSPORT=http`,
`HOST=0.0.0.0`, `PORT=8000`) so it's reachable on a published port.

### Pull the image

```sh
docker pull ghcr.io/mitchallen/random-mcp-server:latest
# or from Docker Hub
docker pull mitchallen/random-mcp-server:latest
```

Both registries also publish version tags (e.g. `:0.1.0`); prefer a pinned
version over `:latest` for reproducible deployments.

### Run the container

```sh
docker run --rm -p 8000:8000 --name random-mcp ghcr.io/mitchallen/random-mcp-server:latest
```

Then connect an HTTP MCP client to `http://localhost:8000/mcp`.

### Test a published release with make

Convenience targets pull and run the **published** image in your local Docker
environment — handy for smoke-testing a release without a local build:

```sh
make docker-test               # up + smoke + down in one shot (exits non-zero on failure)

make docker-up                 # pull + run ghcr.io/mitchallen latest, detached
make docker-smoke              # MCP `initialize` handshake — passes if the server responds
make docker-logs               # follow the container logs
make docker-down               # stop it

make docker-up TAG=0.1.1                         # pin a version
make docker-up REGISTRY=docker.io/mitchallen     # pull from Docker Hub instead
make docker-up HTTP_PORT=9000                    # publish on a different host port
```

### Configure at runtime

Pass any of the [configuration](#configuration) variables with `-e`:

```sh
docker run --rm -p 9000:9000 \
  -e PORT=9000 \
  -e APP_NAME=my-random \
  -e RANDOM_COUNT=50 \
  -e RANDOM_SEED=42 \
  ghcr.io/mitchallen/random-mcp-server:latest
```

To run over stdio inside the container instead (e.g. when another process
attaches to it), override the transport:

```sh
docker run --rm -i -e MCP_TRANSPORT=stdio ghcr.io/mitchallen/random-mcp-server:latest
```

### Build locally

```sh
make docker-build        # docker build -t random-mcp-server .
make docker-run          # serves http on localhost:8000
```

* * *

## CI / Publish

Two GitHub Actions workflows live in `.github/workflows/`:

- **`test`** — runs on every push/PR to `main`: the **unit** suite
  (`uv sync --frozen` then `pytest --ignore=tests/test_bdd.py`).
- **`bdd`** — runs on every push/PR to `main` in its own workflow: the
  **pytest-bdd** scenarios (`pytest tests/test_bdd.py`), so they pass or fail
  and report (and badge) independently of the unit suite.
- **`publish`** — triggered by pushing a `v*` tag. Builds a multi-platform
  (`linux/amd64`, `linux/arm64`) image and pushes it to the GitHub Container
  Registry as `ghcr.io/mitchallen/random-mcp-server` with both the version and
  `latest` tags, then runs `make docker-test` against the just-published image as
  a post-publish smoke check (the job fails if the released image doesn't answer
  an MCP `initialize`). It uses the built-in `GITHUB_TOKEN`, so no extra secrets
  are needed.
- **`publish-dockerhub`** — also triggered by a `v*` tag. Pushes the same
  multi-platform image to Docker Hub as `mitchallen/random-mcp-server`, runs the
  same `make docker-test` post-publish smoke check against it, and syncs this
  README to the Docker Hub repo description. Requires two repository secrets and
  a pre-created Docker Hub repository (see below).

### Docker Hub setup

The `publish-dockerhub` workflow needs:

1. A Docker Hub repository named `mitchallen/random-mcp-server`.
2. Two repository secrets — set them with the GitHub CLI:

   ```sh
   gh secret set DOCKERHUB_USERNAME --repo mitchallen/random-mcp-server
   gh secret set DOCKERHUB_TOKEN    --repo mitchallen/random-mcp-server   # a Docker Hub access token
   ```

Until both secrets exist, the `publish-dockerhub` job will fail on tag pushes
while the GHCR `publish` job continues to work on its own.

To cut a release, use the `release` target — it bumps `version` in
`pyproject.toml` (and `uv.lock`), commits, tags, and pushes, which triggers both
publish workflows:

```sh
make release              # patch bump (default)
make release BUMP=minor   # or minor / major
```

The target refuses to run unless the working tree is clean and you're on `main`.
It's equivalent to bumping the version, then `git tag vX.Y.Z && git push origin
main vX.Y.Z` by hand.

* * *

## Development

- Source: `src/random_mcp_server/`
  - `generators.py` — deterministic, seedable record builders (`RandomFactory`)
  - `server.py` — FastMCP tools + entry point (`main`)
- Tests: `tests/`, run with `make test` (`uv run pytest`), driven through an
  in-memory FastMCP client. Two layers:
  - `test_generators.py` / `test_server.py` — plain pytest unit tests.
  - `test_bdd.py` + `tests/features/*.feature` — a **pytest-bdd** layer that
    mirrors random-server's Cucumber features (Gherkin scenarios for each record
    kind and the server info check), plus scenarios for `get_record` (by id,
    stability, out-of-range), `count_records`, and `regenerate` (seed reporting
    and reproducibility). The `/v1/<kind>` routes map to the `list_records` /
    `get_record` / `count_records` tools; `auth.feature` is not mirrored since
    the `x-api-key` guard isn't ported.
- `make build` produces a wheel/sdist via `uv build`.
- **Dependencies:** `uv.lock` is committed and the Docker build installs from it
  with `--frozen`. Whenever you change dependencies in `pyproject.toml`, run
  `make lock` (or `uv lock`) to refresh the lockfile and commit it.

### FastMCP integration notes

Two non-obvious adjustments were needed so the FastMCP tooling reports the
project correctly:

- **Explicit `version`.** `FastMCP(...)` is constructed with
  `version=APP_VERSION` (read from the installed package metadata). Without it,
  FastMCP falls back to reporting *its own framework version* in the MCP
  `initialize` handshake and in `make inspect` / `fastmcp inspect` — so the
  server would advertise e.g. `3.4.3` instead of the package's `0.1.2`.
- **Absolute import in `server.py`.** The module imports its siblings as
  `from random_mcp_server.generators import ...` rather than `from .generators`.
  The FastMCP CLI (`make inspect`, `fastmcp list/call`) loads `server.py` *by
  path* rather than as part of the installed package, and a relative import
  fails that way with `attempted relative import with no known parent package`.
  The absolute form loads correctly both by path and as a package module.

* * *

## License

MIT © Mitch Allen
