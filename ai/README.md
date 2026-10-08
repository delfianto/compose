# AI services

Local model inference, chat interfaces, retrieval APIs, and image-generation
tools. Each row is an independent Compose project; projects can share models,
GPUs, and APIs without sharing their lifecycle.

| Project | Purpose | Integration |
| --- | --- | --- |
| [Bifrost](bifrost/) | Gateway for accessing model providers through a common API | Connects AI clients to configured providers; uses PostgreSQL and Valkey |
| [Ollama](ollama/) | Downloads and serves local language models | API on `genai`; exposes both GPUs |
| [Embedding](embedding/) | Text embedding and reranking for retrieval | TEI embedder, reranker, and proxy; GPU selected by `GPU_ID` |
| [Open WebUI](openwebui/) | Browser chat interface for local and remote models | Uses Bifrost, embeddings, and PostgreSQL; includes CPU task inference and Open Terminal containers |
| [Hollama](hollama/README.md) | Minimal browser client for local LLM APIs | Browser-side settings and conversations; configure an endpoint reachable from the browser |
| [Strata](strata/README.md) | Runs Qwen3.8-Flash-Next using GPU caches and CPU/RAM offload | Release-tagged Bake build; RTX 4080 + RTX 3060 layer split |
| [ComfyUI](comfyui/README.md) | Workflow-based image, video, and other generative media processing | Custom NVIDIA image; both GPUs visible; persistent models, workflows, and outputs |
| [ComfyUI MCP](comfyui-mcp/README.md) | Lets MCP clients interact with ComfyUI | Separate server and lifecycle; connects over `genai`, endpoint bound to localhost |
| [SmartGallery](comfyui-gallery/) | Browses ComfyUI outputs and their workflows | Shares output, input, and model directories with ComfyUI |
| [Forge Neo](forgeneo/README.md) | Stable Diffusion WebUI for image generation | Custom image; shares ComfyUI assets read-only; uses GPU 0 |
| [KoboldCpp](koboldcpp/) | GGUF inference with a browser interface and generation APIs | On-demand inference on GPU 0; models bind-mounted from storage |
| [Text Generation WebUI](textgen/) | Interactive LLM loading and generation with multiple backends | On-demand GPU 0 workload with persistent user data and cache |
| [RisuAI](risuai/) | Character-based chat and roleplaying client | Persistent saved content; Traefik web route; uses `compose.yml` |

## How the projects fit together

Open WebUI is the main consumer-facing chat project. It uses PostgreSQL,
Bifrost, and the embedding APIs, with Ollama as an optional model backend.
Bifrost uses PostgreSQL and Valkey. ComfyUI MCP connects to ComfyUI while
remaining independently updatable from the generation backend.

The `genai` network carries internal APIs where projects declare it. Browser
interfaces use Traefik on `proxy`; direct API ports remain configured for some
projects. Browser-side clients such as Hollama need a URL reachable by the
browser, not just a Docker container hostname.

## GPUs and model storage

This host has an RTX 4080 (GPU 0, 16 GB) and RTX 3060 (GPU 1, 12 GB).
Ollama, ComfyUI, and Strata expose both. Forge Neo, KoboldCpp, and Text Generation
WebUI use GPU 0; embedding uses its configured `GPU_ID`. Open WebUI's task-model
container is CPU-only. CDI grants access without reserving exclusive VRAM.
Check existing allocations before starting another large model.

Keep model files and caches on the paths selected by each project's `.env`.
Sharing directories avoids duplicate assets, but write access varies: Forge Neo
reads shared ComfyUI data, while ComfyUI and SmartGallery can write their outputs.
Large-model startup may need substantial system RAM as well as VRAM.

Custom images require a build, not just an image pull. Follow the project README
for ComfyUI, ComfyUI MCP, Forge Neo, or Strata before using an update command.
Strata supplies a standalone wrapper for configuration checks and Bake builds;
compose-utils also loads its `.env.local` storage override automatically.

[Repository configuration and lifecycle](../README.md) · [Dependency mirror](../service.toml)
