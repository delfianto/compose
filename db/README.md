# Databases

Shared persistence and cache services for the rest of the homelab. These
projects have no browser dashboard or Traefik HTTP router. Applications normally
reach them by container name over the external `database` network.

| Project | Purpose | Current integration |
| --- | --- | --- |
| [VectorChord / PostgreSQL](vchord/) | Relational storage with vector and text-search extensions | PostgreSQL for Bifrost, Open WebUI, Forgejo, and Immich; initializes VectorChord, BM25, and tokenizer extensions |
| [MariaDB](mariadb/) | MySQL-compatible relational storage | PhotoPrism database; persistent data and file-backed user/root credentials |
| [MongoDB](mongo/) | Document-oriented database | Available for document-backed applications; official entrypoint handles privilege dropping |
| [Valkey](valkey/) | Redis-compatible cache and key-value store | Bifrost and Immich dependencies; Infisical runtime config also references it |

## Storage and access

Each project mounts its own data beneath `DATA_DIR`. Credentials use Compose
secrets where configured. PostgreSQL's init SQL runs when the database cluster
is first initialized; changing it does not rerun initialization on an existing
data directory. Application database names and accounts still need to match
the consumer's runtime configuration.

These Compose files currently publish database ports to the host as well as
joining `database`: PostgreSQL `5432`, MariaDB `3306`, MongoDB `27017`, and Valkey
`6379`. The network's internal flag does not replace the access rules for those
host bindings. Per-project `default` networks are also present in these files.

## Application dependencies

The checked-in [dependency mirror](../service.toml)
records the configured Bifrost, Open WebUI, Forgejo, and Immich requirements.
PhotoPrism's runtime config names MariaDB, and Infisical references Valkey,
but these relationships are not currently recorded there. Cross-project
dependency management is explained in the [repository guide](../README.md#designed-for-compose-utils).

Read the [rootless ownership guidance](../README.md#rootless-docker)
before adjusting data permissions. An image's own privilege-dropping entrypoint
can require a different mapped owner from container root.

Back up persistent database contents using the database's supported backup
method before upgrades. Container recreation retains the bind mounts; deleting
the data directories does not.

[Repository guide](../README.md)
