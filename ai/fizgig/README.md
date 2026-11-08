# Fizgig

Compose project, service and container: `fizgig`. Source image project:
`/srv/project/github/fizgig-docker`, targeting `ghcr.io/delfianto/fizgig:latest`.
Compose contains deployment configuration only. Its image is fixed directly in
`compose.yaml` as `ghcr.io/delfianto/fizgig:latest`; there is no image environment
variable or local image override. The [source repository](https://github.com/delfianto/fizgig-docker)
builds and publishes the image through GitHub Actions.

```sh
composectl start ai-fizgig --json
composectl stop ai-fizgig --json
composectl update ai-fizgig --json
```

UI: `https://fizgig.${TRAEFIK_ACME_DOMAIN}` or host-local
`http://127.0.0.1:8082`. The login uses the central `fizgig_password` secret.
No new HF token is required for local-only operation.

## Shared models

`${DATA_DIR}/config/models.json` selects explicit bundles. ComfyUI's manifest and
weights are mounted read-only at `/catalog` and `/models`. The resolver translates
stable catalogue IDs to current filenames and sets Fizgig's component preferences.
It never copies, renames or downloads weights. Existing model metadata and
catalogue records remain owned by ComfyUI.

Initial selections:

| Bundle | Existing weights |
| --- | --- |
| `krea-lustify` | Krea 2 Lustify V10 RAW ConvRot, shared Qwen-Image VAE, Toolkit's retained FP8 Qwen3-VL-4B |
| `anima-anisee` | AniSee V2 Aesthetic BF16, shared Qwen-Image VAE and Qwen3 0.6B |
| `sdxl-base` | Complete SDXL Base V1.0 checkpoint with embedded components |

The shared INT8 Krea text encoder is incompatible with Fizgig's current loader;
Toolkit's FP8 file avoids downloading another copy. Transformer support does not
imply that every encoder/quantisation format works. Other model families and
expanded architectures need reviewed bindings in the image integration first.

```sh
docker exec fizgig python3 -m fizgig_local list
docker exec fizgig python3 -m fizgig_local validate
```

Change `active` in the host selection file and restart to switch bundles. One
bundle per family is allowed. Active model preferences are reapplied at startup;
other UI settings persist. Missing assets fail explicitly. No weights are fetched
when clicking Start or using a Python download helper in offline mode.

## Storage and lifecycle

| Host | Container | Access |
| --- | --- | --- |
| `${COMFY_MANIFEST_DIR}` | `/catalog` | Read-only |
| `${COMFY_MODELS_DIR}` | `/models` | Read-only |
| `${TOOLKIT_MODELS_DIR}` | `/toolkit-models` | Read-only |
| `${MODEL_CATALOG}` | `/etc/fizgig/models.json` | Read-only |
| `${DATASETS_DIR}` | `/datasets` | Read/write; existing Toolkit datasets |
| `${DATA_DIR}` | `/workspace` | Read/write; settings, cache, outputs |

Results live at `${DATA_DIR}/output_loras`, independently of ComfyUI's model tree.
Import/register selected finished LoRAs deliberately later. Captions/preparation
can modify shared datasets, as in Toolkit. Existing HF cache/model helper assets
are not assumed to be complete: missing optional helpers are reported instead of
downloaded.

Both GPUs are visible through CDI, following Toolkit. Visibility does not reserve
VRAM. `restart: "no"` leaves lifecycle to `compose@ai-fizgig.service`; boot enablement
is separate from creating this project. There are no service dependencies on
ComfyUI or Toolkit processes, only their existing data directories.

The custom image bakes source/dependencies and uses its own entrypoint. Restarts
do not update application code or install packages. Python workers default to
offline mode; incoming browser requests work, outbound helpers are disabled.
No SSH or separate file manager is exposed.
