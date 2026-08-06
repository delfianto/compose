# ComfyUI

Locally built ComfyUI runtime using NVIDIA's Ubuntu 24.04 CUDA 13.2 base image. The
container updates the ComfyUI checkout to `COMFYUI_REF` whenever it starts and
installs changed core/Manager requirements before launching.

The resulting local image is tagged
`ghcr.io/delfianto/comfyui-nvidia-cuda:latest`; building does not publish it.

The image also includes build-time snapshots of
[ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) and
[ComfyUI-MultiGPU](https://github.com/pollockjj/ComfyUI-MultiGPU). They live in
`/opt/custom_nodes` and are added through `/opt/comfy-extra-model-paths.yaml`.
This keeps image-owned nodes separate from Manager-installed nodes in the
persisted `/data/custom_nodes` bind mount.

PyTorch 2.11, TorchVision 0.26, and TorchAudio 2.11 are installed as a matched
set from PyTorch's CUDA 13.0 wheel channel. CUDA 13.x minor compatibility lets
those wheels run with the CUDA 13.2 host interface. The PyTorch wheels supply
the CUDA workload libraries and cuDNN, avoiding duplication with NVIDIA's
larger `runtime`/`cudnn-runtime` images. This also avoids PyTorch 2.12's currently
incomplete CUDA 13.2 set, which has no matching TorchAudio wheel even though
ComfyUI still imports TorchAudio.

The source checkout and Python environment are intentionally disposable
container state. Models, inputs, user data, custom nodes, and download caches
live together under `${DATA_DIR}` (`/srv/appdata/comfyui` by default); generated
images remain in `${OUTPUT_DIR}`. ComfyUI's SQLite database is
explicitly stored at `/data/user/comfyui.db`; `--base-directory` alone does not
relocate the database from its source-tree default.

## Build and run

```sh
docker compose build --pull
composectl start ai-comfyui
```

Use `composectl restart ai-comfyui` to fetch the configured ComfyUI ref on the
next start. Rebuild periodically with `docker compose build --pull` to update
the PyTorch/CUDA base and to reset any Python packages modified by custom nodes.

## Update policy

- `COMFYUI_REF=master` follows current ComfyUI on each container start.
- Set `COMFYUI_REF` to a tag or commit SHA for a reproducible deployment.
- `COMFYUI_UPDATE_STRICT=false` allows startup from the image's bundled commit
  when the remote is unavailable. Set it to `true` to fail closed.
- Core and Manager dependency files are hashed. Pip runs only after those files
  change.
- `COMFYUI_INSTALL_CUSTOM_NODE_REQUIREMENTS=true` discovers and installs each
  persisted custom node's `requirements.txt`; hashes avoid repeat work on an
  ordinary restart.
- `COMFYUI_GGUF_REF=main` and `COMFYUI_MULTIGPU_REF=main` capture the latest
  commits of the image-owned custom nodes during each build. Existing images
  and containers do not update automatically; rebuild to refresh them. A commit
  SHA can still be used temporarily when bisecting a regression. Do not update
  these copies through ComfyUI Manager.

ComfyUI Manager can mutate `/data/custom_nodes` and install Python packages in
the container. The nodes persist; their installed packages do not survive a
container recreation. The entrypoint restores declared node requirements,
while a rebuild provides a clean runtime when node dependencies become tangled.

No host port is published. Access is through the existing Traefik `proxy`
network at `https://comfyui.${TRAEFIK_ACME_DOMAIN}`.

Forge Neo mounts the same `${DATA_DIR}` and uses
`--forge-ref-comfy-home /comfyui` to discover compatible ComfyUI model folders.
This shares model files only; Forge remains a separate inference application
and does not use the running ComfyUI service as its backend.

## GGUF and multiple GPUs

ComfyUI-GGUF adds quantized diffusion-model and text-encoder loaders. Put GGUF
diffusion models in `${DATA_DIR}/models/diffusion_models` (or the legacy
`models/unet` directory) and GGUF text encoders in `${DATA_DIR}/models/clip`.
The existing GGUF files in `${DATA_DIR}/models/hf` are MiniMax H3/Qwen assets,
not standard diffusion UNets, so they remain associated with the existing
MiniMax workflows rather than the generic GGUF loaders.

ComfyUI-MultiGPU exposes `cuda:0`, `cuda:1`, and CPU choices on its loader
nodes. It controls where whole components are loaded and, with DisTorch2,
where model layers are stored. It does not execute arbitrary workflow nodes in
parallel. On this host:

- `cuda:0` is the 16 GB RTX 4080 and should normally run UNet/sampling compute.
- `cuda:1` is the 12 GB RTX 3060 and is useful for CLIP, VAE, or as a DisTorch2
  donor, subject to VRAM used by other services assigned to GPU 1.
- The GPUs have no CUDA peer-to-peer path. Cross-GPU model splitting travels
  through PCIe, so use only as much donor VRAM as needed for the model to fit.

## Predefined workflows

Workflows are persisted under `${DATA_DIR}/user/default/workflows` and appear
in ComfyUI's workflow browser:

- `SDXL-Pony-Dual-GPU.json` uses the installed
  `pony-reapony-v10.safetensors`: UNet on `cuda:0`, CLIP and VAE on `cuda:1`.
- `FLUX-Dev-FP8-DisTorch2-Dual-GPU.json` uses the installed all-in-one
  `flux1-dev-fp8.safetensors`: UNet compute on `cuda:0`, 4 GB of DisTorch2
  donor capacity from `cuda:1`, and CLIP/VAE on `cuda:1`.

These are starting allocations, not universal performance presets. Reduce the
FLUX workflow's `virtual_vram_gb` when the model fits without it, or move
CLIP/VAE to CPU when GPU 1 is occupied.

## Rootless Docker

The service deliberately runs as container uid/gid `0:0`. Under this host's
rootless user namespace, container uid 0 maps to the Docker daemon owner on the
host (uid/gid 1000), while container uid 1000 would map into the subordinate-id
range and could not write the existing bind mounts.

The Compose service drops every Linux capability and enables
`no-new-privileges`. Persistent directories must remain owned and writable by
the rootless daemon owner. NVIDIA CDI devices and the external `genai` and
`proxy` networks must be configured for that same rootless daemon.
