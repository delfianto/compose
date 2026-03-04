# --- Build Stage ---
FROM mcr.microsoft.com/dotnet/sdk:8.0-bookworm-slim AS build

ARG SWARMUI_UID=1000
ARG SWARMUI_GID=1000
ARG SWARMUI_VERSION=latest

ENV SWARMUI_UID=${SWARMUI_UID}
ENV SWARMUI_GID=${SWARMUI_GID}
ENV SWARMUI_VERSION=${SWARMUI_VERSION}
ENV SWARMUI_ROOT=/SwarmUI

WORKDIR /tmp
COPY compose.sh .

# Consolidate all build steps
RUN bash /tmp/compose.sh --stage1

# --- Runtime Stage ---
FROM mcr.microsoft.com/dotnet/sdk:8.0-bookworm-slim AS runtime

ARG SWARMUI_UID=1000
ARG SWARMUI_GID=1000
ARG SWARMUI_VERSION=latest
ARG SWARMUI_PORT=7801

ENV SWARMUI_UID=${SWARMUI_UID}
ENV SWARMUI_GID=${SWARMUI_GID}
ENV SWARMUI_VERSION=${SWARMUI_VERSION}
ENV SWARMUI_ROOT=/SwarmUI
ENV SWARMUI_PORT=${SWARMUI_PORT}

# Copy the build script and install runtime dependencies
COPY compose.sh /tmp/compose.sh
RUN bash /tmp/compose.sh --stage2

# Copy the final application and its entrypoint script from the build stage
# Store it in a pristine location so the entrypoint can copy it to the persistent volume
COPY --from=build --chown=$SWARMUI_UID:$SWARMUI_GID $SWARMUI_ROOT /SwarmUI_pristine

# Expose the port
EXPOSE $SWARMUI_PORT

# Set the entrypoint to the wrapper script that populates the volume
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
