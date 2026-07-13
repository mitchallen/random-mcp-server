# --- Stage 1: Build ---
# Build the venv on Chainguard/Wolfi's Python-dev image (uv is preinstalled).
# Building on the SAME base as the runtime keeps the venv's interpreter symlink
# valid at runtime. Wolfi is a minimal, hardened distro with a near-zero CVE
# footprint (no perl / util-linux / ncurses / tar), so the final image ships
# clean where a Debian base carries dozens of unfixable OS-package CVEs.
FROM cgr.dev/chainguard/python:latest-dev AS builder
WORKDIR /app

# uv settings: compile bytecode, copy (don't link) for portability, and use the
# image's system Python instead of downloading one (so the venv is hosted on the
# base interpreter that the runtime stage also provides).
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# Install dependencies first (layer-cached) using only the manifest + lockfile.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy source and install the project itself (no dev deps).
COPY . .
RUN uv sync --frozen --no-dev

# --- Stage 2: Production ---
# Distroless Chainguard/Wolfi Python runtime — no shell, no package manager,
# and it already runs as the non-root 'nonroot' user (uid 65532).
FROM cgr.dev/chainguard/python:latest AS prod
WORKDIR /app

# Copy the fully built virtualenv and the app source from the builder.
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Put the venv on PATH so the console script resolves, and serve over HTTP by
# default so the container is reachable on a published port.
ENV PATH="/app/.venv/bin:$PATH" \
    MCP_TRANSPORT=http \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000
ENTRYPOINT ["random-mcp-server"]
