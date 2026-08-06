# syntax=docker/dockerfile:1.7

ARG CUDA_IMAGE=nvidia/cuda:13.2.1-base-ubuntu24.04
FROM ${CUDA_IMAGE}

ARG COMFYUI_REPOSITORY=https://github.com/Comfy-Org/ComfyUI.git
ARG COMFYUI_REF=master
ARG COMFYUI_GGUF_REPOSITORY=https://github.com/city96/ComfyUI-GGUF.git
ARG COMFYUI_GGUF_REF=main
ARG COMFYUI_MULTIGPU_REPOSITORY=https://github.com/pollockjj/ComfyUI-MultiGPU.git
ARG COMFYUI_MULTIGPU_REF=main
ARG TORCH_VERSION=2.11.0
ARG TORCHVISION_VERSION=0.26.0
ARG TORCHAUDIO_VERSION=2.11.0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu130

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/var/cache/huggingface \
    TORCH_HOME=/var/cache/torch \
    UV_CACHE_DIR=/var/cache/uv \
    UV_LINK_MODE=copy \
    COMFYUI_DIR=/opt/ComfyUI \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        ffmpeg \
        git \
        git-lfs \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        ninja-build \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN --mount=type=cache,target=/var/cache/uv \
    python3 -m venv "${VIRTUAL_ENV}" \
    && uv pip install --python "${VIRTUAL_ENV}/bin/python" --upgrade pip setuptools wheel \
    && uv pip install --python "${VIRTUAL_ENV}/bin/python" \
        "torch==${TORCH_VERSION}" \
        "torchvision==${TORCHVISION_VERSION}" \
        "torchaudio==${TORCHAUDIO_VERSION}" \
        --index-url "${TORCH_INDEX_URL}"

RUN git init "${COMFYUI_DIR}" \
    && git -C "${COMFYUI_DIR}" remote add origin "${COMFYUI_REPOSITORY}" \
    && git -C "${COMFYUI_DIR}" fetch --depth=1 origin "${COMFYUI_REF}" \
    && git -C "${COMFYUI_DIR}" checkout --detach FETCH_HEAD

WORKDIR ${COMFYUI_DIR}

# The matching CUDA-enabled Torch trio is installed first, so ComfyUI's
# unversioned torch requirements cannot silently select CPU or mismatched wheels.
RUN --mount=type=cache,target=/var/cache/uv \
    uv pip install --python "${VIRTUAL_ENV}/bin/python" \
        -r requirements.txt -r manager_requirements.txt \
    && sha256sum requirements.txt manager_requirements.txt \
       | sha256sum | cut -d ' ' -f 1 > /opt/comfy-requirements.sha256

# Image-owned nodes are kept outside /data/custom_nodes because that path is a
# persistent bind mount. Their configured refs are captured at build time while
# /data/custom_nodes remains available to Manager.
RUN --mount=type=cache,target=/var/cache/uv \
    mkdir -p /opt/custom_nodes \
    && git init /opt/custom_nodes/ComfyUI-GGUF \
    && git -C /opt/custom_nodes/ComfyUI-GGUF remote add origin "${COMFYUI_GGUF_REPOSITORY}" \
    && git -C /opt/custom_nodes/ComfyUI-GGUF fetch --depth=1 origin "${COMFYUI_GGUF_REF}" \
    && git -C /opt/custom_nodes/ComfyUI-GGUF checkout --detach FETCH_HEAD \
    && git init /opt/custom_nodes/ComfyUI-MultiGPU \
    && git -C /opt/custom_nodes/ComfyUI-MultiGPU remote add origin "${COMFYUI_MULTIGPU_REPOSITORY}" \
    && git -C /opt/custom_nodes/ComfyUI-MultiGPU fetch --depth=1 origin "${COMFYUI_MULTIGPU_REF}" \
    && git -C /opt/custom_nodes/ComfyUI-MultiGPU checkout --detach FETCH_HEAD \
    && uv pip install --python "${VIRTUAL_ENV}/bin/python" \
        -r /opt/custom_nodes/ComfyUI-GGUF/requirements.txt

COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/comfy-entrypoint
COPY extra_model_paths.yaml /opt/comfy-extra-model-paths.yaml

RUN mkdir -p \
        /data/models \
        /data/input \
        /data/output \
        /data/user \
        /data/custom_nodes \
        /data/temp \
        /var/cache/huggingface \
        /var/cache/torch

EXPOSE 8188

ENTRYPOINT ["/usr/local/bin/comfy-entrypoint"]
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188", "--base-directory", "/data", "--database-url", "sqlite:////data/user/comfyui.db", "--extra-model-paths-config", "/opt/comfy-extra-model-paths.yaml", "--enable-manager", "--reserve-vram", "2.0"]
