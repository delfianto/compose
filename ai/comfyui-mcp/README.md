# ComfyUI MCP

Standalone MCP project with its own systemd unit, `ai-comfyui-mcp`. Updating this
project does not restart ComfyUI. The server connects to `http://comfyui:8188`
over the external `genai` network and keeps its state in
`/srv/appdata/comfyui/mcp`. Its HTTP endpoint remains
`http://127.0.0.1:9100/mcp`, with no LAN or Traefik exposure.

## Update

From anywhere:

```sh
/srv/compose/ai/comfyui-mcp/update.py
```

The updater selects GitHub's latest stable release, verifies the matching npm
package exists, resolves the Git tag to a revision, and builds the published
package using the local Dockerfile. This avoids depending on an upstream
Dockerfile, which newer releases no longer provide. Both the version and Git
revision are recorded in image labels. It tags the image with the release
version and `comfyui-mcp:latest`, then restarts only `ai-comfyui-mcp` and waits for
container health. Failed lookups or builds leave the running container alone.

To build without restarting, or return to a previous release:

```sh
/srv/compose/ai/comfyui-mcp/update.py --build-only
/srv/compose/ai/comfyui-mcp/update.py --version 0.49.8
```

The updater needs Python 3, Git, Docker with BuildKit, and `composectl`, plus
network access to GitHub, npm, and Docker Hub. GitHub's unauthenticated API
rate limit applies. Run it as the user owning the rootless Docker daemon.

## First installation

```sh
/srv/compose/ai/comfyui-mcp/update.py --build-only
composectl deps add ai-comfyui-mcp ai-comfyui
composectl enable ai-comfyui-mcp
composectl start ai-comfyui-mcp
```

The soft systemd dependency starts ComfyUI first without coupling MCP's
lifecycle to ComfyUI restarts. Startup ordering does not guarantee ComfyUI is
healthy yet; MCP can reconnect as ComfyUI becomes available.

The Compose image has `pull_policy: never` because it is built locally.
`docker upgrade` and `composectl update` do not rebuild this image; use the
updater. Publishing images to a registry would be needed for pull-based updates.

Check status with:

```sh
composectl status ai-comfyui-mcp --json
docker inspect --format '{{.State.Health.Status}}' comfyui-mcp
```
