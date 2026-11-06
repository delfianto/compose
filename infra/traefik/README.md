# Traefik

Traefik routes Compose services through Docker labels and host services through
its file provider. Both providers use the existing `web` / `websecure` entrypoints
and Cloudflare ACME resolver. Systemd owns the container lifecycle:

```sh
composectl restart infra-traefik
```

## Local host routes

Keep resolved domains, backend addresses and TLS trust files under the service's
`DATA_DIR`, outside the repository. The committed Compose configuration mounts:

| Host | Container | Contents |
| --- | --- | --- |
| `${DATA_DIR}/dynamic` | `/etc/traefik/dynamic` | Local route YAML/TOML files |
| `${DATA_DIR}/backend-certs` | `/etc/traefik/backend-certs` | Public backend certificates or CA certificates |

Both mounts are read-only. On a new host, create these directories before
starting Traefik; they may remain empty when no host services need routing.
With `DATA_DIR` set to the value in this project's `.env` / `.env.local`:

```sh
mkdir -p "${DATA_DIR}/dynamic" "${DATA_DIR}/backend-certs"
```

The `examples/` directory contains sanitized templates and is not watched or
mounted into Traefik. Commit templates and generic Compose settings, never
the live host route files or backend certificates. The former repository-local
`dynamic/` directory is ignored to prevent accidental reintroduction.

## DeepSeek Harness

1. Copy `examples/dsh.yaml.example` to `${DATA_DIR}/dynamic/dsh.yaml`.
2. Replace both router hostnames with the desired public hostname. Arrange DNS
   separately; Traefik's ACME integration does not create application DNS records.
3. Replace the backend URL with an HTTPS address reachable from Traefik's
   container network. Container `localhost` refers to Traefik itself.
4. Set `serverName` to a DNS name covered by the backend certificate. This is
   the backend TLS identity, which may differ from the public router hostname.
5. Put the backend's public certificate, or its issuing CA certificate, at
   `${DATA_DIR}/backend-certs/dsh.crt`. Keep private keys with the harness and
   credentials in the central secret store.

Traefik's file provider reads this YAML directly. Compose does not expand
`${VARIABLE}` references inside it, so the live file needs resolved values.
The example keeps backend certificate verification enabled.

The directory watcher reloads route changes automatically; replacing the
container mounts or changing Compose options requires a restart. When rotating
a self-signed backend certificate, update `backend-certs/dsh.crt` too and re-save
the route file to trigger a provider reload, then verify the HTTPS route.

On the current host, the live route is in `${DATA_DIR}/dynamic/dsh.yaml` and
the trust certificate is in `${DATA_DIR}/backend-certs/dsh.crt`. Neither is
part of the repository, and the Compose project has no dependency on a
DeepSeek Harness installation when these directories are empty.

[Infrastructure routing guide](../README.md)
