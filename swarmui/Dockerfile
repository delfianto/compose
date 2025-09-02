# --- Build Stage ---
FROM mcr.microsoft.com/dotnet/sdk:8.0-bookworm-slim AS build

ENV UID=1000
ENV GID=1000
ENV SWARMUI_ROOT=/SwarmUI

WORKDIR /tmp
COPY compose.sh .

# Consolidate all build steps
RUN bash /tmp/compose.sh --stage1

# --- Runtime Stage ---
FROM mcr.microsoft.com/dotnet/sdk:8.0-bookworm-slim AS runtime

ENV UID=1000
ENV GID=1000
ENV SWARMUI_ROOT=/SwarmUI

# Copy the final application and its entrypoint script from the build stage
# Also recreate the swarmui user and group with the same UID and GID
COPY --from=build --chown=$UID:$GID /tmp/compose.sh /tmp/compose.sh
COPY --from=build --chown=$UID:$GID $SWARMUI_ROOT $SWARMUI_ROOT
RUN bash /tmp/compose.sh --stage2

# Expose the port
EXPOSE $SWARMUI_PORT

# Set the entrypoint
ENTRYPOINT ["/bin/bash", "-c", "exec $SWARMUI_ROOT/run.sh"]
