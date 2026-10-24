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
            printf 'Usage: ./build.sh [--ref RELEASE_TAG] [BAKE OPTIONS] [TARGETS]\n\nBuilds the remote release as :latest and :v<version>.\nDefaults to LYCHEE_REF from .env / .env.local.\nExamples: ./build.sh --pull; ./build.sh --ref v0.1.0-beta.1 --print\n'
            exit 0
            ;;
        --ref)
            if [ "$remaining" -eq 0 ] || [ -z "$1" ]; then
                printf '%s\n' '--ref requires a release tag' >&2
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

# Build an explicit release tag; keep its exact commit as the source cache key.
# Refuse branch/hash builds so an unreleased commit cannot overwrite a release tag.
release_tag=$LYCHEE_REF
case "$release_tag" in
    v[0-9]*.[0-9]*.[0-9]*) ;;
    *) printf '%s\n' '--ref must be a version tag such as v0.1.0-beta.1' >&2; exit 2 ;;
esac
ref_dir=$(mktemp -d)
trap 'rm -rf -- "$ref_dir"' EXIT HUP INT TERM
git -C "$ref_dir" init --quiet
git -C "$ref_dir" fetch --quiet --depth=1 "$LYCHEE_REPOSITORY" "refs/tags/$release_tag"
LYCHEE_REF=$(git -C "$ref_dir" rev-parse 'FETCH_HEAD^{commit}')
LYCHEE_VERSION=$(git -C "$ref_dir" show "$LYCHEE_REF:frontend/package.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')
if [ "$release_tag" != "v$LYCHEE_VERSION" ]; then
    printf 'Release tag %s does not match app version %s\n' "$release_tag" "$LYCHEE_VERSION" >&2
    exit 2
fi
LYCHEE_IMAGE_TAG=$release_tag
export LYCHEE_REF LYCHEE_IMAGE_TAG LYCHEE_VERSION
printf 'Building %s at %s as %s:latest and %s:%s\n' \
    "$LYCHEE_REPOSITORY" "$LYCHEE_REF" "$IMAGE_NAME" "$IMAGE_NAME" "$LYCHEE_IMAGE_TAG" >&2
for arg do
    case "$arg" in
        --check|--call=check)
            set -- --set '*.output=type=cacheonly' "$@"
            break
            ;;
    esac
done
docker buildx bake -f docker-bake.hcl "$@"
