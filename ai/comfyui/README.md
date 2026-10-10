# ComfyUI

Locally built ComfyUI runtime using NVIDIA's Ubuntu 24.04 CUDA 13.4.2 base image. The
container updates the ComfyUI checkout to `COMFYUI_REF` whenever it starts and
installs changed core/Manager requirements before launching.

The resulting local image is tagged
`ghcr.io/delfianto/comfyui-nvidia-cuda:latest`; building does not publish it.

Custom nodes are persistent Git checkouts under `/srv/appdata/comfyui/custom_nodes`,
mounted at `/data/custom_nodes`, including
[ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) and
[our MultiGPU fork](https://github.com/delfianto/ComfyUI-MultiGPU).
Their edits and updates survive image rebuilds; restart ComfyUI after changing
Python code. Neither node is installed in the image.

PyTorch 2.11, TorchVision 0.26, and TorchAudio 2.11 are installed as a matched
set from PyTorch's CUDA 13.0 wheel channel. The wheels supply the CUDA workload
libraries and cuDNN, avoiding duplication with NVIDIA's larger
`runtime`/`cudnn-runtime` images. Updating the base to CUDA 13.4.2 does not
change `torch.version.cuda` from 13.0 or automatically improve inference speed.
TorchAudio remains included because ComfyUI imports it.

The fork handles versioned CUDA runtime libraries and treats P2P detection
failures as a request to stage transfers through host memory. It also guards
CLIP inference with the encoder's actual load device, preventing FP8 encoder
tensors from being moved onto the diffusion GPU during text encoding.
These compatibility fixes live in the fork rather than Dockerfile patches.

[NVIDIA's compatibility documentation](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)
lists driver 580 or newer for CUDA 13.x. This host uses driver 615.71.09;
compatibility also depends on the libraries and features a workflow uses.
The CUDA 13.4.2 image passed FP16 matrix multiplication, convolution, and
attention checks on both the RTX 4080 and RTX 3060, plus ComfyUI startup and an
HTTP `/system_stats` probe. These checks do not cover every custom workflow.

The source checkout and Python environment are intentionally disposable
container state. Models, inputs, user data, custom nodes, and download caches
live together under `${DATA_DIR}` (`/srv/appdata/comfyui` by default); generated
images remain in `${OUTPUT_DIR}`. ComfyUI's SQLite database is
explicitly stored at `/data/user/comfyui.db`; `--base-directory` alone does not
relocate the database from its source-tree default.

The Python environment remains disposable image/container state. Dependency
installation uses `uv pip`, with its cache persisted at `${DATA_DIR}/cache/uv`,
so custom-node requirements can be reconstructed after a container recreation
without downloading unchanged wheels again. Regular `pip` remains installed in
the venv for third-party custom nodes that invoke it directly. Docker builds use
a BuildKit cache mount for `uv` without embedding its cache in image layers.

## Build and run

[docker-bake.hcl](docker-bake.hcl) owns the build definition; Compose owns the
runtime configuration. `./build.sh` loads shell-compatible `.env` assignments
and then optional `.env.local` overrides before invoking Docker Buildx Bake.
The default target builds for `linux/amd64` and loads the image into the local
Docker daemon with the configured `IMAGE_NAME:IMAGE_TAG`. It does not push it.

Inspect the resolved build settings with `./build.sh --print`, or validate the
Dockerfile with `./build.sh --check comfyui` (without exporting an image), then
build:

```sh
./build.sh --pull comfyui
composectl start ai-comfyui
```

Use `composectl restart ai-comfyui` to fetch the configured ComfyUI ref on the
next start. Rebuild periodically with `./build.sh --pull comfyui` to update
the PyTorch/CUDA base and to reset any Python packages modified by custom nodes.

ComfyUI MCP now lives in [../comfyui-mcp](../comfyui-mcp/README.md) with its own
systemd unit. `composectl restart ai-comfyui` updates ComfyUI without restarting
MCP. Run `/srv/compose/ai/comfyui-mcp/update.py` to build the latest stable MCP
release and restart MCP independently.

Docker caches source-fetching build layers. Add `--no-cache` when rebuilding to
refresh the bundled ComfyUI snapshot even if its configured ref has not changed.

## Update policy

- `COMFYUI_REF=latest-stable` resolves GitHub's latest stable release at build
  time and on each container start. Prereleases and unreleased master commits
  are excluded.
- Set `COMFYUI_REF` to a tag or commit SHA for a reproducible deployment.
- `COMFYUI_UPDATE_STRICT=false` allows startup from the image's bundled commit
  when the remote is unavailable. Set it to `true` to fail closed.
- Core and Manager dependency files are hashed. Pip runs only after those files
  change.
- `COMFYUI_INSTALL_CUSTOM_NODE_REQUIREMENTS=true` discovers and installs each
  persisted custom node's `requirements.txt`; hashes avoid repeat work on an
  ordinary restart.
- GGUF is maintained in its persistent checkout or through ComfyUI Manager.
  Restart ComfyUI after updating it.
- MultiGPU is maintained in its persistent checkout. Review and update its Git
  branch there, then run `composectl restart ai-comfyui --json` to load changes.
  Its development checks and upstream issue review are documented in the fork's
  `docs/MAINTENANCE.md`.

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

## Node caching

Normal runs use ComfyUI's default RAM-pressure node caching. The switching
stress test used `--cache-none` as a diagnostic workaround; it is no longer a
runtime default. When finished with a workflow, `POST /free` with
`{"unload_models": true, "free_memory": true}` requests model unloading and
executor-cache cleanup after the active generation finishes. Automatic cleanup
at workflow boundaries and memory reclamation with caching enabled still need
validation; switching workflows does not yet trigger this request automatically.

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
