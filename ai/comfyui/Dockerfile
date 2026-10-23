# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE=ghcr.io/delfianto/comfyui-cuda:13.4.2-base-ubuntu26.04
FROM ${BASE_IMAGE}

# Host CachyOS Proton supplies Wine/DXVK/vkd3d/NVAPI through a read-only bind.
# Keep Linux libraries in the Ubuntu image and Wine state in a separate prefix.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        xvfb xauth vulkan-tools libvulkan1 \
        libx11-6 libxext6 libxrender1 libxrandr2 libxi6 libxcursor1 libxinerama1 \
        libfontconfig1 libfreetype6 fonts-liberation libasound2t64 libpulse0 \
    && rm -rf /var/lib/apt/lists/*

# Proton's bootstrap also invokes its 32-bit loader, even for a 64-bit prefix.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libc6-i386 lib32gcc-s1 \
    && rm -rf /var/lib/apt/lists/*

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libfreetype6:i386 libfontconfig1:i386 libx11-6:i386 libxext6:i386 \
        libxrender1:i386 libxrandr2:i386 libxi6:i386 libxcursor1:i386 \
    && rm -rf /var/lib/apt/lists/*

ARG COMFYUI_REPOSITORY=https://github.com/Comfy-Org/ComfyUI.git
ARG COMFYUI_REF=latest-stable
ENV COMFYUI_REF=${COMFYUI_REF} \
    COMFYUI_AUTO_UPDATE=false
LABEL org.opencontainers.image.version=${COMFYUI_REF}
COPY --chmod=755 resolve-comfy-ref.py /usr/local/bin/comfy-resolve-ref

RUN git init "${COMFYUI_DIR}" \
    && git -C "${COMFYUI_DIR}" remote add origin "${COMFYUI_REPOSITORY}" \
    && resolved_ref="$(python3 /usr/local/bin/comfy-resolve-ref "${COMFYUI_REPOSITORY}" "${COMFYUI_REF}")" \
    && git -C "${COMFYUI_DIR}" fetch --depth=1 origin "${resolved_ref}" \
    && git -C "${COMFYUI_DIR}" checkout --detach FETCH_HEAD

WORKDIR ${COMFYUI_DIR}

# The matching CUDA-enabled Torch trio is installed first, so ComfyUI's
# unversioned torch requirements cannot silently select CPU or mismatched wheels.
RUN --mount=type=cache,target=/var/cache/uv \
    uv pip install --python "${VIRTUAL_ENV}/bin/python" \
        -r requirements.txt -r manager_requirements.txt \
    && sha256sum requirements.txt manager_requirements.txt \
       | sha256sum | cut -d ' ' -f 1 > /opt/comfy-requirements.sha256

COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/comfy-entrypoint

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
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188", "--base-directory", "/data", "--database-url", "sqlite:////data/user/comfyui.db", "--enable-manager", "--reserve-vram", "2.0"]
