#!/bin/sh
# Project env files are trusted, shell-compatible assignments (as in ComfyUI).
set -eu
cd -- "$(dirname -- "$0")"
set -a
if [ -f .env ]; then . ./.env; fi
if [ -f .env.local ]; then . ./.env.local; fi
set +a

remaining=$#
while [ "$remaining" -gt 0 ]; do
    arg=$1
    shift
    remaining=$((remaining - 1))
    case "$arg" in
        --help|-h)
            printf 'Usage: ./build.sh [--ref BRANCH|TAG|COMMIT] [BAKE OPTIONS] [TARGETS]\n\nBuilds the remote source as :latest and :<short-commit>.\nDefaults to LYCHEE_REF from .env / .env.local.\nExamples: ./build.sh --pull; ./build.sh --ref main --print\n'
            exit 0
            ;;
        --ref)
            if [ "$remaining" -eq 0 ] || [ -z "$1" ]; then
                printf '%s\n' '--ref requires a branch, tag, or commit' >&2
                exit 2
            fi
            LYCHEE_REF=$1
            shift
            remaining=$((remaining - 1))
            ;;
        --ref=*) LYCHEE_REF=${arg#*=} ;;
        *) set -- "$@" "$arg" ;;
    esac
done

# Resolve mutable refs before Bake so a new commit invalidates the source layer.
# Fetching also validates explicit commits before starting an expensive build.
ref_dir=$(mktemp -d)
trap 'rm -rf -- "$ref_dir"' EXIT HUP INT TERM
git -C "$ref_dir" init --quiet
git -C "$ref_dir" fetch --quiet --depth=1 "$LYCHEE_REPOSITORY" "$LYCHEE_REF"
LYCHEE_REF=$(git -C "$ref_dir" rev-parse FETCH_HEAD)
short_ref=$(git -C "$ref_dir" rev-parse --short=7 FETCH_HEAD)
LYCHEE_IMAGE_TAG=$short_ref
export LYCHEE_REF LYCHEE_IMAGE_TAG
printf 'Building %s at %s as %s:latest and %s:%s\n' \
    "$LYCHEE_REPOSITORY" "$short_ref" "$IMAGE_NAME" "$IMAGE_NAME" "$LYCHEE_IMAGE_TAG" >&2
for arg do
    case "$arg" in
        --check|--call=check)
            set -- --set '*.output=type=cacheonly' "$@"
            break
            ;;
    esac
done
docker buildx bake -f docker-bake.hcl "$@"
