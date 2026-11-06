# AI Toolkit

Ostris AI Toolkit (`ostris/aitoolkit`) for LoRA training on consumer GPUs.
The container is on-demand and exposes GPU 0 (RTX 4080) and GPU 1 (RTX 3060).
Use GPU 0 for training and GPU 1 for captioning. GPU 1
is also shared by other homelab services; check available VRAM before captioning.
The UI is at
`https://ostris.${TRAEFIK_ACME_DOMAIN}` and is gated by `AI_TOOLKIT_AUTH`.
The [MCP adapter](mcp_adapter/README.md) runs inside the same container at
`https://ostris-mcp.${TRAEFIK_ACME_DOMAIN}/mcp`, using the same bearer token.
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
`.venv/bin/python` in its toolchain selector if needed.
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
| `${DATA_DIR}/datasets` | `/app/ai-toolkit/datasets` | Training image folders |
| `${COMFY_MODELS_DIR}` | `/models` (read-only) | Shared ComfyUI diffusion, VAE, CLIP, LoRA files |
| `${DATA_DIR}/output` | `/app/ai-toolkit/output` | Checkpoints and sample images |
| `${DATA_DIR}/config` | `/app/ai-toolkit/config` | Saved job YAML |
| `${DATA_DIR}/models` | `/app/ai-toolkit/models` (read-only) | Legacy paths used by previous jobs |
| `${DATA_DIR}/cache/huggingface` | `/root/.cache/huggingface` | Tokenizer / model configuration cache |
| `${DATA_DIR}/database` | `/app/ai-toolkit/state` | UI SQLite database and WAL/SHM files |

The upstream database path `/app/ai-toolkit/aitk_db.db` is a symlink to
`state/aitk_db.db`. Persisting its whole directory preserves SQLite's WAL
across container recreation. On an existing installation, stop Toolkit and
checkpoint/backup the database before migrating the old file into `database/`.

Krea 2 Lustify v10 RAW (this host, INT8 ConvRot conversion):

```
/models/diffusion_models/krea2-lustify-v10-raw.safetensors
```

Use this exact container path as `model.name_or_path` with architecture
**Krea 2 (raw)** (`krea2`). The complete shared model directory is mounted
read-only at `/models`; no symlink, hardlink, renamed checkpoint or duplicate
weights are needed. The bind mount refuses a missing host source. Other RAW
finetunes can use their own direct `/models/diffusion_models/<file>` path.

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

Some RAW repacks include auxiliary `last.down.*` and `last.up.*` tensors.
The patch removes only those keys before quantized loading because the
[official LastLayer](https://github.com/krea-ai/krea-2/blob/main/mmdit.py) and
ComfyUI do not use them. All other upstream weight/shape checks remain strict;
checkpoint files are unchanged. Re-evaluate this compatibility hook on upgrades.
The hook also decodes the tiny text-layer projector from plain INT8 to floating
point in memory when a repack quantizes it: its 12 inputs do not meet the CUDA
INT8 kernel alignment requirement. Main transformer layers stay quantized.

Lustify v10 RAW stores its quantization configuration in safetensors header
`_quantization_metadata` version 1.0 instead of per-layer `.comfy_quant`
tensors. The Krea file-reader hook translates those entries into Toolkit's
in-memory markers before loading, preserving the original INT8 weights,
scales and ConvRot group sizes. The source file is unchanged. Missing scales,
unsupported schemas and conflicting markers fail explicitly. Recheck upstream
header support after image upgrades before removing this compatibility hook.

`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` in `toolkit.env` block Hub
downloads. Tokenizer and configuration files must already be in the mounted
Hugging Face cache; the Qwen files are seeded on this host. Missing cache
entries fail offline. All shared weights are mounted read-only.

## Legacy paths and verification

The `/app/ai-toolkit/models` mount remains for previous saved jobs. New jobs
use `/models` directly, including the VAE and text encoder. No new aliases
should be created. Replacing a checkpoint under its normal ComfyUI filename
is visible on the next load through the shared directory mount.

The UI draft `jenada_krea2_lustify_raw_v1_2000` uses this direct Lustify path
and preserves the portrait/context datasets and settings from
`jenada_krea2_official_raw_v3_2000`. Its exported job is saved under
`${DATA_DIR}/config/jenada_krea2_lustify_raw_v1_2000.json`. It has not been
queued for training.

Lustify v10 RAW passed a strict transformer load on CPU using the live
container's loader: all parameters materialized and all 256 INT8 ConvRot
layers retained rotation group size 256. This verifies checkpoint loading,
not training quality or GPU memory requirements.

Verified on this host: the local Snofs transformer, Qwen VAE, Qwen3-VL text
encoder and tokenizer load with Hub access disabled. A 50-step LoRA test
completed on the 4080 at 512 resolution, rank 32, 50% transformer offloading,
with caption embeddings cached and checkpoints saved. VRAM was tight while
ComfyUI retained models on that GPU.

## First training job (Krea 2 character LoRA, 16 GB)

1. Open the UI and create a dataset from a folder under `/app/ai-toolkit/datasets`
   (for example `my_subject`). Captions are optional for a character LoRA.
2. New job → architecture **Krea 2 (K2)**.
3. Set **name or path** to `/models/diffusion_models/krea2-lustify-v10-raw.safetensors`.
   Keep **quantize**, **quantize TE**,
   and **low VRAM** enabled.
4. Training: `linear` timesteps, flowmatch, batch 1, gradient accumulation 2,
   rank/alpha 32, LR `1e-4` to `2e-4`, 750–2500 steps. Cache latents and enable
   **Cache Text Embeddings**. Leave **Unload Text Encoder** off so captions
   are used; that option trains with only the trigger/blank prompt.
5. Sample on Raw during the run; evaluate the LoRA on your chosen compatible
   Krea base in ComfyUI.

Copy finished `.safetensors` from `${DATA_DIR}/output` into
`${COMFY_MODELS_DIR}/loras` when you want them in ComfyUI.

## Preparing a larger character dataset

The [dataset preparation pipeline](dataset_prep/README.md) audits source albums,
filters small or soft faces, balances album coverage, and exports native portrait
crops plus wider context images. Keep its audit, review exclusions and output
in the runtime data directory. Visually review selections and generate fresh
captions before adding the exported folders to a training job.

## Auto-captioning on the RTX 3060

Use the reusable [Gemma4 captioning pipeline](captioning/README.md) to caption
the six dataset folders through your Rust llama.rs runner and ik_llama.cpp:

```sh
caption-datasets --json
```

The launcher lives at `${DATA_DIR}/captioning/caption-datasets`;
`caption-datasets` on PATH is a symlink to it. It supplies the dataset root
and private runner path.
System instructions, model and compute settings live in the local profile
`captioning/gemma4-captioning.yaml`. There is no pipeline TOML file; the
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
