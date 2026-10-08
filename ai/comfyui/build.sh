#!/bin/sh
# Project env files are trusted, shell-compatible assignments.
set -eu
cd -- "$(dirname -- "$0")"
set -a
if [ -f .env ]; then
    . ./.env
fi
if [ -f .env.local ]; then
    . ./.env.local
fi
set +a
for arg do
    case "$arg" in
        --check|--call=check)
            set -- --set '*.output=type=cacheonly' "$@"
            break
            ;;
    esac
done
exec docker buildx bake -f docker-bake.hcl "$@"
