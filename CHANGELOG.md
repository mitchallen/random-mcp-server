# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-06

### Changed

- **`regenerate` is now opt-in and disabled by default.** It reseeds the single
  process-wide pool shared by every client on an instance, so on a shared
  deployment one caller could reshuffle records out from under everyone else. It
  is now gated behind the new `ALLOW_REGENERATE` environment variable; when
  unset the tool is not registered at all — absent from the tool list and not
  callable. Enable it (`ALLOW_REGENERATE=1`) only for single-user / per-session
  (client-launched stdio) deployments where reseeding affects just that caller.
  **This is a behavior change:** clients that relied on `regenerate` being
  present must now set the flag.

### Added

- `ALLOW_REGENERATE` environment variable (accepts `1`/`true`/`yes`/`on`).
- `server_info` now reports an `allow_regenerate` field so clients can tell
  whether reseeding is available.

### Documentation

- New **Determinism & idempotency of records** section in the README explaining
  what stays stable and what changes across calls, restarts, shared instances,
  and seeds, plus a scenario table and the `regenerate` opt-in guidance.
- Documented the verified client setups and clarified developer (from-source)
  vs consumer (published image / remote) MCP client configuration.

## [0.1.3] - 2026-07-06

### Added

- Report the package version in the MCP `initialize` handshake (instead of
  FastMCP's own framework version).
- `make inspect` target for a quick server summary.
- pytest-bdd layer mirroring random-server's Cucumber features, with coverage
  for `get_record`, `count_records`, and `regenerate`, run as its own CI job
  with a dedicated badge.

## [0.1.2] - 2026-07-06

### Added

- Make targets to pull and run the published image locally
  (`docker-up`/`docker-smoke`/`docker-down`/`docker-test`).
- Post-publish smoke check on both publish workflows (fails the release if the
  just-published image doesn't answer an MCP `initialize`).
- README badges (version, Docker Hub, CI) and Claude Code example prompts.

## [0.1.1] - 2026-07-06

### Added

- `make release` target (version bump + commit + tag + push).
- Expanded Docker usage section in the README.

## [0.1.0] - 2026-07-06

### Added

- Initial release: FastMCP server exposing the random-server API as MCP tools
  (`server_info`, `list_records`, `get_record`, `count_records`, `regenerate`).
- CI test/bdd workflows and GHCR + Docker Hub publish workflows.

[0.2.0]: https://github.com/mitchallen/random-mcp-server/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/mitchallen/random-mcp-server/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/mitchallen/random-mcp-server/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/mitchallen/random-mcp-server/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/mitchallen/random-mcp-server/releases/tag/v0.1.0
