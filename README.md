# random-mcp-server

[![GitHub tag](https://img.shields.io/github/v/tag/mitchallen/random-mcp-server?sort=semver&label=version)](https://github.com/mitchallen/random-mcp-server/tags) [![Docker Hub](https://img.shields.io/docker/v/mitchallen/random-mcp-server?sort=semver&label=docker%20hub)](https://hub.docker.com/r/mitchallen/random-mcp-server) [![test](https://github.com/mitchallen/random-mcp-server/actions/workflows/test.yml/badge.svg)](https://github.com/mitchallen/random-mcp-server/actions/workflows/test.yml)

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
| _(restart to reseed)_     | `regenerate(seed?)`                   |

Records are **seeded at start-up**, so a given `id` is stable until you call
`regenerate`. Pass a fixed `seed` (tool arg or `RANDOM_SEED`) for reproducible
data.

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

### Interactive Inspector

```sh
make dev                 # launches the FastMCP Inspector
```

* * *

## Configuration

All configuration is via environment variables:

| Variable        | Default            | Purpose                                              |
| --------------- | ------------------ | ---------------------------------------------------- |
| `APP_NAME`      | `random-mcp-server`| Name reported by `server_info`                       |
| `RANDOM_COUNT`  | `25`               | Records generated per kind at start-up               |
| `RANDOM_SEED`   | _(random)_         | Fixed seed for reproducible pools                    |
| `MCP_TRANSPORT` | `stdio`            | `stdio`, `http`, or `sse`                            |
| `HOST`          | `127.0.0.1`        | Bind address for `http`/`sse`                        |
| `PORT`          | `8000`             | Bind port for `http`/`sse`                           |

* * *

## Using with an MCP client

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

Then connect an HTTP MCP client to `http://localhost:8000/mcp/`.

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

- **`test`** — runs on every push/PR to `main`: `uv sync --frozen` then `uv run
  pytest`.
- **`publish`** — triggered by pushing a `v*` tag. Builds a multi-platform
  (`linux/amd64`, `linux/arm64`) image and pushes it to the GitHub Container
  Registry as `ghcr.io/mitchallen/random-mcp-server` with both the version and
  `latest` tags, then runs `make docker-test` against the just-published image as
  a post-publish smoke check (the job fails if the released image doesn't answer
  an MCP `initialize`). It uses the built-in `GITHUB_TOKEN`, so no extra secrets
  are needed.
- **`publish-dockerhub`** — also triggered by a `v*` tag. Pushes the same
  multi-platform image to Docker Hub as `mitchallen/random-mcp-server` and syncs
  this README to the Docker Hub repo description. Requires two repository
  secrets and a pre-created Docker Hub repository (see below).

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
- Tests: `tests/` (`pytest`, driven through an in-memory FastMCP client)
- `make build` produces a wheel/sdist via `uv build`.
- **Dependencies:** `uv.lock` is committed and the Docker build installs from it
  with `--frozen`. Whenever you change dependencies in `pyproject.toml`, run
  `make lock` (or `uv lock`) to refresh the lockfile and commit it.

* * *

## License

MIT © Mitch Allen
