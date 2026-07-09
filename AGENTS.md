# AGENTS.md

## Project Overview

Docker Compose orchestration for a self-hosted homelab. Modular compose files manage databases, generative AI, media streaming, infrastructure, and dashboard/management tooling. Deployed on Linux with systemd, rootless Docker, dual NVIDIA GPUs, and Traefik reverse proxy.

**Repository**: `github.com/delfianto/compose`
**License**: MIT

## Directory Layout

```
.
├── ai/               # AI/ML services (bifrost, ollama, embedding, openwebui, librechat, comfyui, forge, risuai)
├── db/               # Databases (postgres, mariadb, mongo, valkey, qdrant)
├── infra/            # Infrastructure & Reverse proxy (forgejo, infisical, traefik)
├── media/            # Media services (immich, photoprism, plex, stash)
├── panel/            # Dashboard & management (homepage, portainer, tugtainer)
├── lib/              # Shared scripts bind-mounted into containers (e.g. secret-env.sh)
├── service.toml      # Service dependency graph
└── AGENTS.md
```

Each service lives in its own subdirectory with a `compose.yaml` and env files. Nested directories use the pattern `category/service` (e.g., `ai/ollama`).

## Key Conventions

### Naming

- **Directories**: lowercase, no hyphens within a service name (e.g., `openwebui`, `librechat`)
- **Compose files**: always `compose.yaml` (not `docker-compose.yml`), except `ai/risuai` which uses `compose.yml`
- **Service names in compose**: lowercase simple names matching the directory (e.g., `ollama`, `postgres`)
- **Container names**: set explicitly via `container_name:`
- **Systemd service names**: `category-service` with hyphens mapping to path separators (e.g., `ai-ollama` -> `ai/ollama`)
- **Subdomains**: `{shortname}.${TRAEFIK_ACME_DOMAIN}` (e.g., `webui.example.com`)

### Environment Files

Each service directory follows this pattern:

| File                  | Purpose                                                     | Committed to git |
| --------------------- | ----------------------------------------------------------- | ---------------- |
| `.env`                | Shell interpolation vars (image tags, paths, UIDs, GPU IDs) | Yes              |
| `.env.local`          | Local overrides for `.env`                                  | No (gitignored)  |
| `{service}.env`       | Container runtime env vars (app config, credentials)        | Yes              |
| `{service}.env.local` | Secrets and local-only container vars                       | No (gitignored)  |

**Precedence** (last wins), verified empirically (see below) rather than assumed:
- For **interpolation** (`${VAR}` in `compose.yaml` itself): `~/.config/docker/compose.env` < `.env` — that's it. `.env.local` is **not** loaded for interpolation on this host (`COMPOSE_ENV_FILES` only lists `compose.env,.env`); don't rely on it to override paths/domains that a compose file interpolates. If a real value must differ from what's tracked in `.env` and can't be committed, either gitignore that service's `.env` outright and keep a `.env.sample` template (see `ai/librechat`), or keep the value out of interpolation entirely (put it only in `{service}.env`/`{service}.env.local`, which the container reads as runtime vars, not Compose interpolation).
- For **container runtime env** (what the process inside actually sees): `{service}.env` < `{service}.env.local` < `environment:` section — these are loaded via `env_file:`/`environment:` at container-start time, a completely different mechanism from `.env` interpolation, and `.local` here does take effect.

**Machine-wide interpolation layer**: `COMPOSE_ENV_FILES` (exported by the login shell and by the `compose@.service` systemd template, e.g. `~/.config/docker/compose.env,.env`) makes Compose load `~/.config/docker/compose.env` before each project's own `.env`, and the project's `.env` wins on conflicts. That file holds host-wide interpolation vars: `COMPOSE_BASE`, `COMPOSE_DATA`, `TRAEFIK_ACME_DOMAIN/EMAIL/SERVER`, `DOCKER_HOST`, `DOCKER_SOCK`. Reference `${COMPOSE_BASE}` (e.g. for `lib/secret-env.sh` mounts) instead of hardcoding relative `../../` paths, since it's already exported everywhere.

**Rules**:

- Never hardcode secrets in compose files or committed env files
- All passwords/tokens go in `.local` files or the central secret store (below)
- Document required variables with comments in base env files

### Secrets & Privilege Escalation

- **Central Secret Store**: All secrets are stored in `/srv/appdata/secret/` (`SECRET_DIR`), owned by host `geist` (uid 1000), directory `0700` / files `0600`.
- **Reference Pattern**: Secrets are mounted using Docker's secrets mechanism:
    ```yaml
    secrets:
        my_secret:
            file: ${SECRET_DIR}/my_secret
    ```
- **Shared vs Service-specific**: Shared credentials (e.g., `openai_api_key`) use bare names, while service-specific secrets (e.g., `librechat_meili_master_key`) are prefixed.
- **The `/secret-env.sh` Entrypoint Shim** (`lib/secret-env.sh`):
    - Used for images that do not support reading secrets from `/run/secrets/{name}` natively.
    - Mount `${COMPOSE_BASE}/lib/secret-env.sh` at `/secret-env.sh:ro` and set `entrypoint: ["/secret-env.sh"]`.
    - Exports every mounted secret as an uppercased env var (or verbatim if the secret name already has an uppercase letter — use `target:` in the compose `secrets:` block to control the exact var name), then expands `$VAR` references inside other env vars, then execs the original command.
    - `#!/bin/sh`, deliberately POSIX-only (`[ ]`, not `[[ ]]`) — it's bind-mounted into a mix of BusyBox `ash` (alpine-based images: bifrost, forgejo, librechat, meilisearch) and `dash` (debian-based: mongo, openwebui, photoprism) containers, none of which have bash.
- **Privilege Dropping**:
    - Because secret files are `0600` on the host, only container root (host `geist` uid 1000) can read them, so images needing `user: "0:0"` + the shim to read them.
    - The shim reads `/proc/self/uid_map` to detect whether container uid 0 is _real_ host root. Under rootless Docker (this host), uid 0 maps to an unprivileged host uid, so dropping to `DROP_USER` buys no extra isolation and is **skipped by default** — the app just keeps running as container root.
    - Set `FORCE_DROP_USER=1` alongside `DROP_USER=<user>` when the app itself refuses to run as uid 0 for its own reasons, independent of host security — e.g. `codeberg.org/forgejo/forgejo:14-rootless` hard-exits with "Forgejo is not supposed to be run as root". Check the app's actual behavior (don't assume from the image tag) before deciding this is needed.
    - For containers that drop privileges via their **own** official entrypoint (e.g. the stock `mongo` image's `docker-entrypoint.sh`, which does its own root -> `mongodb` handoff via `gosu` once it sees the resolved env var), don't set `DROP_USER` at all — the shim just needs to run once as root to export the secret, then exec into the image's normal entrypoint chain.
- **Rootless User Namespace Mapping**:
    - Container root maps to host `geist` (uid 1000). Container uid N>0 maps to host subuid `100000+N-1` (verify per-host: `cat /proc/self/uid_map` from inside any container).
    - For directories a dropped-privilege container needs to write to, chown the host directory to the container's target uid from a disposable root container:
      `docker run --rm -v /srv/appdata/service:/data alpine chown -R 1000:1000 /data/logs`
- `.gitignore` blocks: `*.local`, `*.secret`, `*.key`, `*.pem`, `*.crt`, `certs/`, `data/`, `global.env`

### Networks

Five isolated Docker bridge networks, defined in `~/.config/docker/networks.toml` and managed via the `docker net` CLI plugin (`docker net -i <file>` to bootstrap, `docker net -v [name]` to inspect):

| Network    | Subnet        | Internal | Purpose                  |
| ---------- | ------------- | -------- | ------------------------ |
| `proxy`    | 172.20.0.0/24 | No       | Traefik-exposed services |
| `metrics`  | 172.21.0.0/24 | Yes      | Monitoring (future)      |
| `database` | 172.22.0.0/24 | Yes      | Database services        |
| `genai`    | 172.23.0.0/24 | Yes      | AI/ML inter-service      |
| `auth`     | 172.24.0.0/24 | Yes      | Authentication (future)  |

All networks are declared `external: true` in compose files. Services connect only to networks they need. A few services (e.g. `mariadb`, `mongo`) also carry Compose's automatic per-project `default` network alongside `database` — incidental, not part of the intentional 5-network design.

### GPU Assignment

Dual NVIDIA GPU setup using Compose's CDI device syntax (`devices: - nvidia.com/gpu=<id>`) — not the older `deploy.resources.reservations.devices` block:

- `ai/ollama` and `ai/comfyui` hardcode both `nvidia.com/gpu=0` and `=1` directly (visibility into both GPUs, not a var)
- `ai/forge` hardcodes `nvidia.com/gpu=0` only
- Everything else on a GPU reads `nvidia.com/gpu=${GPU_ID}` from its own `.env`: `ai/embedding`, `db/qdrant`, `media/immich`, `media/photoprism`, `media/plex`, `media/stash` — all currently pinned to `GPU_ID=1`
- OpenWebUI's sidecar is **CPU-only** (Zen5-optimized llama.cpp, see Custom Builds) — it does not reserve a GPU device
- CDI device declarations only grant visibility, not an exclusive lock — VRAM budgeting across services sharing a GPU is a manual convention, not enforced by Docker

### Data Paths

- `/srv/appdata/{service}` (`DATA_DIR`): Persistent service data
- `/mnt/{media_type}`: External media mounts (Plex, Stash, PhotoPrism)
- `PROJ_DIR`: only used by `ai/librechat` today (bind-mounts its own `.env` into the container), not a repo-wide convention
- Bind mounts use `:ro` where write access is unnecessary

### Traefik Labels

Label format is a list of `"key=value"` strings, not a YAML map:

```yaml
labels:
    - "traefik.enable=true"
    - "traefik.http.routers.{name}.rule=Host(`{subdomain}.${TRAEFIK_ACME_DOMAIN}`)"
    - "traefik.http.routers.{name}.entrypoints=websecure"
    - "traefik.http.routers.{name}.tls.certresolver=cloudflare"
    - "traefik.http.services.{name}.loadbalancer.server.port=${PORT}"
    - "homepage.group=Category"
    - "homepage.name=Display Name"
    - "homepage.icon=icon.svg"
    - "homepage.href=https://{subdomain}.${TRAEFIK_ACME_DOMAIN}"
```

### Homepage Dashboard Labels

Services include `homepage.*` labels for auto-discovery by the Homepage dashboard service.

## Service Dependencies

Defined in `service.toml` and mirrored via `composectl deps`:

```
ai-bifrost       -> db-postgres
ai-librechat     -> db-postgres, ai-bifrost, ai-embedding, ai-ollama
ai-openwebui     -> db-postgres, ai-bifrost, ai-embedding, ai-ollama
infra-forgejo    -> db-postgres
infra-infisical  -> db-postgres, db-valkey
media-immich     -> db-postgres, db-valkey
```

**Startup order**: databases -> infrastructure -> AI foundations -> AI consumers -> media -> panel

## Tooling

### `compose` / `composectl` (`~/.local/bin/`)

Same Rust binary — `compose` is a symlink to `composectl` — dispatching a different command set depending on which name it's invoked as.

**As `compose`** — thin per-project Docker Compose wrapper, run from inside a service directory (all subcommands take an optional `[SERVICES]...` filter):

| Command           | Behavior                                                                                                   |
| ----------------- | ---------------------------------------------------------------------------------------------------------- |
| `compose up`      | `docker compose up -d`                                                                                     |
| `compose down`    | `docker compose down`                                                                                      |
| `compose restart` | `docker compose down` + `up`                                                                               |
| `compose pull`    | Pull images without restarting                                                                             |
| `compose ps`      | List containers/status                                                                                     |
| `compose config`  | View/set global config (`--compose-base`, `--compose-data`, `--acme-domain/email/server`, `--docker-host`) |

**As `composectl`** — systemd-service-lifecycle layer, run from anywhere with a `category-service` name:

| Command                                 | Behavior                                                                                                            |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `composectl start/stop/restart`         | `systemctl start/stop/restart` the unit                                                                             |
| `composectl update`                     | Pull new images and restart via systemd                                                                             |
| `composectl enable/disable`             | `systemctl enable/disable`                                                                                          |
| `composectl status`                     | `systemctl status`                                                                                                  |
| `composectl ps`                         | List containers/status                                                                                              |
| `composectl deps list/add/remove/clear` | Manage the `service.toml` dependency graph (`add <service> <dep>... [--requires]`, default relationship is `Wants`) |

### Docker CLI Plugins (`~/.docker/cli-plugins/`)

| Plugin       | Command          | Purpose                                                                  |
| ------------ | ---------------- | ------------------------------------------------------------------------ |
| Network      | `docker net`     | Bootstrap networks from TOML (`-i`) or inspect (`-v`)                    |
| Image List   | `docker img`     | List images grouped by registry                                          |
| Image Update | `docker upgrade` | Pull updates for all local images (`--dry-run`, `--filter`, `--workers`) |
| Pretty PS    | `docker pps`     | Enhanced container status (`-v`/`--verbose`, `--running`)                |
| GPU Checker  | `docker nvidia`  | `nvidia-smi` passthrough                                                 |
| Live Stats   | `docker pstats`  | Live container stats dashboard (`-1` one-shot, `-s` sort column)         |

## Custom Builds

- `ai/forge/Dockerfile` + `ai/forge/entrypoint.sh`: CUDA 13.2, Python 3.13, Forge Neo SD WebUI
- `ai/openwebui/sidecar-cpu/Dockerfile` + `build.sh`: Zen5-optimized llama.cpp CPU inference
- Images pushed to `ghcr.io/delfianto/`

## Testing

- `ai/embedding/test/test_embedding.py`: pytest-based embedding/reranking pipeline validator (own `.venv` under `ai/embedding/test/`)

## Adding a New Service

1. Create `category/service/` directory with `compose.yaml` and `.env`
2. Add service-specific env files (`{service}.env`, `{service}.env.local`)
3. Connect only to required networks (declare as `external: true`)
4. Add Traefik labels if web-accessible
5. Add Homepage labels for dashboard visibility
6. Define data paths via `DATA_DIR` env var
7. If GPU-dependent, add `devices: - nvidia.com/gpu=${GPU_ID}` and set `GPU_ID` in `.env`
8. Update `service.toml` if the service has dependencies
9. Register with systemd: `composectl deps add <category-service> <dependency>...`, then `composectl enable <category-service>`
10. Test with `compose up` before enabling via `composectl`

## Editing Guidelines

- Secrets: real credential values live only in `/srv/appdata/secret/` (`SECRET_DIR`), one file per secret, injected via Compose `secrets:` (+ the `/secret-env.sh` shim where the image needs it). Once a service is migrated, its `*.env.local` should be reduced to a comment-only stub — don't put live secret values back into it.
- Do not change network subnet assignments without checking `~/.config/docker/networks.toml` and all compose files
- Do not change GPU assignments without considering VRAM contention across services sharing a GPU
- Keep `service.toml` in sync when adding or removing service dependencies (mirror with `composectl deps add/remove`)
- Validate with `docker compose config --quiet` after editing — never dump full unfiltered config while a service's env files still hold secrets
- Compose services declare `restart: "no"` — systemd (`compose@.service` + `composectl`) owns lifecycle and restart-on-failure, not Docker's restart policy.
