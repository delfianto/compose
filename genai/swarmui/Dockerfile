# --- Build Stage ---
FROM mcr.microsoft.com/dotnet/sdk:8.0-bookworm-slim AS build

ARG SWARMUI_VERSION=latest

ENV SWARMUI_VERSION=${SWARMUI_VERSION}
ENV SWARMUI_ROOT=/SwarmUI

WORKDIR /tmp
RUN apt-get update && apt-get install -y git

RUN tag_arg=""; \
    if [ -n "$SWARMUI_VERSION" ] && [ "$SWARMUI_VERSION" != "latest" ]; then \
        tag_arg="--branch $SWARMUI_VERSION"; \
    fi && \
    git clone --depth=1 $tag_arg https://github.com/mcmonkeyprojects/SwarmUI.git $SWARMUI_ROOT

WORKDIR $SWARMUI_ROOT
RUN dotnet publish src/SwarmUI.csproj -c Release -o /app/publish

# --- Runtime Stage ---
FROM mcr.microsoft.com/dotnet/aspnet:8.0-bookworm-slim AS runtime

ARG SWARMUI_UID=1000
ARG SWARMUI_GID=1000
ARG SWARMUI_PORT=7801

ENV SWARMUI_UID=${SWARMUI_UID}
ENV SWARMUI_GID=${SWARMUI_GID}
ENV SWARMUI_ROOT=/SwarmUI
ENV SWARMUI_PORT=${SWARMUI_PORT}
ENV HOME=$SWARMUI_ROOT/Home

# Install only runtime dependencies (no git, no build-essential, no full SDK)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip git \
    ffmpeg libglib2.0-0 libgl1 && \
    rm -rf /var/lib/apt/lists/*

# Copy the published application
COPY --from=build --chown=$SWARMUI_UID:$SWARMUI_GID /app/publish $SWARMUI_ROOT
COPY --from=build --chown=$SWARMUI_UID:$SWARMUI_GID /SwarmUI/launchtools $SWARMUI_ROOT/launchtools
COPY --from=build --chown=$SWARMUI_UID:$SWARMUI_GID /SwarmUI/languages $SWARMUI_ROOT/languages
COPY --from=build --chown=$SWARMUI_UID:$SWARMUI_GID /SwarmUI/docs $SWARMUI_ROOT/docs
COPY --from=build --chown=$SWARMUI_UID:$SWARMUI_GID /SwarmUI/src/BuiltinExtensions $SWARMUI_ROOT/src/BuiltinExtensions
COPY --from=build --chown=$SWARMUI_UID:$SWARMUI_GID /SwarmUI/src/wwwroot $SWARMUI_ROOT/src/wwwroot

RUN mkdir -p $SWARMUI_ROOT/Home $SWARMUI_ROOT/Data $SWARMUI_ROOT/dlbackend && \
    chown -R $SWARMUI_UID:$SWARMUI_GID $SWARMUI_ROOT

EXPOSE $SWARMUI_PORT

# Basic entrypoint script inside the Dockerfile
RUN echo '#!/usr/bin/env bash' > /usr/local/bin/entrypoint.sh && \
    echo 'chown -R "$SWARMUI_UID:$SWARMUI_GID" "$SWARMUI_ROOT/Home" "$SWARMUI_ROOT/Data" "$SWARMUI_ROOT/Models" "$SWARMUI_ROOT/Output" 2>/dev/null || true' >> /usr/local/bin/entrypoint.sh && \
    echo 'cd "$SWARMUI_ROOT"' >> /usr/local/bin/entrypoint.sh && \
    echo 'if [ "$(id -u)" = "0" ] && [ "$SWARMUI_UID" != "0" ]; then' >> /usr/local/bin/entrypoint.sh && \
    echo '    if setpriv --reuid="$SWARMUI_UID" --regid="$SWARMUI_GID" --init-groups --clear-groups true 2>/dev/null; then' >> /usr/local/bin/entrypoint.sh && \
    echo '        exec setpriv --reuid="$SWARMUI_UID" --regid="$SWARMUI_GID" --init-groups --clear-groups dotnet SwarmUI.dll --launch_mode none --host 0.0.0.0' >> /usr/local/bin/entrypoint.sh && \
    echo '    else' >> /usr/local/bin/entrypoint.sh && \
    echo '        exec dotnet SwarmUI.dll --launch_mode none --host 0.0.0.0' >> /usr/local/bin/entrypoint.sh && \
    echo '    fi' >> /usr/local/bin/entrypoint.sh && \
    echo 'else' >> /usr/local/bin/entrypoint.sh && \
    echo '    exec dotnet SwarmUI.dll --launch_mode none --host 0.0.0.0' >> /usr/local/bin/entrypoint.sh && \
    echo 'fi' >> /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
