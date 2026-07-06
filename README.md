# random-mcp-server

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

* * *

## Docker

The image runs over HTTP by default so it's reachable on a published port.

```sh
make docker-build
make docker-run          # serves http on localhost:8000
```

Then connect an HTTP MCP client to `http://localhost:8000/mcp/`.

* * *

## CI / Publish

Two GitHub Actions workflows live in `.github/workflows/`:

- **`test`** — runs on every push/PR to `main`: `uv sync --frozen` then `uv run
  pytest`.
- **`publish`** — triggered by pushing a `v*` tag. Builds a multi-platform
  (`linux/amd64`, `linux/arm64`) image and pushes it to the GitHub Container
  Registry as `ghcr.io/mitchallen/random-mcp-server` with both the version and
  `latest` tags. It uses the built-in `GITHUB_TOKEN`, so no extra secrets are
  needed.
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

To cut a release, bump `version` in `pyproject.toml`, then tag and push:

```sh
git commit -am "0.1.1"
git tag v0.1.1
git push origin main
git push origin v0.1.1
```

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
