---
name: service-config
description: View or update composectl/compose's own global settings (COMPOSE_BASE, COMPOSE_DATA, Traefik ACME domain/email/server, DOCKER_HOST, Infisical) stored in ~/.config/docker/compose.env. Use when checking or changing host-wide interpolation defaults shared by every project, not a specific service's env files.
---

`compose config` / `composectl config` (identical implementation, either persona works) manage the **machine-wide** settings file — `/etc/compose.env` if root, `~/.config/docker/compose.env` under rootless Docker (this host's mode). This is the file `AGENTS.md` calls the "machine-wide interpolation layer": it's loaded before each project's own `.env` via `COMPOSE_ENV_FILES`, and the project's `.env` wins on any key collision. Don't confuse it with a service's own `.env`/`{service}.env`/`.local` files — those are per-project and this tool doesn't touch them.

## View

```bash
compose config --json
```
```json
{
  "command": "config",
  "path": "/home/geist/.config/docker/compose.env",
  "exists": true,
  "config": {
    "COMPOSE_BASE": "/srv/compose",
    "COMPOSE_DATA": "/srv/appdata",
    "DOCKER_HOST": "unix:///run/user/1000/docker.sock",
    "DOCKER_SOCK": "/run/user/1000/docker.sock",
    "TRAEFIK_ACME_DOMAIN": "vexelstrom.app",
    "TRAEFIK_ACME_EMAIL": "dwi.elfianto@gmail.com",
    "TRAEFIK_ACME_SERVER": "https://acme-v02.api.letsencrypt.org/directory"
  }
}
```
(`DOCKER_SOCK` is host-specific extra content the tool preserves but doesn't manage — see "unknown keys" below.)

## Update

Every flag validates before anything is written; on failure the file is untouched.

| Flag | Key | Validation |
|---|---|---|
| `--compose-base <PATH>` | `COMPOSE_BASE` | directory must exist |
| `--compose-data <PATH>` | `COMPOSE_DATA` | directory must exist |
| `--acme-domain <DOMAIN>` | `TRAEFIK_ACME_DOMAIN` | RFC 1035 domain |
| `--acme-email <EMAIL>` | `TRAEFIK_ACME_EMAIL` | RFC 5322-ish email |
| `--acme-server <URL>` | `TRAEFIK_ACME_SERVER` | valid HTTP(S) URL, resolvable host |
| `--docker-host <URI>` | `DOCKER_HOST` | `unix://` (socket must exist), `tcp://`, or `ssh://` |
| `--infisical-project-id <ID>` | `INFISICAL_PROJECT_ID` | none |
| `--infisical-env <ENV>` | `INFISICAL_ENV` | none |
| `--infisical-address <URL>` | `INFISICAL_ADDRESS` | valid HTTP(S) URL |
| `--infisical-bootstrap <LIST>` | `INFISICAL_BOOTSTRAP` | comma-separated, no empty entries |

Multiple flags in one call are fine:
```bash
compose config --acme-domain example.com --acme-email admin@example.com --json
```
```json
{"command": "config", "status": "updated", "path": "/home/geist/.config/docker/compose.env"}
```

Any key already in the file that isn't one of the flags above (e.g. `DOCKER_SOCK`) is preserved verbatim on write — the tool only ever touches the keys you pass.

## This host's mode

Rootless (`DOCKER_HOST=unix:///run/user/1000/docker.sock`, config at `~/.config/docker/compose.env`, `systemctl --user` under the hood for the lifecycle/deps skills). Don't assume `/etc/compose.env` — that path is only used when running as root.
