# --- Stage 1: Build ---
# Pin a uv image that already ships a compatible Python.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app

# uv settings: compile bytecode and copy (don't link) into the venv for portability.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# Install dependencies first (cached) using only the manifest + lockfile.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy source and install the project itself (no dev deps).
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Stage 2: Production ---
FROM python:3.12-slim-bookworm AS prod
WORKDIR /app

# Upgrade OS packages to pick up security fixes.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Copy the fully built virtualenv and the app source from the builder.
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Put the venv on PATH so the console script resolves.
ENV PATH="/app/.venv/bin:$PATH"

# Serve over HTTP by default so the container is reachable on a published port.
ENV MCP_TRANSPORT=http \
    HOST=0.0.0.0 \
    PORT=8000

# Security: run as a non-root user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
CMD ["random-mcp-server"]
