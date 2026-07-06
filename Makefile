# Makefile with help command

IMAGE ?= random-mcp-server

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
	@echo "  make test         - Run the test suite (pytest)"
	@echo "  make lock         - Refresh uv.lock"
	@echo "  make build        - Build the wheel/sdist with uv"
	@echo "  make docker-build - Build the Docker image locally"
	@echo "  make docker-run   - Run the server in Docker over HTTP on port 8000"
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

# Run tests
.PHONY: test
test: install
	@echo "Running tests..."
	uv run pytest

# Refresh the lockfile
.PHONY: lock
lock:
	uv lock

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

# Run the container over HTTP on port 8000
.PHONY: docker-run
docker-run:
	docker run --rm -p 8000:8000 --name $(IMAGE) $(IMAGE)

# Scan container for vulnerabilities using Trivy
.PHONY: scan
scan:
	@echo "Scanning Docker image for vulnerabilities..."
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image $(IMAGE) || echo "Trivy scan failed. Is the image built?"

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
