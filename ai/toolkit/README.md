# AI Toolkit

Ostris AI Toolkit for LoRA training, deployed from
`ghcr.io/delfianto/ai-toolkit:latest`. The image source, model resolver, MCP adapter,
checkpoint compatibility code, captioning tools and tests live in
[`delfianto/ai-toolkit-docker`](https://github.com/delfianto/ai-toolkit-docker).
This directory contains deployment configuration only.

```sh
composectl start ai-toolkit --json
composectl stop ai-toolkit --json
composectl update ai-toolkit --json
```

The UI is at `https://ostris.${TRAEFIK_ACME_DOMAIN}`. MCP is at
`https://ostris-mcp.${TRAEFIK_ACME_DOMAIN}/mcp`; both use the existing
`aitoolkit_auth` secret. Source code is baked into the image, with no local build
context or application-code bind mounts.

## Models and persistent data

`MODEL_CATALOG` in `.env` points to the host JSON catalog, mounted read-only at
`/etc/ai-toolkit/models.json`. Register actual paths and component identities in that
catalog, then select `catalog:<bundle-id>` as the job model path. Keep the UI's
architecture consistent with the bundle. SDXL, FLUX and Z-Image examples and the
[catalog guide](https://github.com/delfianto/ai-toolkit-docker/blob/main/docs/models.md)
are maintained with the image source.

```sh
docker exec ai-toolkit python -m aitoolkit_models list
docker exec ai-toolkit python -m aitoolkit_models validate krea-lustify
```

The deployment catalog initially registers `krea-lustify`, including its existing
FP8 Qwen3-VL encoder. It uses the original asset in the retained model directory;
files need not match upstream's naming conventions. Existing saved jobs still
work through the catalog's shared component bindings. Select `catalog:krea-lustify`
for preflight of the complete declared bundle before loading its transformer.

| Host setting/path | Container path | Purpose |
| --- | --- | --- |
| `COMFY_MODELS_DIR` | `/models` (read-only) | Shared model library |
| `${DATA_DIR}/models` | `/app/ai-toolkit/models` (read-only) | Existing assets and saved job paths |
| `DATASETS_DIR` | `/app/ai-toolkit/datasets` | Training datasets |
| `${DATA_DIR}/config` | `/app/ai-toolkit/config` | Saved jobs and host catalog data |
| `${DATA_DIR}/output` | `/app/ai-toolkit/output` | Training outputs |
| `${DATA_DIR}/database` | `/app/ai-toolkit/state` | SQLite DB, WAL/SHM and generated model views |
| `${DATA_DIR}/cache/huggingface` | `/root/.cache/huggingface` | Existing model configs/tokenizers |

The Compose directory and service use `toolkit`, with systemd unit
`compose@ai-toolkit.service`. The container, image and Traefik labels use
`ai-toolkit`. Existing appdata paths deliberately remain unchanged to preserve jobs,
datasets and history. `AI_TOOLKIT_OFFLINE=1` prevents automatic downloads and writes
into shared weights. Add missing assets explicitly; making `/models` writable is
not required.

Both GPUs remain visible. Choose GPU 0 for training or GPU 1 for captioning in the
UI; visibility is not exclusive GPU ownership. Secrets remain in the central
secret store and are exported by the repository's shared secret shim.

Host development clone: `/srv/project/github/ai-toolkit-docker`. Captioning and dataset
utilities now live under its `tools/` directory; the existing `caption-datasets`
launcher points there.
