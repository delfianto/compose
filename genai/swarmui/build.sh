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

GHCR_IMAGE=${GHCR_IMAGE:-"ghcr.io/username/swarmui"}
SWARMUI_VERSION=${SWARMUI_VERSION:-"latest"}

if [[ "$GHCR_IMAGE" == *"your_github_username"* ]] || [[ "$GHCR_IMAGE" == *"username"* ]]; then
  echo "WARNING: GHCR_IMAGE is set to a placeholder ($GHCR_IMAGE)."
  echo "Please set GHCR_IMAGE in your .env file to your actual GitHub Container Registry path."
  echo "Example: GHCR_IMAGE=ghcr.io/octocat/swarmui"

  if [ "$ACTION_PUSH" = true ]; then
      echo "ERROR: Cannot push with a placeholder registry. Exiting."
      exit 1
  fi
fi

if [[ "$ACTION_BUILD" = true ]]; then
    echo "Building SwarmUI image: ${GHCR_IMAGE}:${SWARMUI_VERSION}"
    docker compose build swarmui
fi

if [[ "$ACTION_PUSH" = true ]]; then
    echo "Pushing image to ${GHCR_IMAGE}:${SWARMUI_VERSION}..."
    docker compose push swarmui

    echo "Done! You can now pull this image using:"
    echo "  docker pull ${GHCR_IMAGE}:${SWARMUI_VERSION}"
fi
