# Makefile with help command

IMAGE ?= random-mcp-server

# Version bump level for `make release`: patch (default), minor, or major.
BUMP ?= patch

# Published image coordinates for pulling/running release images locally.
# Switch registries with e.g. REGISTRY=docker.io/mitchallen, pin with TAG=0.1.1.
REGISTRY ?= ghcr.io/mitchallen
TAG ?= latest
PUBLISHED_IMAGE ?= $(REGISTRY)/random-mcp-server
CONTAINER ?= random-mcp
HTTP_PORT ?= 8000

# Default target is help
.PHONY: all
all: help

# Help target
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make install      - Sync dependencies into a uv-managed venv (.venv)"
	@echo "  make run          - Run the MCP server over stdio"
	@echo "  make run-http     - Run the MCP server over streamable HTTP (PORT, default 8000)"
	@echo "  make dev          - Launch the MCP Inspector against the server"
	@echo "  make inspect      - Print a server summary (name, version, tools) via fastmcp"
	@echo "  make test         - Run the test suite (pytest)"
	@echo "  make lock         - Refresh uv.lock"
	@echo "  make release      - Bump version (BUMP=patch|minor|major), commit, tag, and push"
	@echo "  make build        - Build the wheel/sdist with uv"
	@echo "  make docker-build - Build the Docker image locally"
	@echo "  make docker-run   - Run the locally-built image over HTTP on port 8000"
	@echo "  make docker-pull  - Pull the published image (REGISTRY, TAG)"
	@echo "  make docker-up    - Pull and run the published image detached (HTTP_PORT, TAG)"
	@echo "  make docker-smoke - Smoke-test the running container's MCP endpoint (HTTP_PORT)"
	@echo "  make docker-test  - Up + smoke + down in one shot (CI gate for a published image)"
	@echo "  make docker-logs  - Follow logs of the running test container"
	@echo "  make docker-down  - Stop the running test container"
	@echo "  make scan         - Scan the Docker image for vulnerabilities (Trivy)"
	@echo "  make docker-rm    - Remove the Docker image"
	@echo "  make docker-prune - Prune unused Docker data"
	@echo "  make clean        - Remove venv and build artifacts"
	@echo "  make help         - Display this help message"

# Sync dependencies (creates .venv) including the dev group
.PHONY: install
install:
	@echo "Syncing dependencies with uv..."
	uv sync

# Run the server over stdio (default MCP transport)
.PHONY: run
run: install
	uv run random-mcp-server

# Run the server over streamable HTTP
.PHONY: run-http
run-http: install
	MCP_TRANSPORT=http HOST=0.0.0.0 PORT=$${PORT:-8000} uv run random-mcp-server

# Launch the interactive MCP Inspector against the server
.PHONY: dev
dev: install
	uv run fastmcp dev src/random_mcp_server/server.py

# Print a summary of the server (name, version, tools) via the FastMCP CLI
.PHONY: inspect
inspect: install
	uv run fastmcp inspect src/random_mcp_server/server.py

# Run tests
.PHONY: test
test: install
	@echo "Running tests..."
	uv run pytest

# Refresh the lockfile
.PHONY: lock
lock:
	uv lock

# Bump the version in pyproject.toml (+ uv.lock), commit, tag, and push.
# The pushed v* tag triggers the publish workflows (GHCR + Docker Hub).
# Override the bump level with BUMP=minor or BUMP=major.
.PHONY: release
release:
	@test -z "$$(git status --porcelain)" || { echo "Working tree is not clean; commit or stash first."; exit 1; }
	@branch=$$(git rev-parse --abbrev-ref HEAD); \
	test "$$branch" = "main" || { echo "Refusing to release from '$$branch'; switch to main."; exit 1; }
	@echo "Bumping version ($(BUMP))..."
	uv version --bump $(BUMP)
	@version=$$(uv version --short); \
	echo "Releasing v$$version..."; \
	git add pyproject.toml uv.lock; \
	git commit -m "Release v$$version"; \
	git tag "v$$version"; \
	git push origin main; \
	git push origin "v$$version"; \
	echo "Pushed v$$version — the publish workflows will build and push the images."

# Build distributables
.PHONY: build
build:
	@echo "Building wheel and sdist..."
	uv build

# Build Docker image locally
.PHONY: docker-build
docker-build:
	@echo "Building Docker image locally..."
	docker build -t $(IMAGE) .

# Run the locally-built image over HTTP on port 8000
.PHONY: docker-run
docker-run:
	docker run --rm -p 8000:8000 --name $(IMAGE) $(IMAGE)

# --- Published image (for local testing of a release) --------------------

# Pull the published image from the registry.
#   make docker-pull                              # ghcr.io/mitchallen, latest
#   make docker-pull REGISTRY=docker.io/mitchallen TAG=0.1.1
.PHONY: docker-pull
docker-pull:
	@echo "Pulling $(PUBLISHED_IMAGE):$(TAG)..."
	docker pull $(PUBLISHED_IMAGE):$(TAG)

# Pull and run the published image detached over HTTP for local testing.
# Override the host port with HTTP_PORT=9000.
.PHONY: docker-up
docker-up: docker-pull
	-docker rm -f $(CONTAINER) 2>/dev/null || true
	docker run -d --rm -p $(HTTP_PORT):8000 --name $(CONTAINER) $(PUBLISHED_IMAGE):$(TAG)
	@echo "Running $(PUBLISHED_IMAGE):$(TAG) as '$(CONTAINER)'."
	@echo "Connect an HTTP MCP client to http://localhost:$(HTTP_PORT)/mcp/"

# Smoke-test the running container: confirms the $(CONTAINER) container is up,
# then performs a real MCP `initialize` handshake against the HTTP endpoint and
# asserts the server identifies itself.
.PHONY: docker-smoke
docker-smoke:
	@docker ps --filter "name=^/$(CONTAINER)$$" --filter "status=running" --format '{{.Names}}' \
	  | grep -q "^$(CONTAINER)$$" \
	  || { echo "FAIL: container '$(CONTAINER)' is not running. Start it with 'make docker-up'."; exit 1; }
	@echo "Smoke-testing MCP endpoint at http://localhost:$(HTTP_PORT)/mcp ..."
	@curl -fsS -L --max-time 10 \
	  -X POST http://localhost:$(HTTP_PORT)/mcp \
	  -H "Content-Type: application/json" \
	  -H "Accept: application/json, text/event-stream" \
	  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"make-smoke","version":"0"}}}' \
	  | grep -q '"name":"random-mcp-server"' \
	  && echo "PASS: server responded to MCP initialize" \
	  || { echo "FAIL: no valid MCP initialize response on port $(HTTP_PORT). Is 'make docker-up' running?"; exit 1; }

# Follow logs of the running test container.
.PHONY: docker-logs
docker-logs:
	docker logs -f $(CONTAINER)

# Stop the running test container (started with --rm, so it is removed too).
.PHONY: docker-down
docker-down:
	@echo "Stopping $(CONTAINER)..."
	-docker stop $(CONTAINER)

# End-to-end container check: up -> wait for readiness -> smoke -> down.
# Always tears down (even if the smoke test fails) and exits with the smoke
# test's status, so it works as a one-shot CI gate for a published image.
.PHONY: docker-test
docker-test:
	@$(MAKE) --no-print-directory docker-up
	@printf "Waiting for MCP endpoint on port $(HTTP_PORT)"; \
	for i in $$(seq 1 30); do \
	  if curl -sS -o /dev/null --max-time 2 http://localhost:$(HTTP_PORT)/mcp 2>/dev/null; then break; fi; \
	  printf "."; sleep 1; \
	done; echo
	@$(MAKE) --no-print-directory docker-smoke; status=$$?; \
	  $(MAKE) --no-print-directory docker-down; \
	  exit $$status

# Scan container for vulnerabilities using Trivy
.PHONY: scan
scan:
	@echo "Scanning $(IMAGE) for vulnerabilities (fixable CRITICAL/HIGH fail)..."
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy \
		image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 $(IMAGE) \
		|| { echo "Vulnerabilities found (or image not built — run 'make docker-build')."; exit 1; }

# Remove Docker image
.PHONY: docker-rm
docker-rm:
	@echo "Removing Docker image..."
	-docker rmi $(IMAGE)

# Prune unused Docker data
.PHONY: docker-prune
docker-prune:
	@echo "Pruning unused Docker data..."
	docker system prune -f

# Clean venv and build artifacts
.PHONY: clean
clean:
	@echo "Cleaning venv and build artifacts..."
	rm -rf .venv dist *.egg-info .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
