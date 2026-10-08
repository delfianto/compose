# Homelab Compose

A modular Docker Compose homelab for local AI, databases, media, infrastructure,
and management tools. Each application is an independent Compose project with
its own configuration and persistent data. The deployment uses rootless Docker,
systemd for service lifecycle, NVIDIA CDI for GPU access, and Traefik for HTTPS.

The files describe available projects; a directory's presence does not mean the
service is running or enabled at boot.

## Explore the repository

| Directory | What belongs here | Guide |
| --- | --- | --- |
| `ai/` | LLM inference, chat clients, embeddings, and image generation | [AI services](ai/README.md) |
| `db/` | Shared relational databases, document storage, and caches | [Databases](db/README.md) |
| `infra/` | HTTPS routing, certificates, Git hosting, and secret management | [Infrastructure](infra/README.md) |
| `media/` | Photo libraries, streaming, and media organization | [Media](media/README.md) |
| `panel/` | Service discovery dashboards and container management | [Management panels](panel/README.md) |
| `lib/` | Scripts shared across container entrypoints | [Shared helpers](lib/README.md) |

```text
compose/
├── ai/<project>/
├── db/<project>/
├── infra/<project>/
├── media/<project>/
├── panel/<project>/
├── lib/
├── service.toml
└── AGENTS.md
```

Project directories normally contain `compose.yaml` and `.env`, plus
application-specific runtime env files. `ai/risuai` uses `compose.yml`.
Persistent data belongs outside the checkout, usually under `/srv/appdata/`,
with larger models and media on separately configured storage mounts.

## Designed for compose-utils

[compose-utils](https://github.com/delfianto/compose-utils) provides two commands
from one Rust binary: `compose` wraps direct Docker Compose operations, while
`composectl` manages projects through systemd, including startup, updates,
boot persistence, and dependencies. It supports rootless Docker and centralized
host configuration.

**compose-utils is optional; it makes life much easier.** Every project can run
with ordinary `docker compose` commands. The tools save you from typing the
full project path and env-file arguments each time, and provide a consistent
way to manage startup, updates, and dependencies across projects.

This repository's `category/project` layout is intentional. With `COMPOSE_BASE`
pointing at the checkout, `ai/ollama` resolves to `ai-ollama` and
`infra/traefik` to `infra-traefik`. Hyphens inside project names are preserved:
`ai/comfyui-mcp` becomes `ai-comfyui-mcp`. One project can contain multiple
containers; for example, `media/plex` manages Plex and Tautulli together.

Compose `depends_on` coordinates services within one Compose project; it does
not manage dependencies between separate projects in this repository. Systemd
provides that cross-project ordering through `Requires=`, `Wants=`, and `After=`.
Services declare `restart: "no"` because systemd also owns their lifecycle and
failure recovery on this host. `composectl` is the convenient way to use that
setup:

```sh
composectl status infra-traefik --json
composectl start ai-ollama --json
composectl update ai-ollama --json
composectl enable ai-ollama --json
```

Without compose-utils, the equivalent direct startup command looks like this
(include each project env file only if it exists):

```sh
docker compose \
  --project-directory /srv/compose/ai/ollama \
  --env-file "$HOME/.config/docker/compose.env" \
  --env-file /srv/compose/ai/ollama/.env \
  --env-file /srv/compose/ai/ollama/.env.local \
  up -d
```

You also need to arrange cross-project startup order and failure recovery
yourself, through systemd units or another lifecycle manager. Plain Compose
does not provide dependency management between these separate projects.

The direct `compose` command is useful for inspection and initial iteration from
a project directory. If you use the systemd setup, after direct container lifecycle changes use
`composectl sync --json` to reconcile systemd's tracked state. Locally built
images may need their project's build script instead of a pull-based update.

[service.toml](service.toml) documents cross-project dependencies. The installed
systemd overrides are managed separately with `composectl deps`; updating that
file alone does not change the live dependency graph. Keep both in sync.
Ordering starts a dependency first but does not prove its application is ready.

## Configuration and secrets

| File or location | Purpose | Versioned? |
| --- | --- | --- |
| `~/.config/docker/compose.env` | Host-wide paths, domain, ACME settings, and Docker endpoint | Outside this repository |
| `<project>/.env` | Compose interpolation defaults: image tags, mounts, GPU IDs | Yes |
| `<project>/.env.local` | Local interpolation overrides, loaded by compose-utils | No |
| `<project>/<service>.env` | Application runtime settings | Yes |
| `<project>/<service>.env.local` | Local runtime overrides, when referenced by `env_file` | No |
| `/srv/appdata/secret/` | File-backed credentials mounted as Docker secrets | No |

`compose` and `composectl` load existing interpolation files in order:
`~/.config/docker/compose.env`, the project's `.env`, then `.env.local`.
Later files override earlier ones; missing files are skipped, so projects do not
need an empty `.env`. The tools ignore inherited `COMPOSE_ENV_FILES`.
Explicit shell variables still take precedence for direct commands. Systemd
launches read global defaults through the files so project overrides can win.

Raw `docker compose` commands need equivalent `--env-file` arguments;
[Strata](ai/strata/README.md) supplies `./compose.sh` for this purpose.
Runtime `env_file` entries are a separate mechanism; an `environment:` value
overrides them.

Keep real passwords and tokens out of tracked files. The preferred pattern is
one credential per file in `SECRET_DIR`, with directory mode `0700` and file mode
`0600`, mounted using Compose `secrets`. Applications that lack native secret-file
support use [lib/secret-env.sh](lib/README.md). Some older projects retain
service-specific secret paths; their Compose definitions are authoritative.

After editing a project, validate without printing resolved credentials:

```sh
docker compose config --quiet
```

## Networks and HTTPS

Networks are created outside individual projects and declared `external: true`.
The host's `~/.config/docker/networks.toml` defines their shared addressing.

| Network | Subnet | Internal | Role |
| --- | --- | --- | --- |
| `proxy` | `172.20.0.0/24` | No | Traefik-facing applications and outbound connectivity |
| `metrics` | `172.21.0.0/24` | Yes | Monitoring connectivity |
| `database` | `172.22.0.0/24` | Yes | Application-to-database traffic |
| `genai` | `172.23.0.0/24` | Yes | AI APIs and inter-service traffic |
| `auth` | `172.24.0.0/24` | Yes | Reserved authentication connectivity |

Traefik is the shared HTTP entrypoint: DNS directs a hostname to the host,
Traefik selects a router from container labels, terminates TLS, and forwards to
the application's internal port over `proxy`. Cloudflare DNS-01 handles ACME
certificate validation. Traefik routes requests; it does not create application
DNS records. See the [infrastructure guide](infra/README.md#traefik-routing-and-certificates)
for the full flow and a label example.

Connect services only to the networks they need. Some database projects also
use a per-project `default` network, and some applications publish direct API,
SSH, or media-discovery ports in addition to their Traefik routes.

## Rootless Docker

These services run on a rootless Docker daemon. Use the configured Docker
context or `DOCKER_HOST` without `sudo`; running Docker with `sudo` may
select a different daemon.

Container UID/GID `0:0` maps to the daemon owner's host UID/GID (`1000:1000`
on this host). Nonzero container IDs map to subordinate host IDs: container
UID 1000 maps to host UID 100999 with this host's current mapping. For a
service that needs to write a daemon-user-owned bind mount, use container
`user: "0:0"` unless the application requires another user. If the image
drops privileges itself, prepare ownership for that application's mapped
UID instead. Do not recursively change data ownership to host UID 1000
without checking which container user actually writes it.

Create bind-mounted data directories as the daemon owner before starting
the service. Projects can use `bind.create_host_path: false` to catch
missing or incorrect paths instead of creating directories automatically.
NVIDIA services use CDI device declarations (`nvidia.com/gpu=0`, etc.);
privileged mode and host networking are not required for GPU access.

Containers cannot raise their memlock limit beyond the rootless daemon's
inherited hard limit. This host currently allows **32 GiB**
(`34359738368` bytes); requesting unlimited memlock (`-1`) fails container
creation with `error setting rlimit type 8: operation not permitted`.
For inference services that pin RAM, set a finite Compose `ulimits.memlock`
within that ceiling and match any application-specific pinning limit.
Memlock limits pinned memory, not total application RAM.

Verify the daemon and its current limits with:

```sh
docker info --format '{{json .SecurityOptions}}'
systemctl --user show docker.service -p LimitMEMLOCK -p LimitMEMLOCKSoft
```

Shared Docker networks remain available to rootless containers. HTTP services
can use Traefik without publishing their own host ports.

## Bringing up a project

1. Configure the rootless Docker endpoint and host-wide values in `compose.env`.
2. Create the external networks and prepare the project's data and secret files.
3. Review the project's env files, mounts, GPU allocation, and build instructions.
4. Validate the Compose configuration and arrange cross-project startup order
   (with systemd dependencies if using the composectl setup).
5. Start the project, check health, and enable boot startup when appropriate.

Databases generally start before their consumers. Traefik must be running for
domain-based access. GPU device visibility is shared, not exclusive: Ollama,
ComfyUI, Strata, and other inference services can compete for the same VRAM.
Category guides explain their integration points and service-specific exceptions.

[AGENTS.md](AGENTS.md) contains the detailed repository conventions and editing
guidance. [docker-conf](https://github.com/delfianto/docker-conf) provides the
companion network definitions and Docker CLI plugins used on this host.

# Disclaimer

This project comes without any warranty of any kind. By using this software, you accept all risks, including but not limited to:

- The Borg may invade your neighborhood.
- Your dog may suddenly hate you.
- Coffee may taste slightly more bitter.
- Spontaneous interpretive dance outbreaks are possible.
- The universe may collapse into a potato.

I am not responsible for any of these (or other) outcomes. Use at your own risk!

# License

[MIT License](https://github.com/delfianto/compose/blob/main/LICENSE)
