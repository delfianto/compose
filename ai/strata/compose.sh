#!/bin/sh
# Preserve the host-wide interpolation layer and load this project's override.
set -eu
cd -- "$(dirname -- "$0")"
# Compose is the runtime definition; Bake owns the HCL build definition.
if [ "${1:-}" = build ]; then
    shift
    exec ./build.sh "$@"
fi
unset COMPOSE_ENV_FILES
global_env_file="${XDG_CONFIG_HOME:-$HOME/.config}/docker/compose.env"
for env_file in .env.local .env "$global_env_file"; do
    if [ -f "$env_file" ]; then
        set -- --env-file "$env_file" "$@"
    fi
done
exec docker compose "$@"
