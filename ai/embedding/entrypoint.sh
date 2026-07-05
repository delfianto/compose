#!/bin/bash
set -e

if [[ -f "${HF_TOKEN_FILE}" ]]; then
  export HF_TOKEN=$(cat "${HF_TOKEN_FILE}")
fi

exec /entrypoint.sh "$@"
