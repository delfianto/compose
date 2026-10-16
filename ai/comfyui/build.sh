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

# Remove our option while preserving all remaining Bake arguments and quoting.
requested_version=latest-stable
needs_version=true
runtime_target=false
for arg do
    case "$arg" in
        --help|-h)
            printf 'Usage: ./build.sh [--version VERSION] [BAKE OPTIONS] [TARGETS]\n\nOmit --version (or use latest) for the latest stable ComfyUI release.\nBuilds comfyui-nvidia-cuda:latest and :vX.Y.Z, with CUDA and DLSS.\nUse target base to build only the reusable CUDA/PyTorch base.\n'
            exit 0
            ;;
        base) needs_version=false ;;
        comfyui|default) runtime_target=true ;;
    esac
done
remaining=$#
while [ "$remaining" -gt 0 ]; do
    arg=$1
    shift
    remaining=$((remaining - 1))
    case "$arg" in
        --version)
            if [ "$remaining" -eq 0 ] || [ -z "$1" ]; then
                printf '%s\n' '--version requires a release version, e.g. v0.3.60' >&2
                exit 2
            fi
            requested_version=$1
            shift
            remaining=$((remaining - 1))
            ;;
        --version=*)
            requested_version=${arg#*=}
            ;;
        *) set -- "$@" "$arg" ;;
    esac
done
if [ "$runtime_target" = true ]; then
    needs_version=true
fi
if [ "$needs_version" = true ]; then
    case "$requested_version" in
        latest|latest-stable) requested_version=latest-stable ;;
        *)
            requested_version=v${requested_version#v}
            if ! printf '%s\n' "$requested_version" | LC_ALL=C grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
                printf 'Invalid release version: %s\n' "$requested_version" >&2
                exit 2
            fi
            ;;
    esac
    COMFYUI_REF=$(python3 ./resolve-comfy-ref.py "$COMFYUI_REPOSITORY" "$requested_version")
    export COMFYUI_REF
    # Fail before building if an explicit release tag does not exist.
    if [ "$requested_version" != latest-stable ]; then
        refs=$(git ls-remote --exit-code --tags "$COMFYUI_REPOSITORY" "refs/tags/$COMFYUI_REF")
        [ -n "$refs" ]
    fi
    printf 'Building ComfyUI %s as %s:latest and %s:%s\n' \
        "$COMFYUI_REF" "$IMAGE_NAME" "$IMAGE_NAME" "$COMFYUI_REF" >&2
fi
for arg do
    case "$arg" in
        --check|--call=check)
            set -- --set '*.output=type=cacheonly' "$@"
            break
            ;;
    esac
done
exec docker buildx bake -f docker-bake.hcl "$@"
