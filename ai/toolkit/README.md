# AI Toolkit

Ostris AI Toolkit (`ostris/aitoolkit`) for LoRA training on consumer GPUs.
The container is on-demand and exposes GPU 0 (RTX 4080) and GPU 1 (RTX 3060).
Use GPU 0 for training and GPU 1 for captioning. GPU 1
is also shared by other homelab services; check available VRAM before captioning.
The UI is at
`https://toolkit.${TRAEFIK_ACME_DOMAIN}` and is gated by `AI_TOOLKIT_AUTH`.
The [MCP adapter](mcp_adapter/README.md) runs inside the same container at
`https://toolkit-mcp.${TRAEFIK_ACME_DOMAIN}/mcp`, using the same bearer token.
Harnesses can manage UI jobs, datasets, GPU queues, logs, samples and LoRAs
through reusable tools.

```sh
composectl start ai-toolkit
composectl stop ai-toolkit
```

Do not leave a training job running at the same time as a ComfyUI / Forge Neo
workload on the 4080. CDI grants visibility, not exclusive VRAM.

Host paths are set in `.env` (`DATASETS_DIR`, `COMFY_MODELS_DIR`). Optional
`.env.local` overrides win for compose interpolation.

## Python development in Zed

The captioner, MCP adapter and local-model helper share one host development
environment, declared in `pyproject.toml` and pinned by `uv.lock`:

```sh
uv sync
basedpyright -p .
```

Open this service folder as a Python subproject in Zed and select
`/srv/compose/ai/toolkit/.venv/bin/python` in its toolchain selector if needed.
The project manifest lets Zed distinguish this environment from the other
Python services in the compose repository. `requirements.txt` files describe
dependencies for standalone/container use; Zed does not install them.
The host development venv does not contain Torch or Diffusers; those are
loaded dynamically by the local-model helper only inside the training container.
The MCP source directory is named `mcp_adapter` so it does not shadow the SDK's
`mcp` package. Container runtime dependencies remain isolated from the host venv.

## Paths

| Host | Container | Purpose |
| --- | --- | --- |
| `/srv/appdata/toolkit/datasets` | `/app/ai-toolkit/datasets` | Training image folders |
| `/srv/appdata/comfyui/models` | `/models` (read-only) | Diffusion, VAE, CLIP, LoRA files |
| `/srv/appdata/toolkit/output` | `/app/ai-toolkit/output` | Checkpoints and sample images |
| `/srv/appdata/toolkit/config` | `/app/ai-toolkit/config` | Saved job YAML |
| `/srv/appdata/toolkit/models` | `/app/ai-toolkit/models` (read-only) | Hardlink aliases for existing weights |
| `/srv/appdata/toolkit/cache/huggingface` | `/root/.cache/huggingface` | Tokenizer / model configuration cache |
| `/srv/appdata/toolkit/database` | `/app/ai-toolkit/state` | UI SQLite database and WAL/SHM files |

The upstream database path `/app/ai-toolkit/aitk_db.db` is a symlink to
`state/aitk_db.db`. Persisting its whole directory preserves SQLite's WAL
across container recreation. On an existing installation, stop Toolkit and
checkpoint/backup the database before migrating the old file into `database/`.

Krea 2 snofs raw (this host):

```
/models/diffusion_models/krea2-snofs-raw-v1.4-int8-convrot.safetensors
```

That file is an AI Toolkit merge quantized to convrot8 for ComfyUI. The
trainer loads it as `name_or_path`. It also has a hardlink alias:

```
/app/ai-toolkit/models/krea2-snofs-raw/raw.safetensors
```

Use either file path with architecture **Krea 2 (raw)** (`krea2`). If using
the directory `/app/ai-toolkit/models/krea2-snofs-raw`, set
`model.model_kwargs.checkpoint_filename: raw.safetensors`.

`MODELS_PATH=/models` makes the shared ComfyUI tree the toolkit model search
root. The Qwen3-VL-4B text encoder and Qwen-Image VAE are the files already
under `/models/clip` and `/models/vae`. `sitecustomize.py` registers these
local candidates and converts the ComfyUI VAE keys during loading. It is
mounted as `toolkit_local_models.py` and imported through
`toolkit-local-models.pth`, because Ubuntu's own `sitecustomize.py` takes
precedence over a same-named file in dist-packages.

This patch remains necessary for offline Krea training with the current
image: the native Qwen VAE/text-encoder classes register no local ComfyUI
candidates, and the local VAE also needs tensor-key conversion. Gemma4
captioning runs outside this container and does not use the patch. Recheck
these native loaders after updating the toolkit image before removing it.

`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` in `toolkit.env` block Hub
downloads. Tokenizer and configuration files must already be in the mounted
Hugging Face cache; the Qwen files are seeded on this host. Missing cache
entries fail offline. All shared weights are mounted read-only.

## Hardlinks

The ComfyUI and toolkit data directories currently share the same host
filesystem. These aliases share the original files' inodes and consume no
second copy of the weights:

| Toolkit models alias | ComfyUI models source |
| --- | --- |
| `krea2-snofs-raw/raw.safetensors` | `diffusion_models/krea2-snofs-raw-v1.4-int8-convrot.safetensors` |
| `vae/qwen-image-vae-bf16.safetensors` | `vae/qwen-image-vae-bf16.safetensors` |
| `clip/qwen3-vl-4b-fp8-scaled.safetensors` | `clip/qwen3-vl-4b-fp8-scaled.safetensors` |

Create links on the host, before exposing them as separate container mounts:

```sh
mkdir -p /srv/appdata/toolkit/models/krea2-snofs-raw
ln /srv/appdata/comfyui/models/diffusion_models/krea2-snofs-raw-v1.4-int8-convrot.safetensors \
   /srv/appdata/toolkit/models/krea2-snofs-raw/raw.safetensors
```

`ln` refuses to overwrite an existing alias. Hardlinks cannot cross
filesystems or link directories. Editing either link changes the same file;
replacing a source file by rename leaves the alias pointing at the old inode.
Refresh the alias after replacing a model. A matching filename does not
convert quantization or tensor keys into another format, nor populate a Hub
cache. The local loader handles those formats here; the VAE and text-encoder
aliases are optional because the patch loads directly from `/models`.

Verified on this host: the local Snofs transformer, Qwen VAE, Qwen3-VL text
encoder and tokenizer load with Hub access disabled. A 50-step LoRA test
completed on the 4080 at 512 resolution, rank 32, 50% transformer offloading,
with caption embeddings cached and checkpoints saved. VRAM was tight while
ComfyUI retained models on that GPU.

## First training job (Krea 2 character LoRA, 16 GB)

1. Open the UI and create a dataset from a folder under `/app/ai-toolkit/datasets`
   (for example `my_subject`). Captions are optional for a character LoRA.
2. New job → architecture **Krea 2 (K2)**.
3. Set **name or path** to either snofs file path above. Keep **quantize**, **quantize TE**,
   and **low VRAM** enabled.
4. Training: `linear` timesteps, flowmatch, batch 1, gradient accumulation 2,
   rank/alpha 32, LR `1e-4` to `2e-4`, 750–2500 steps. Cache latents and enable
   **Cache Text Embeddings**. Leave **Unload Text Encoder** off so captions
   are used; that option trains with only the trigger/blank prompt.
5. Sample on Raw during the run; judge the LoRA on Turbo (and on snofs) in ComfyUI.

Copy finished `.safetensors` from `${DATA_DIR}/output` into
`/srv/appdata/comfyui/models/loras` when you want them in ComfyUI.

## Auto-captioning on the RTX 3060

Use the reusable [Gemma4 captioning pipeline](captioning/README.md) to caption
the six dataset folders through your Rust llama.rs runner and ik_llama.cpp:

```sh
caption-datasets --json
```

The launcher lives at `/srv/appdata/toolkit/captioning/caption-datasets`;
`caption-datasets` on PATH is a symlink to it. It supplies the dataset root
and private runner path.
System instructions, model and compute settings live in the local profile
`/srv/compose/ai/toolkit/captioning/gemma4-captioning.yaml`. There is no pipeline TOML file; the
repository contains only a generic pipeline and example YAML. This profile
uses GPU 1 with CPU expert offloading and the local GGUF plus its vision
projector. It needs no Hugging Face download. The pipeline saves matching
`.txt` files beside the images, skips existing captions, and stops the model
server afterwards. Toolkit reads the saved captions when training.

The installed toolkit does not include a Gemma/GGUF captioner, so this runs
on the host rather than through the UI's Auto Caption dropdown.

### Optional Qwen UI captioning

Auto-caption jobs have their own GPU selector. Choose **GPU #1** (RTX 3060,
12 GB), captioner **Qwen3-VL**, and model **Qwen/Qwen3-VL-8B-Instruct**.
Enable **Low VRAM** and **8bit convrot** quantization, use **Max Resolution
512** and **Max New Tokens 128**, and leave **Compile Models**, **Thinking**,
and **Recaption** off for the first run. Recaption overwrites existing captions.

The captioner loads the full Transformers-format vision-language model; it
does not use the training text-encoder patch. Pre-download its weights,
tokenizer, processor and configuration into the mounted Hugging Face cache
before starting an offline job. The full 8B model download is about 17.55 GB;
runtime quantization is needed for the 12 GB GPU.

For a deliberate pre-download, temporarily override `HF_HUB_OFFLINE` and
`TRANSFORMERS_OFFLINE` only on the downloader process and pass the token read
from `/run/secrets/HF_TOKEN` to `huggingface_hub.snapshot_download`. Keep the
service's normal offline settings enabled. Use the repo ID in the UI so
Transformers resolves its downloaded snapshot from the persistent cache.

[AI services](../README.md) · [Repository configuration](../../README.md)
