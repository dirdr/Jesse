# syntax=docker/dockerfile:1
FROM --platform=$BUILDPLATFORM node:22-alpine AS web-build
WORKDIR /build/ui
RUN npm install --global pnpm@10.11.0
COPY ui/package.json ui/pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store pnpm install --frozen-lockfile
COPY ui/ ./
RUN pnpm build

FROM ghcr.io/astral-sh/uv:0.9.30 AS uv
FROM python:3.13-slim-bookworm AS python-build
RUN apt-get update && apt-get install --yes --no-install-recommends build-essential linux-libc-dev \
    && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /uvx /usr/local/bin/
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY src/ ./src/
COPY --from=web-build /build/src/jesse/conversation/static/ ./src/jesse/conversation/static/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-editable

FROM python:3.13-slim-bookworm AS backend
LABEL org.opencontainers.image.source="https://github.com/dirdr/Jesse"
RUN apt-get update && apt-get install --yes --no-install-recommends libportaudio2 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 jesse \
    && useradd --uid 10001 --gid 10001 --no-create-home jesse \
    && mkdir -p /data/runs && chown -R jesse:jesse /data
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp \
    JESSE_CONTEXTS_DIR=/app/contexts
COPY --from=python-build /app/.venv/ /app/.venv/
COPY contexts/ /app/contexts/
USER 10001:10001
EXPOSE 8765
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=3)"
CMD ["jesse-ui", "--host", "0.0.0.0", "--surface", "web", "--port", "8765", "--runs", "/data/runs"]

FROM nginxinc/nginx-unprivileged:1.28-alpine AS frontend
LABEL org.opencontainers.image.source="https://github.com/dirdr/Jesse"
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=web-build /build/src/jesse/conversation/static/ /usr/share/nginx/html/
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --spider http://127.0.0.1:8080/healthz || exit 1
