# syntax=docker/dockerfile:1.7
FROM node:24-bookworm AS builder
ARG MCP_VERSION
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 make g++ \
    && rm -rf /var/lib/apt/lists/*
# The npm release includes compiled JavaScript and the supporting resources.
# Rebuild only the native dependencies after skipping package install hooks.
RUN --mount=type=cache,target=/root/.npm \
    test -n "${MCP_VERSION}" \
    && npm install --omit=dev --ignore-scripts "comfyui-mcp@${MCP_VERSION}" \
    && npm rebuild better-sqlite3 sharp

FROM node:24-bookworm-slim
ARG MCP_VERSION
ARG MCP_REVISION
LABEL org.opencontainers.image.source="https://github.com/artokun/comfyui-mcp" \
      org.opencontainers.image.version="${MCP_VERSION}" \
      org.opencontainers.image.revision="${MCP_REVISION}"
ENV NODE_ENV=production
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
USER node
ENTRYPOINT ["node", "/app/node_modules/comfyui-mcp/dist/index.js"]
