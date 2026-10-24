# Lychee

One image serves the API and built Vue frontend on port 8000. Source comes from
https://github.com/delfianto/lychee.git; the local development checkout is never
used. Like `ai/comfyui`, builds use `build.sh` and `docker-bake.hcl`.

```sh
./build.sh --pull
# Select a release tag:
./build.sh --ref v0.1.0-beta.1
# Inspect the resolved build without building:
./build.sh --print
```

Every build fetches an explicit Git release tag and resolves it to an exact commit.
The tag must match `v` plus the version in the release's `frontend/package.json`.
The image gets `ghcr.io/delfianto/lychee:v0.1.0-beta.1` and `:latest`; commit-hash
image tags are retired. The OCI version label records the app version and the
revision label retains the exact source commit. Builds require host Python 3
for reading the release version.

Compose pins `IMAGE_TAG` to the release tag. For an upgrade or rollback, select the
release in `.env.local` (`LYCHEE_REF=v...` and `IMAGE_TAG=v...`), run `./build.sh`,
then `composectl restart media-lychee`. Restarting alone does not rebuild.
Builds load into Docker by default; use `./build.sh --push` to publish to GHCR.

The build uses upstream's frozen Bun and uv lockfiles, Python 3.14, Node 24, and
Bun 1.4.4. FFmpeg enables gallery video posters. The runtime excludes build tools,
frontend dependencies, development Python dependencies, and the optional MCP server.

Upstream currently returns JSON at `/` and does not mount the frontend.
`deployment.py` replaces that landing route and serves the frontend with a Vue
Router fallback, retaining API routes, errors, documentation, and startup migrations.
One Uvicorn worker keeps the in-memory background queue and SSE broker together.

## Configuration and first start

`.env` contains build and host paths; `.env.local` overrides them. `lychee.env`
contains runtime settings; optional `lychee.env.local` overrides those. Global
`COMPOSE_BASE` and `TRAEFIK_ACME_DOMAIN` come from `~/.config/docker/compose.env`.

Create the central encryption key once (keep it with database backups). This
preserves an existing key and never prints it:

```sh
python3 - <<'PY'
import os
import secrets
from pathlib import Path

directory = Path('/srv/appdata/secret')
directory.mkdir(mode=0o700, parents=True, exist_ok=True)
key = directory / 'lychee_secret'
if not key.exists():
    fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(secrets.token_urlsafe(48))
PY
mkdir -p /srv/appdata/lychee /srv/appdata/lychee/library
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
`/srv/appdata/secret/lychee_secret`; changing or losing
the key makes stored account credentials unreadable. No external database or GPU
is required, so no `service.toml` dependency entry is needed.

After changing runtime settings or rebuilding, use `composectl restart media-lychee`.
Lychee currently follows a trusted single-user model without login; restrict access
at your reverse proxy or network boundary when needed.
