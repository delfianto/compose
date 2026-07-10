---
name: service-lifecycle
description: Start, stop, restart, update, enable/disable, and check status of a compose service in this repo. Prefers composectl (systemd unit) over the direct compose persona, and uses --json for machine-parseable output. Also covers docker upgrade, the separate host-wide CLI plugin that refreshes every local Docker image and prunes dangling ones afterward. Use when starting/stopping a service, checking why something is down, deploying an image update, bulk-updating all images on the machine, enabling boot-persistence, or inspecting live container health/ports.
---

Control compose services the way this repo expects: through the systemd unit (`composectl`), not by shelling into `docker compose` directly. Per `AGENTS.md`, every service declares `restart: "no"` — systemd (`compose@.service` + `composectl`) owns restart-on-failure and lifecycle, Docker's own restart policy is intentionally disabled. Bypassing systemd doesn't just skip a convention, it produces a container with no supervisor.

## Command matrix

| Want to... | Run | Notes |
|---|---|---|
| Start on boot + now | `composectl enable <svc>` then `composectl start <svc>` | `enable` also accepts `--deps <file>` to apply dependencies first |
| Start now (session only) | `composectl start <svc>` | |
| Stop | `composectl stop <svc>` | |
| Restart | `composectl restart <svc>` | |
| Pull + restart (one service) | `composectl update <svc>` | pull happens in the project dir, then `systemctl restart` |
| Pull only, no restart (one service) | `composectl pull <svc>` (or `compose pull <svc>`) | same underlying `docker compose pull` |
| Refresh **every** local image on the machine | `docker upgrade` | host-wide, not scoped to a compose project — see below |
| Check systemd state | `composectl status <svc>` | `ActiveState`/`SubState`/`LoadState`/`UnitFileState`, not container health |
| Check container health/ports | `compose ps` | direct-persona only; see gotcha below |
| Fix systemd/container drift | `composectl sync <svc>` | run after any `compose`/bare `docker compose` invocation |
| Boot persistence on/off | `composectl enable <svc>` / `composectl disable <svc>` | |

Always add `--json` when the output will be parsed rather than read.

## Service name resolution

Accepts, and normalizes to `compose@<flat-name>.service`:

| Input | Resolves to | Notes |
|---|---|---|
| `ai/ollama` | `compose@ai-ollama.service` | slash form |
| `ai-ollama` | `compose@ai-ollama.service` | dash form, if `ai/ollama` dir exists |
| `ollama` | `compose@ollama.service` | bare name, if a top-level `ollama` dir exists |
| `compose@ai-ollama.service` | itself | already-qualified, idempotent |
| `docker.service` | itself | anything with `.service`/`.target`/`.socket`/`@` and no slash passes through unmodified |

If no service is given, it's auto-detected from `$PWD` (must be a subdirectory of `COMPOSE_BASE` containing a compose file; nested dirs become dash-joined names). Auto-detection only fires when the arg list is empty — you can't mix explicit names with auto-detect in one call.

## JSON shapes

`start` / `restart` (per-service `state` is the post-action `ActiveState`):
```json
{"command": "start", "results": [
  {"service": "db-postgres", "unit": "compose@db-postgres.service", "state": "active"}
]}
```

`stop` / `enable` / `disable` (fire-and-forget, no state re-check):
```json
{"command": "stop", "results": [
  {"service": "db-postgres", "unit": "compose@db-postgres.service", "status": "stopped"}
]}
```

`status`:
```json
{"command": "status", "results": [
  {"service": "db-postgres", "unit": "compose@db-postgres.service",
   "active_state": "inactive", "sub_state": "dead",
   "load_state": "loaded", "unit_file_state": "enabled",
   "description": "Compose Service for db-postgres"}
]}
```

`sync` (`action` is one of `none` / `adopted` / `reset`):
```json
{"command": "sync", "results": [
  {"service": "db-postgres", "unit": "compose@db-postgres.service",
   "systemd_active": false, "containers_running": true, "action": "adopted"}
]}
```

`update`:
```json
{"command": "update", "results": [
  {"service": "db-postgres", "pulled": "ok", "restarted": true}
]}
```

`compose ps` (container-level, no systemd knowledge — see gotcha):
```json
{"command": "ps", "results": [
  {"name": "traefik", "id": "d868d4fdec73", "image": "traefik:v3.6",
   "state": "running", "health": "healthy", "uptime": "1d 10:06",
   "ports": ["0.0.0.0:80->80/tcp", "0.0.0.0:443->443/tcp"]}
]}
```

## Gotcha: `compose ps [services]` ignores the filter

`compose ps <name>` accepts a services argument but the current binary drops it (`run_ps(ctx, _services)` in `src/commands/ps.rs` never reads `_services`) — it always lists every container on the host regardless of what you pass. Don't rely on it to scope output; instead pipe `--json` through `jq` and filter client-side, e.g.:

```bash
compose ps --json | jq '.results[] | select(.name == "postgres")'
```

`composectl status <svc>` *does* filter correctly (it operates per-unit), so prefer it when you only care about one service's state.

## `docker upgrade` vs. `composectl update`/`pull`

`docker upgrade` is a separate CLI plugin (`~/.config/docker/cli-plugins/docker-upgrade`, from the `docker-conf` repo, documented in `AGENTS.md`'s Docker CLI Plugins table) — it is **not** part of the `compose`/`composectl` binary and has no `--json` mode. Where `composectl update <svc>` / `compose pull <svc>` are scoped to the images one compose project's `compose.yaml` references, `docker upgrade` walks **every local image on the host**, regardless of which project (or none) it belongs to: it checks all of them for updates in parallel via registry HEAD requests, pulls only the ones that changed, and then prunes the dangling images those pulls just orphaned (`docker image prune -f`, on by default — pass `--no-prune` to skip it). `--dry-run` previews with no pulls and no prune; `--filter` narrows by substring.

**It does not restart anything.** `docker upgrade` only refreshes the local image cache — a running container keeps using the image digest it was started with even after a newer one has been pulled. After running it, any service whose image actually changed still needs `composectl restart <svc>` (or `composectl update <svc>` next time, which pulls-then-restarts in one step) to pick up the new image. Use `docker upgrade` for bulk "what's stale across the whole machine" sweeps; use `composectl update <svc>` when you know exactly which service you want refreshed-and-restarted right now.

## When you must use the direct `compose` persona

`compose up/down/restart` talk straight to `docker compose`, bypassing systemd entirely — useful for quick iteration on a compose file before it's wired into a unit, or when systemd itself is the thing being debugged. After any such direct invocation, run `composectl sync <svc>` so systemd's tracked state matches reality again; `composectl start`/`stop` are no-ops when systemd already believes it's in the target state, even if that belief is stale.

## Examples (real services in this repo)

```bash
composectl status db-postgres infra-traefik --json
composectl start ai-ollama
composectl update media-immich --json
composectl sync panel-homepage   # after a manual `docker compose up` in panel/homepage
```
