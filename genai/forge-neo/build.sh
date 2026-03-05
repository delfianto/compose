#!/usr/bin/env bash
set -e

# Default action is just build if no arguments are provided
ACTION_BUILD=true
ACTION_PUSH=false

# If arguments are provided, reset defaults so we only do what is asked
if [[ $# -gt 0 ]]; then
  ACTION_BUILD=false
fi

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --build) ACTION_BUILD=true ;;
        --push) ACTION_PUSH=true ;;
        -h|--help)
            echo "Usage: $0 [--build] [--push]"
            echo "  --build : Build the docker image (default if no args)"
            echo "  --push  : Push the docker image to GHCR"
            exit 0
            ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Load variables from .env if present
if [[ -f .env ]]; then
  source .env
fi

if [[ -z "$GHCR_IMG" ]] || [[ -z "$GHCR_VER" ]]; then
  echo "Please set GHCR_IMG and GHCR_VER in your .env file to GitHub Container Registry path."
  echo "Example: GHCR_IMG=ghcr.io/octocat/forge-neo"
  echo "Example: GHCR_VER=latest"
  exit 1
fi

if [[ "$ACTION_BUILD" = true ]]; then
    echo "Building Forge Neo image: ${GHCR_IMG}:${GHCR_VER}"
    docker compose build forge-neo
fi

if [[ "$ACTION_PUSH" = true ]]; then
    echo "Pushing image to ${GHCR_IMG}:${GHCR_VER}..."
    docker compose push forge-neo

    echo "Done! You can now pull this image using:"
    echo "  docker pull ${GHCR_IMG}:${GHCR_VER}"
fi
