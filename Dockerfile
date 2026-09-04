# syntax=docker/dockerfile:1

# Build-Stufe: Abhaengigkeiten mit uv aufloesen und installieren.
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Erst die Manifeste, damit der Layer-Cache bei reinen Code-Aenderungen haelt.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# Laufzeit-Stufe: nur die fertige venv, kein uv, kein Build-Werkzeug.
FROM python:3.12-slim

# Nicht als root laufen.
RUN useradd --create-home --uid 10001 mcp

WORKDIR /app

COPY --from=builder --chown=mcp:mcp /app/.venv /app/.venv
COPY --from=builder --chown=mcp:mcp /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER mcp

# stdio-Transport: stdout gehoert dem JSON-RPC, Logs gehen nach stderr.
ENTRYPOINT ["openai-ads-mcp"]
