# Official Comfy MCP

[Comfy-Org/comfy-mcp](https://github.com/Comfy-Org/comfy-mcp), with official
`comfy-cli`, runs as the CPU-only `ai-comfyui-mcp` sidecar. The endpoint remains
**http://127.0.0.1:9100/mcp**. It is restricted to host loopback and has no Traefik
route. The non-internal `proxy` network enables host port publishing and outbound
CLI requests; `genai` carries the connection to ComfyUI. Existing clients must reconnect and refresh their tool list: community
server tool names are replaced by the official ones.

Upstream's command serves stdio. Our small `http-server.py` entrypoint serves the
same official tools through the MCP SDK's Streamable HTTP transport. It removes
six process/install tools because Compose owns ComfyUI's lifecycle and image;
use `composectl` and the generation image's build process for those operations.

`COMFY_LOCAL_URL=http://127.0.0.1:8188` points every CLI operation at a local
`socat` proxy, which forwards to `comfyui:8188` on the `genai` network. The CLI
restricts local node discovery to loopback addresses, so the proxy is needed for
a separate sidecar. It carries both HTTP and WebSocket traffic, including
generation, validation, GPU statistics, and cleanup.
The sidecar has no GPU devices; use `system_stats` for the generator's actual
hardware, rather than the sidecar's `server_info.hardware` snapshot.

Models, inputs, workflows, and outputs share the generation service's mounts.
Custom nodes are mounted read-only. The lightweight Python image copies only
the core workspace from the generator's image, without its CUDA/Torch runtime.
Workspace paths link to `/data`, so model downloads reach the real model folder.
Official CLI state lives under `/srv/appdata/comfyui/mcp/official`; previous
community state is preserved separately in the same parent directory.

## Build and update

```bash
/srv/compose/ai/comfyui-mcp/update.py
```

The updater resolves the latest stable official GitHub release, verifies its
PyPI package and Git tag, builds `comfy-mcp:<version>` and `comfy-mcp:latest`, then
restarts only the MCP unit and waits for health. It uses the running generator's
local image for the core workspace snapshot. Rebuild the MCP after rebuilding
the generation image to refresh that snapshot; API operations always target the
live generator. CLI/SDK versions are pinned to the tested versions in Dockerfile.

```bash
/srv/compose/ai/comfyui-mcp/update.py --build-only
/srv/compose/ai/comfyui-mcp/update.py --version 0.10.0
composectl status ai-comfyui-mcp --json
docker inspect --format '{{.State.Health.Status}}' comfyui-mcp
```

The existing enabled unit and optional `ai-comfyui` startup dependency remain.
The image is locally built (`pull_policy: never`); `docker upgrade` and
`composectl update` do not rebuild it.

## Validation

`smoke-test.py` connects over HTTP and checks official node/model discovery,
workflow validation, one SDXL DisTorch generation, job status, output retrieval,
and memory cleanup on both GPUs. It refuses to run when the queue is busy.

```bash
docker exec comfyui-mcp python /app/smoke-test.py
```

Test artifacts are saved under
`/srv/appdata/comfyui/user/default/workflow-backups/official-mcp-sidecar-test`.
