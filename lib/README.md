# Shared container helpers

Scripts bind-mounted into several projects. This directory provides shared
entrypoints for the application categories.

| Helper | Purpose | Used when |
| --- | --- | --- |
| [secret-env.sh](secret-env.sh) | Exports mounted Docker secrets as environment variables, resolves variable references, then executes the application's command | An image accepts credentials through env vars but lacks native secret-file support |

## Secret entrypoint

Mount the helper as `${COMPOSE_BASE}/lib/secret-env.sh:/secret-env.sh:ro` and
set it as the entrypoint. Pass the image's original entrypoint/command chain
through `command`, so the helper hands control back after reading secrets.

Each file in `/run/secrets` becomes an environment variable. Lowercase secret
names are uppercased; names already containing uppercase letters are preserved.
Use a Compose secret's `target` to select the exact variable name expected by
the application. The script uses POSIX `sh` for compatibility with Alpine and
Debian-based images.

## User mapping and privilege dropping

On this rootless deployment, container root maps to the daemon owner and can
read the owner's `0600` credential files. A nonzero container UID maps to a
subordinate host UID and may not be able to read them.

The helper skips its requested `DROP_USER` handoff under rootless Docker unless
`FORCE_DROP_USER=1` is set. Forgejo uses that override because the application
refuses to run as container UID 0. For images such as MongoDB, keep the official
entrypoint responsible for its own privilege drop after the helper exports the
credential. Writable bind mounts must match the final application's mapped UID.

The variable-expansion step evaluates shell expressions in runtime env values;
those files must be trusted configuration. The helper does not retrieve secrets
from Infisical or any remote secret manager.

[Rootless Docker and secrets](../README.md) · [Infrastructure](../infra/README.md)
