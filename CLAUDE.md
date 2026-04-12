# CLAUDE.md

## Project Overview

Docker Compose orchestration for a self-hosted homelab. Modular compose files manage databases, generative AI, media streaming, infrastructure, and MCP servers. Deployed on Linux with systemd, NVIDIA GPUs, and Traefik reverse proxy.

**Repository**: `github.com/delfianto/compose`
**Wiki**: `github.com/delfianto/compose/wiki` (cloned at `../compose-wiki`)
**License**: MIT

## Directory Layout

```
.
├── ai/               # AI/ML services (bifrost, ollama, embedding, openwebui, librechat, comfyui, forge, risuai)
├── db/               # Databases (postgres, mariadb, mongo, valkey, qdrant)
├── infra/            # Infrastructure (forgejo, infisical)
├── media/            # Media services (immich, photoprism, plex, stash)
├── mcp/              # MCP servers (valkey, qdrant, dbhub)
├── panel/            # Reverse proxy & dashboard (traefik, homepage, portainer, tugtainer)
├── service.toml      # Service dependency graph
└── CLAUDE.md
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

| File | Purpose | Committed to git |
|------|---------|-----------------|
| `.env` | Shell interpolation vars (image tags, paths, UIDs, GPU IDs) | Yes |
| `.env.local` | Local overrides for `.env` | No (gitignored) |
| `{service}.env` | Container runtime env vars (app config, credentials) | Yes |
| `{service}.env.local` | Secrets and local-only container vars | No (gitignored) |

**Precedence** (last wins): `.env` < `.env.local` < `env_file:` entries < `environment:` section

**Rules**:
- Never hardcode secrets in compose files or committed env files
- All passwords/tokens go in `.local` or `.secret` files
- Document required variables with comments in base env files

### Secrets

- Docker-managed secrets mounted read-only at `/run/secrets/{name}`
- Secret files stored at `${DATA_DIR}/{secret_name}.txt` or `panel/secret/`
- Referenced in compose via `file: ${DATA_DIR}/secret.txt`
- `.gitignore` blocks: `*.local`, `*.secret`, `*.key`, `*.pem`, `*.crt`, `certs/`, `data/`, `global.env`

### Networks

Five isolated Docker bridge networks (must be pre-created via `docker nbs`):

| Network | Subnet | Internal | Purpose |
|---------|--------|----------|---------|
| `proxy` | 172.20.0.0/24 | No | Traefik-exposed services |
| `metrics` | 172.21.0.0/24 | Yes | Monitoring (future) |
| `database` | 172.22.0.0/24 | Yes | Database services |
| `genai` | 172.23.0.0/24 | Yes | AI/ML inter-service |
| `auth` | 172.24.0.0/24 | Yes | Authentication (future) |

All networks are declared `external: true` in compose files. Services connect only to networks they need. Multi-network services must specify `traefik.docker.network=proxy` label.

### GPU Assignment

Dual NVIDIA GPU setup with explicit device allocation per service:

- GPU 0+1: Ollama (24GB limit)
- GPU 0: Image generation (ComfyUI, Forge) ~16GB
- GPU 1: Embedding/reranking (12GB each), OpenWebUI sidecar (2GB), Qdrant
- Configured via `GPU_ID` env var and `deploy.resources.reservations.devices`

### Data Paths

- `/srv/appdata/{service}` (`DATA_DIR`): Persistent service data
- `/srv/compose/{path}` (`PROJ_DIR`): Project/compose files
- `/mnt/{media_type}`: External media mounts (Plex, Stash, PhotoPrism)
- Bind mounts use `:ro` where write access is unnecessary

### Traefik Labels

Standard label pattern for exposed services:

```yaml
labels:
  traefik.enable: "true"
  traefik.docker.network: proxy
  traefik.http.routers.{name}.rule: "Host(`{subdomain}.${TRAEFIK_ACME_DOMAIN}`)"
  traefik.http.routers.{name}.entrypoints: websecure
  traefik.http.routers.{name}.tls.certresolver: cloudflare
  homepage.group: "{Category}"
  homepage.name: "{Display Name}"
  homepage.icon: "{icon}.svg"
```

### Homepage Dashboard Labels

Services include `homepage.*` labels for auto-discovery by the Homepage dashboard service.

## Service Dependencies

Defined in `service.toml` and mirrored in systemd drop-in files:

```
ai-bifrost       -> db-postgres
ai-librechat     -> db-postgres, ai-bifrost, ai-embedding, ai-ollama
ai-openwebui     -> db-postgres, db-qdrant, ai-bifrost, ai-embedding, ai-ollama
infra-forgejo    -> db-postgres
infra-infisical  -> db-postgres, db-valkey
media-immich     -> db-postgres, db-valkey
```

**Startup order**: databases -> infrastructure -> AI foundations -> AI consumers -> media -> panel

## Tooling

### Compose Wrapper (`/usr/local/bin/compose`)

Enhanced Docker Compose wrapper with sensible defaults:

| Command | Behavior |
|---------|----------|
| `compose up` | `docker compose up --remove-orphans --detach` |
| `compose down` | `docker compose down --remove-orphans --volumes` |
| `compose logs` | `docker compose logs -f --tail=100` |
| `compose ps` | Pretty table format |
| `compose build` | `docker compose build --no-cache` |
| `compose exec` | Opens `/bin/bash` if no command given |

Supports `COMPOSE_PROJECT` env var for hyphenated project names (e.g., `genai-ollama` -> `genai/ollama`).

### Service Controller (`/usr/local/bin/composectl`)

Systemctl wrapper for `docker-compose@` template units:

```bash
sudo composectl start/stop/restart/enable/disable <service>
composectl status/is-active/is-enabled/list/logs <service>
```

### Systemd Installer (`systemd.py`)

```bash
sudo python3 systemd.py install --acme-domain example.com --acme-email you@example.com
sudo python3 systemd.py deps add <service> <dependency> requires|wants
python3 systemd.py deps list|check <service>
```

### Docker CLI Plugins

| Plugin | Command | Purpose |
|--------|---------|---------|
| Network Bootstrap | `docker nbs` | Create networks from TOML config |
| Image List | `docker img` | List images grouped by registry |
| Image Update | `docker imu` | Pull updates (supports `--parallel`) |
| Pretty PS | `docker pps` | Enhanced container status (`-v` for verbose) |
| GPU Checker | `docker smi` | Verify NVIDIA GPU availability |

## Custom Builds

- `ai/forge/Dockerfile` + `ai/forge/entrypoint.sh`: CUDA 13.2, Python 3.13, Forge Neo SD WebUI
- `ai/openwebui/sidecar-cpu/Dockerfile` + `build.sh`: Zen5-optimized llama.cpp CPU inference
- Images pushed to `ghcr.io/delfianto/`

## Testing

- `ai/embedding/tests/tei.py`: Embedding/reranking pipeline validator
  - `python tei.py --embed <file>` or `--query <text>`
  - Tests against local endpoints (ports 4000-4002, 6333)

## Adding a New Service

1. Create `category/service/` directory with `compose.yaml` and `.env`
2. Add service-specific env files (`{service}.env`, `{service}.env.local`)
3. Connect only to required networks (declare as `external: true`)
4. Add Traefik labels if web-accessible
5. Add Homepage labels for dashboard visibility
6. Define data paths via `DATA_DIR` env var
7. If GPU-dependent, configure `GPU_ID` and device reservations
8. Update `service.toml` if the service has dependencies
9. Register with systemd: `sudo python3 systemd.py deps add ...`
10. Test with `compose up` before enabling via `composectl`

## Editing Guidelines

- Do not remove or modify `.env.local` or `*.secret` files (they contain deployment-specific secrets)
- Do not change network subnet assignments without checking all compose files
- Do not change GPU assignments without considering memory contention across services
- Keep `service.toml` in sync when adding or removing service dependencies
- Use `compose config` to validate compose files after editing
- All compose services should declare `restart: unless-stopped` (systemd handles lifecycle, not Docker restart policies)
