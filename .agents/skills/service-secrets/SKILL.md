---
name: service-secrets
description: View/set/delete per-service secrets in Infisical via composectl secret / compose secret. This is a distinct, currently-unconfigured mechanism from the repo's primary docker-secrets/SECRET_DIR convention documented in AGENTS.md — check which one actually applies before using this. Use only if/when Infisical integration is turned on for a service.
---

`composectl`/`compose` ship a `secret` subcommand, but **this is not the secrets mechanism this repo currently uses**. Don't reach for it by default — check `AGENTS.md`'s "Secrets & Privilege Escalation" section and the current config first.

## The two mechanisms — don't conflate them

1. **What this repo actually does today**: secret values live as individual files under `/srv/appdata/secret/` (`SECRET_DIR`), mounted per-service via Compose's own `secrets:` block, with `lib/secret-env.sh` as an entrypoint shim for images that can't read `/run/secrets/*` natively. This is documented in full in `AGENTS.md` and is what every migrated service uses.
2. **What this skill covers**: `composectl secret` / `compose secret`, which wraps the `infisical` CLI and stores secrets remotely in an Infisical project, keyed by service path (`/​<bare-service-name>`). It's opt-in, gated on `INFISICAL_PROJECT_ID` being set in `compose.env`.

Verify which applies before acting:
```bash
compose config --json | jq '.config | has("INFISICAL_PROJECT_ID")'
```
On this host, as of the last check, `compose config --json` returns no `INFISICAL_*` keys at all — Infisical is **not configured**, so every `secret` subcommand below is currently a no-op (see below). If you're asked to set a credential for a service, it almost certainly belongs in `SECRET_DIR` + Compose `secrets:`, not here.

## Commands (once Infisical is configured)

| Action | Command |
|---|---|
| List | `composectl secret list [svc]` |
| Get one | `composectl secret get <KEY> [--service <svc>]` |
| Set/update | `composectl secret set <KEY> <VALUE> [--service <svc>]` |
| Delete | `composectl secret delete <KEY...> [--service <svc>]` |

`svc`/`--service` auto-detects from `$PWD` like other commands, but only if it resolves to exactly one service.

`INFISICAL_BOOTSTRAP` (comma-separated service list in `compose.env`) marks Tier-0 services that must start before Infisical itself is reachable — those skip secret injection entirely, matching this repo's dependency ordering (`db-postgres` etc. come up before `infra-infisical`).

## JSON shapes

Not configured (current state on this host):
```json
{"command": "secret", "status": "noop", "reason": "infisical not configured or not available"}
```

`list`/`get` wrap Infisical's own CLI output verbatim — its formatting isn't under this tool's control, so it's nested as an opaque string rather than structured:
```json
{"command": "secret", "action": "get", "service": "ai-librechat", "key": "MEILI_MASTER_KEY", "raw": "<infisical CLI stdout>"}
```

`set`:
```json
{"command": "secret", "action": "set", "service": "ai-librechat", "key": "MEILI_MASTER_KEY", "status": "ok"}
```

`delete`:
```json
{"command": "secret", "action": "delete", "service": "ai-librechat", "keys": ["MEILI_MASTER_KEY"], "status": "ok"}
```

## Non-JSON side effect worth knowing

`set` prints the value was set but never echoes it back — `infisical secrets set KEY=VALUE` is called directly with the plaintext value as a CLI argument, so it will land in shell history / process listings on whatever machine runs the command. Treat it the same as any other plaintext-secret CLI, not as a safer channel than editing a `.local` file.
