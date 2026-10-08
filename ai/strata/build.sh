#!/bin/sh
# Project env files are trusted, shell-compatible assignments.
# Bake HCL reads variables from the process environment, not Compose env files.
set -eu
cd -- "$(dirname -- "$0")"
set -a
. ./.env
if [ -f .env.local ]; then
    . ./.env.local
fi
set +a
exec docker buildx bake -f docker-bake.hcl "$@"
