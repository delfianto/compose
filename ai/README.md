# AI services

Local model inference, chat interfaces, retrieval APIs, and image-generation
tools. Each row is an independent Compose project; projects can share models,
GPUs, and APIs without sharing their lifecycle.

| Project | Purpose | Integration |
| --- | --- | --- |
| [AI Toolkit](toolkit/README.md) | Ostris LoRA trainer for Krea 2, Qwen Image 2.1, and other diffusion bases | GPU 0 for training, GPU 1 for captioning; UI at `toolkit.${TRAEFIK_ACME_DOMAIN}`; datasets under `/srv/appdata/toolkit/datasets`; ComfyUI models at `/models` |
| [Bifrost](bifrost/) | Gateway for accessing model providers through a common API | Connects AI clients to configured providers; uses PostgreSQL (VectorChord) and Valkey |
| [ComfyUI](comfyui/README.md) | Workflow-based image, video, and generative media engine (`comfyui-app`) + official API proxy (`comfyui-proxy`) | Images from GHCR (`comfyui-docker`); both GPUs visible; persistent models, workflows, and outputs; local API proxy |
| [Embedding](embedding/) | Text embedding and reranking for retrieval-augmented generation | TEI embedder, reranker, and proxy; GPU selected by `GPU_ID` |
| [Forge Neo](forgeneo/README.md) | Stable Diffusion WebUI for image generation | Images from GHCR (`sd-webui-forge-docker`); shares ComfyUI assets read-only; uses GPU 0 |
| [Hollama](hollama/README.md) | Minimal browser client for local LLM APIs | Browser-side settings and conversations; configure an endpoint reachable from the browser |
| [KoboldCpp](koboldcpp/) | GGUF inference with a browser interface and generation APIs | On-demand inference on GPU 0; models bind-mounted from storage |
| [Ollama](ollama/) | Downloads and serves local language models | API on `genai`; exposes both GPUs |
| [Open WebUI](openwebui/) | Browser chat interface for local and remote models | Uses Bifrost, embeddings, and PostgreSQL; includes CPU task inference and Open Terminal containers |
| [RisuAI](risuai/) | Character-based chat and roleplaying client | Persistent saved content; Traefik web route; uses `compose.yml` |
| [SmartGallery](comfyui-gallery/) | Browses ComfyUI outputs and their workflows | Shares output, input, and model directories with ComfyUI |
| [Strata](strata/README.md) | Runs Qwen3.8-Flash-Next using GPU caches and CPU/RAM offload | Release-tagged Bake build; RTX 4080 + RTX 3060 layer split |
| [Text Generation WebUI](textgen/) | Interactive LLM loading and generation with multiple backends | On-demand GPU 0 workload with persistent user data and cache |

## How the projects fit together

Open WebUI is the main consumer-facing chat project. It uses PostgreSQL (VectorChord),
Bifrost, and the embedding APIs, with Ollama as an optional model backend.
Bifrost uses PostgreSQL and Valkey. ComfyUI includes an official local API proxy
sidecar (`comfyui-proxy`) for SDK integrations.

The `genai` network carries internal APIs where projects declare it. Browser
interfaces use Traefik on `proxy`; direct API ports remain configured for some
projects. Browser-side clients such as Hollama need a URL reachable by the
browser, not just a Docker container hostname.

## GPUs and model storage

This host has an RTX 4080 (GPU 0, 16 GB) and RTX 3060 (GPU 1, 12 GB).
Ollama, ComfyUI, and Strata expose both. Forge Neo, AI Toolkit, KoboldCpp, and Text Generation
WebUI use GPU 0; embedding uses its configured `GPU_ID` (GPU 1). Open WebUI's task-model
container is CPU-only. CDI grants access without reserving exclusive VRAM.
Check existing allocations before starting another large model.

Keep model files and caches on the paths selected by each project's `.env`.
Sharing directories avoids duplicate assets, but write access varies: Forge Neo
reads shared ComfyUI data, while ComfyUI and SmartGallery can write their outputs.
Large-model startup may need substantial system RAM as well as VRAM.

ComfyUI and Forge Neo container images are built externally in dedicated GitHub
repositories ([`comfyui-docker`](https://github.com/delfianto/comfyui-docker) and
[`sd-webui-forge-docker`](https://github.com/delfianto/sd-webui-forge-docker)) and
published to GHCR; they update via standard `composectl update`. Strata supplies a
standalone wrapper for configuration checks and Bake builds; compose-utils also
loads its `.env.local` storage override automatically.

[Repository configuration and lifecycle](../README.md) · [Dependency mirror](../service.toml)
