# Lychee

One image serves the API and built Vue frontend on port 8000. Images are published
to GHCR from upstream releases at `ghcr.io/delfianto/lychee`.

Compose pins `IMAGE_TAG` to the release tag in `.env` (or overrides in `.env.local`).
For an upgrade or rollback, set `IMAGE_TAG` in `.env.local` and restart the service:

```sh
composectl update media-lychee
```

## Configuration and first start

`.env` contains defaults and paths; `.env.local` overrides them. `lychee.env`
contains runtime settings; optional `lychee.env.local` overrides those. Global
`COMPOSE_BASE` and `TRAEFIK_ACME_DOMAIN` come from `~/.config/docker/compose.env`.

Create the central encryption key once (keep it with database backups). This
preserves an existing key and never prints it:

```sh
python3 - <<'PY'
import os
import secrets
from pathlib import Path

directory = Path(os.environ.get('SECRET_DIR', '/path/to/secret'))
directory.mkdir(mode=0o700, parents=True, exist_ok=True)
key = directory / 'lychee_secret'
if not key.exists():
    fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(secrets.token_urlsafe(48))
PY
mkdir -p "${DATA_DIR}" "${DATA_DIR}/library"
docker compose --env-file "$HOME/.config/docker/compose.env" --env-file .env config --quiet
composectl enable media-lychee
composectl start media-lychee
```

Open `https://lychee.<your-domain>` and register `/library` in Settings → Libraries,
then scan. Set `LIBRARY_DIR` in `.env.local` to use an existing collection. The
library is writable for downloads, imports, and metadata sidecars; change its
mount to `:ro` if only reading existing media. No host port is published.

`/data` persists SQLite. `/library` persists your collection and generated media
(such as thumbnails). `STORAGE_PATH=/library` also makes this mount the root of
Lychee's library/import folder browser. `LIBRARY_DIR` chooses its host location;
inside Lychee, use `/library` paths. Back up both and
`${SECRET_DIR}/lychee_secret`; changing or losing
the key makes stored account credentials unreadable. No external database or GPU
is required, so no `service.toml` dependency entry is needed.

After changing runtime settings, use `composectl restart media-lychee`.
Lychee currently follows a trusted single-user model without login; restrict access
at your reverse proxy or network boundary when needed.
