# syntax=docker/dockerfile:1.7
ARG PYTHON_IMAGE=python:3.14-slim-trixie
ARG NODE_IMAGE=node:24-trixie-slim
ARG BUN_IMAGE=oven/bun:1.4.4
ARG UV_IMAGE=ghcr.io/astral-sh/uv:latest

FROM ${BUN_IMAGE} AS bun
FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS source
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*
ARG LYCHEE_REPOSITORY=https://github.com/delfianto/lychee.git
ARG LYCHEE_REF=main
RUN git init /src \
    && git -C /src remote add origin "${LYCHEE_REPOSITORY}" \
    && git -C /src fetch --depth=1 origin "${LYCHEE_REF}" \
    && git -C /src checkout --detach FETCH_HEAD \
    && rm -rf /src/.git

# Vite+ requires Node; Bun supplies the upstream package manager.
FROM ${NODE_IMAGE} AS frontend
COPY --from=bun /usr/local/bin/bun /usr/local/bin/bun
WORKDIR /build/frontend
COPY --from=source /src/frontend/package.json /src/frontend/bun.lock ./
RUN --mount=type=cache,target=/root/.bun/install/cache bun install --frozen-lockfile
COPY --from=source /src/frontend/ ./
ENV VITE_USE_MOCKS=false
RUN bun run build

FROM ${PYTHON_IMAGE} AS backend
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /app/backend
COPY --from=source /src/backend/pyproject.toml /src/backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

FROM ${PYTHON_IMAGE} AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /data /library
ENV PATH="/app/backend/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    DATABASE_URL=sqlite:////data/lychee.db \
    STORAGE_PATH=/library \
    LOG_LEVEL=INFO \
    LOG_FORMAT=json
WORKDIR /app/backend
COPY --from=backend /app/backend/.venv/ ./.venv/
COPY --from=source /src/backend/src/ ./src/
COPY --from=source /src/backend/alembic/ ./alembic/
COPY --from=source /src/backend/alembic.ini ./alembic.ini
COPY --from=source /src/LICENSE /app/LICENSE
COPY --from=frontend /build/frontend/dist/ /app/frontend/
COPY deployment.py ./deployment.py
ARG LYCHEE_REPOSITORY=https://github.com/delfianto/lychee.git
ARG LYCHEE_REF=main
LABEL org.opencontainers.image.title="Lychee" \
      org.opencontainers.image.source="${LYCHEE_REPOSITORY}" \
      org.opencontainers.image.revision="${LYCHEE_REF}" \
      org.opencontainers.image.licenses="MIT"
EXPOSE 8000
# Keep one worker: the task queue and SSE event broker are process-local.
CMD ["python", "-m", "uvicorn", "deployment:app", "--host", "0.0.0.0", "--port", "8000"]
