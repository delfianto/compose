---
name: service-deps
description: Manage systemd inter-service start-up dependencies (Requires=/Wants=/After=) between compose services via composectl deps, and keep service.toml's documentation mirror in sync. Use when adding/removing a dependency between services (e.g. "librechat needs postgres up first") or auditing the current dependency graph before enabling a new service.
---

Compose services in this repo don't depend on each other through `depends_on:` in a compose file — that only orders containers *within* one project. Cross-project ordering (e.g. `ai-librechat` must come up after `db-postgres`) is expressed as systemd drop-in overrides, managed through `composectl deps`.

## Commands

| Action | Command | Effect |
|---|---|---|
| Add soft dep | `composectl deps add <svc> <dep...>` | `Wants=` + `After=` |
| Add hard dep | `composectl deps add <svc> <dep...> --requires` | `Requires=` + `After=` (fails the dependent unit if the dep fails) |
| Remove dep | `composectl deps remove <svc> <dep...>` | strips from `Requires=`/`Wants=`/`After=` |
| Clear all | `composectl deps clear <svc>` | deletes the drop-in file entirely |
| List one service | `composectl deps list <svc>` | this service's own forward deps (`required`/`wanted`) + explicit overrides |
| List everything | `composectl deps list` | every discovered `compose@*.service` unit, each with its own forward deps |

Every service implicitly gets `Requires=docker.service` + `BindsTo=docker.service` — you don't add those yourself.

Storage: `<systemd_dir>/compose@<service>.service.d/dependencies.conf` (rootless: `~/.config/systemd/user/...`). `deps add`/`remove`/`clear` all run `systemctl daemon-reload` for you.

## JSON shapes

`deps add`:
```json
{"command": "deps", "action": "add", "service": "ai-librechat",
 "added": ["db-postgres", "ai-bifrost"], "type": "Wants"}
```

`deps list <svc>` — `state` is this unit's own `ActiveState`; `required` is `Requires=` + `BindsTo=` (compose units only — the implicit `docker.service` edge every unit has is filtered out as noise); `wanted` is `Wants=`. Both are **forward** deps (what this service depends on), not reverse-dependents. `overrides` is the raw drop-in file contents (`null` if none exists) — `Requires`/`Wants`/`BindsTo`/`After` always present even when empty, unlike `required`/`wanted` below:
```json
{"command": "deps", "action": "list", "service": "compose@ai-openwebui.service",
 "state": "inactive",
 "required": ["compose@ai-bifrost.service", "compose@ai-embedding.service", "compose@db-postgres.service"],
 "wanted": ["compose@ai-ollama.service"],
 "overrides": {
   "After": ["compose@db-postgres.service", "compose@ai-bifrost.service", "compose@ai-embedding.service", "compose@ai-ollama.service"],
   "BindsTo": [],
   "Requires": ["compose@db-postgres.service", "compose@ai-bifrost.service", "compose@ai-embedding.service"],
   "Wants": ["compose@ai-ollama.service"]
 }}
```

**`required`/`wanted` are omitted entirely when empty** (not `[]`) — e.g. a leaf service with no deps at all just returns `{"command": "deps", "action": "list", "service": "compose@db-postgres.service", "state": "inactive", "overrides": null}`. Don't assume the keys exist; check with `.get()`/`in` rather than indexing directly.

`deps list` (no service) — every discovered `compose@*.service` unit (walked outward from `docker.service`'s reverse-dependents), each as its own `{state, required?, wanted?}` under `services`, same omit-if-empty rule per entry:
```json
{"command": "deps", "action": "list", "services": {
  "compose@ai-embedding.service": {"state": "inactive"},
  "compose@infra-forgejo.service": {"state": "inactive", "required": ["compose@db-postgres.service"]},
  "compose@infra-traefik.service": {"state": "active"}
}}
```
No `overrides` in the all-services view — that's single-service only.

## Gotcha: `service.toml` is documentation only, not machine-fed

`AGENTS.md` describes `service.toml` as the dependency graph, "mirrored via `composectl deps`" — but there is no automated sync. The tool *does* have a bulk-apply path (`composectl start|enable <svc...> --deps <file.toml>`), but it expects a different TOML shape than what's checked into this repo:

- Expected by `--deps`: `[dependencies.<service>]` tables (see `src/compose.rs::DependenciesConfig`, `#[serde(rename = "dependencies")]`).
- What `/srv/compose/service.toml` actually has: bare `[ai-bifrost]`, `[ai-librechat]`, etc. — no `dependencies.` prefix.

Feeding the current `service.toml` through `--deps` would silently parse to an empty dependency set (the `#[serde(default)]` on that field swallows the mismatch instead of erroring) — it would not throw, and it would not apply anything. So don't reach for `--deps service.toml` expecting it to reconcile state.

The actual, working mechanism — and the one `AGENTS.md`'s "Editing Guidelines" already prescribes — is: apply each dependency by hand with `composectl deps add <category-service> <dep>... [--requires]`, then hand-edit `service.toml` to match, as the human-readable record. Treat `service.toml` as a snapshot you keep honest, not an input file.

## Example: adding a new consumer service's dependencies

```bash
composectl deps add ai-openwebui db-postgres --requires
composectl deps add ai-openwebui ai-bifrost ai-embedding ai-ollama
composectl deps list ai-openwebui --json
```
Then update the `[ai-openwebui]` block in `/srv/compose/service.toml` to match, per the existing convention (`requires = [...]` for everything above, since the file doesn't distinguish `Requires` from `Wants`).
