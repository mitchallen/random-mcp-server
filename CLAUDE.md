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
  Docker Hub publish workflows. It then creates the matching **GitHub Release**
  (`gh release create`) using that version's `CHANGELOG.md` section as the notes
  (extracted with `awk`), so the tag, images, and Release stay in sync — the
  Releases page previously drifted because the tag was pushed without a Release
  object. `make release` does **not** touch `CHANGELOG.md`, so add the new
  version's entry (Keep a Changelog format, top of the file) **before** running
  it — the release is now **gated** on a matching `## [X.Y.Z]` section (checked
  with `uv version --dry-run` before any mutation) and aborts early if it's
  missing, so notes are never empty.
- **Branch protection:** `main` requires the `unit`, `bdd` and `scan` checks
  (`scan` is the `image-scan` job, which builds the Docker image). `scan` was
  added on 2026-10-12, after Dependabot #18 auto-merged with a failing image
  build — only `unit` and `bdd` were required, and the Python 3.15 base-image
  change had broken the build. `dependabot-auto-merge.yml` uses
  `gh pr merge --auto`, which waits for exactly these required checks, so a
  check that isn't required doesn't gate anything. `enforce_admins` stays
  **off** on purpose: `make release` pushes the version commit straight to
  `main`, which admin enforcement would block (expect a "Bypassed rule
  violations" notice on that push).
- **The `scan` check also smoke-tests the container:** `image-scan.yml` runs
  the freshly built image and calls `make docker-smoke` against it (an MCP
  `initialize` that must return this server's name), so an image that builds
  but crashes at startup fails the PR. `make docker-test` runs the same check
  against the *published* image instead.

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

## Releases — lessons from 2026-10-20

- **Is a release due?** Compare `main` against the latest tag and ignore
  `.github/` and `*.md` — CI and docs changes don't reach the image. A `uv.lock`
  change counts when it moves a package in `[project] dependencies` (`fastmcp`,
  `faker`) or their transitive tree; the `dev` group (`pytest`, `pytest-bdd`)
  doesn't, because the image installs `uv sync --frozen --no-dev`. #26
  (`fastmcp` 4.0.11 → 4.1.0, `faker` 40.41 → 40.43) is why v0.2.10 was cut.
  Dependabot auto-merges land on `main` without a release, so a production bump
  sits unshipped until someone cuts one. `auto-release.yml`
  now does that weekly (see "Automated releases").
- **`make release` does not touch the changelog links.** Add the
  `## [X.Y.Z] - YYYY-MM-DD` section *and* the footer links — point
  `[unreleased]` at `compare/vX.Y.Z...HEAD` and add
  `[X.Y.Z]: …/compare/vPREV...vX.Y.Z` — in one `docs: changelog for vX.Y.Z`
  commit to `main`, then run `make release`. It refuses to run without the
  section, creates the GitHub Release from it, and the `main` push shows a
  "Bypassed rule violations" notice (admins are not enforced).
- **Publish time:** 14–20 min (v0.2.8–v0.2.10). That's normal. Compare against
  `gh run list --workflow publish.yml` before treating a slow run as hung.
- **Verify what shipped, not just the green runs.**
  `docker buildx imagetools inspect <image>:X.Y.Z` on both registries should
  list `linux/amd64` and `linux/arm64`. Then `make docker-test TAG=X.Y.Z` pulls
  the *published* image and runs the MCP `initialize` smoke check, and the
  reply's `serverInfo` should carry the released version — v0.2.10 replied
  `{"name":"random-mcp-server","version":"0.2.10"}`.
- **The required `scan` check now starts the container** (see above), so a PR
  whose image builds but won't serve MCP is caught before release, not after.
- **Sibling conventions differ** — release flows, merge styles and Dependabot
  schedules vary across the eight active repos in `../`. random-server's
  CLAUDE.md ("Sibling projects") keeps the comparison; check it, or the
  sibling's own CLAUDE.md, before porting a fix.

## Automated releases

`.github/workflows/auto-release.yml` ships Dependabot updates without a
hand-cut release. Every Wednesday at 15:00 UTC it runs
`.github/scripts/auto-release.sh plan`. A release is due when `main` has
changes since the latest tag that reach the image, and every one was committed
by a bot. CI, docs and test changes and dev-only dependency bumps don't count.
When a release is due, it opens an `auto-release/vX.Y.Z` PR (patch version bump + `CHANGELOG.md` section) with
auto-merge (squash) on, so it lands only once the required checks pass. When the
PR merges, the `tag` job tags the merge commit, and the tag push triggers the
publish workflows. It also creates the GitHub Release.

- **Anything a person changed is left alone.** A human commit touching
  image-affecting files, or entries under `[Unreleased]` in the changelog,
  makes `plan` skip with a reason in the run summary. Release those with
  `make release`.
- **Run it by hand:** `gh workflow run auto-release.yml -f dry-run=true`
  reports the decision without opening a PR; drop `dry-run` to release now.
- **Credentials:** pushes use a GitHub App token (repo variable
  `RELEASE_APP_CLIENT_ID`, secret `RELEASE_APP_PRIVATE_KEY`), because tags and
  PRs created with `GITHUB_TOKEN` don't trigger other workflows.
- **Keep it in sync.** The same script and workflow live in all eight sibling
  repos; only the `MERGE_METHOD` and `CREATE_RELEASE` env values differ.
