# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE=ghcr.io/delfianto/comfyui-base:cuda13.4.2-torch2.11.0
FROM ${BASE_IMAGE}

ARG COMFYUI_REPOSITORY=https://github.com/Comfy-Org/ComfyUI.git
ARG COMFYUI_REF=latest-stable
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
