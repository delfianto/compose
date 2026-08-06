#!/usr/bin/env bash
set -Eeuo pipefail

COMFYUI_DIR="${COMFYUI_DIR:-/opt/ComfyUI}"
COMFYUI_REPOSITORY="${COMFYUI_REPOSITORY:-https://github.com/Comfy-Org/ComfyUI.git}"
COMFYUI_REF="${COMFYUI_REF:-master}"
COMFYUI_AUTO_UPDATE="${COMFYUI_AUTO_UPDATE:-true}"
COMFYUI_UPDATE_STRICT="${COMFYUI_UPDATE_STRICT:-false}"
COMFYUI_INSTALL_CUSTOM_NODE_REQUIREMENTS="${COMFYUI_INSTALL_CUSTOM_NODE_REQUIREMENTS:-true}"
REQUIREMENTS_STAMP=/opt/comfy-requirements.sha256
CUSTOM_REQUIREMENTS_STAMP=/opt/comfy-custom-requirements.sha256

is_true() {
    case "${1,,}" in
        1|true|yes|on) return 0 ;;
        *) return 1 ;;
    esac
}

update_comfyui() {
    local previous_commit
    previous_commit="$(git -C "${COMFYUI_DIR}" rev-parse --short HEAD)"

    git -C "${COMFYUI_DIR}" remote set-url origin "${COMFYUI_REPOSITORY}"
    if git -C "${COMFYUI_DIR}" fetch --depth=1 origin "${COMFYUI_REF}"; then
        git -C "${COMFYUI_DIR}" reset --hard FETCH_HEAD
        git -C "${COMFYUI_DIR}" clean -fd
        printf 'ComfyUI update: %s -> %s\n' \
            "${previous_commit}" \
            "$(git -C "${COMFYUI_DIR}" rev-parse --short HEAD)"
        return 0
    fi

    printf 'Warning: could not update ComfyUI from %s; using bundled commit %s.\n' \
        "${COMFYUI_REF}" "${previous_commit}" >&2
    if is_true "${COMFYUI_UPDATE_STRICT}"; then
        return 1
    fi
}

sync_requirements() {
    local current_hash installed_hash
    current_hash="$(
        cd "${COMFYUI_DIR}"
        sha256sum requirements.txt manager_requirements.txt \
            | sha256sum | cut -d ' ' -f 1
    )"
    installed_hash="$(cat "${REQUIREMENTS_STAMP}" 2>/dev/null || true)"

    if [[ "${current_hash}" == "${installed_hash}" ]]; then
        return 0
    fi

    printf 'ComfyUI requirements changed; synchronizing Python packages.\n'
    uv pip install --python "${VIRTUAL_ENV}/bin/python" \
        -r "${COMFYUI_DIR}/requirements.txt" \
        -r "${COMFYUI_DIR}/manager_requirements.txt"
    printf '%s\n' "${current_hash}" > "${REQUIREMENTS_STAMP}"
}

sync_custom_node_requirements() {
    local current_hash installed_hash requirement
    local -a requirements=()

    mapfile -d '' -t requirements < <(
        find /data/custom_nodes -mindepth 2 -maxdepth 4 \
            -type f -name requirements.txt -print0 | sort -z
    )
    if (( ${#requirements[@]} == 0 )); then
        return 0
    fi

    current_hash="$({
        for requirement in "${requirements[@]}"; do
            printf '%s\0' "${requirement}"
            sha256sum "${requirement}"
        done
    } | sha256sum | cut -d ' ' -f 1)"
    installed_hash="$(cat "${CUSTOM_REQUIREMENTS_STAMP}" 2>/dev/null || true)"
    if [[ "${current_hash}" == "${installed_hash}" ]]; then
        return 0
    fi

    printf 'Custom-node requirements changed; synchronizing Python packages.\n'
    for requirement in "${requirements[@]}"; do
        printf 'Installing %s\n' "${requirement}"
        uv pip install --python "${VIRTUAL_ENV}/bin/python" -r "${requirement}"
    done
    printf '%s\n' "${current_hash}" > "${CUSTOM_REQUIREMENTS_STAMP}"
}

if is_true "${COMFYUI_AUTO_UPDATE}"; then
    update_comfyui
fi

sync_requirements
if is_true "${COMFYUI_INSTALL_CUSTOM_NODE_REQUIREMENTS}"; then
    sync_custom_node_requirements
fi
cd "${COMFYUI_DIR}"
exec "$@"
