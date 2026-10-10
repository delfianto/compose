# syntax=docker/dockerfile:1.7
ARG COMFYUI_IMAGE=ghcr.io/delfianto/comfyui-nvidia-cuda:latest
FROM ${COMFYUI_IMAGE} AS workspace

FROM python:3.12-slim-bookworm
ARG MCP_VERSION=0.10.0
ARG MCP_REVISION
ARG COMFY_CLI_VERSION=1.22.0
ARG MCP_SDK_VERSION=2.3.0
LABEL org.opencontainers.image.source="https://github.com/Comfy-Org/comfy-mcp" \
      org.opencontainers.image.version="${MCP_VERSION}" \
      org.opencontainers.image.revision="${MCP_REVISION}"
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/mcp \
    && uv pip install --python /opt/mcp/bin/python \
       "comfy-mcp==${MCP_VERSION}" "comfy-cli==${COMFY_CLI_VERSION}" \
       "mcp==${MCP_SDK_VERSION}"
# Copy only the workspace, without CUDA, Torch, or the generation environment.
COPY --from=workspace /opt/ComfyUI /opt/ComfyUI
RUN for folder in models input output user custom_nodes; do \
      rm -rf "/opt/ComfyUI/${folder}"; \
      ln -s "/data/${folder}" "/opt/ComfyUI/${folder}"; \
    done
RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/*
ENV PATH=/opt/mcp/bin:$PATH \
    VIRTUAL_ENV=/opt/mcp \
    COMFY_BIN=/opt/mcp/bin/comfy \
    PYTHONUNBUFFERED=1 \
    DO_NOT_TRACK=1 \
    COMFY_NO_TELEMETRY=1
COPY http-server.py smoke-test.py /app/
COPY --chmod=755 entrypoint.sh /app/entrypoint.sh
WORKDIR /opt/ComfyUI
EXPOSE 9100
ENTRYPOINT ["/app/entrypoint.sh"]
