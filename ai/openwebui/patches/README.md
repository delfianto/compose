# VectorChord (vchordrq) patches

Open WebUI's `pgvector` backend only understands the `ivfflat` and `hnsw`
index methods natively. The database this project actually runs is
`db/vchord` (Postgres + the [VectorChord](https://github.com/tensorchord/VectorChord)
extension), which uses its own index type, `vchordrq`, with different
`WITH (...)` options syntax than plain pgvector. `apply.py` patches that
support in at container start:

1. `open_webui/config.py` -- allow `vchordrq` as a valid
   `PGVECTOR_INDEX_METHOD` value (upstream's validation tuple rejects
   anything outside `('ivfflat', 'hnsw', '')` and silently resets it to
   `''`).
2. `open_webui/retrieval/vector/dbs/pgvector.py` -- teach
   `PgvectorClient._vector_index_configuration()` to emit
   `WITH (options = $$ [build.internal] lists = [N] $$)` for `vchordrq`
   instead of falling through to plain pgvector's `WITH (lists = N)`,
   which is the wrong option syntax for a VectorChord index.

## Why patch instead of bind-mounting full replacement files

The previous approach in this directory bind-mounted complete,
frozen copies of both files over the image's own. That's a full fork:
every future open-webui release's fixes and features to those two files
get silently shadowed, and there's no signal if upstream restructures
code the fork depends on -- it would just keep running the old logic,
possibly now incompatible with the rest of a newer image.

`apply.py` instead does an exact string replace against whatever the
current image ships. Everything else in both files -- including any
future upstream changes -- passes through untouched. If upstream edits
the specific lines this patch targets, the string match fails and the
container refuses to start with a clear error, instead of quietly
running stale or broken logic.

## Updating after an upstream change

If a `docker upgrade` / `composectl update ai-openwebui` starts failing
with `FATAL: expected code not found in ...`:

1. Check what changed:
   ```bash
   docker run --rm --entrypoint cat ghcr.io/open-webui/open-webui:latest-slim \
     /app/backend/open_webui/config.py > /tmp/new-config.py
   docker run --rm --entrypoint cat ghcr.io/open-webui/open-webui:latest-slim \
     /app/backend/open_webui/retrieval/vector/dbs/pgvector.py > /tmp/new-pgvector.py
   diff /tmp/new-config.py path/to/old/config.py
   diff /tmp/new-pgvector.py path/to/old/pgvector.py
   ```
2. Update the `old`/`new` string pairs in `apply.py` to match the new
   surrounding code.
3. Verify: `python3 apply.py` against a scratch copy of the new files
   before deploying (see the FATAL-path check below).

## What was here before

`config.py`/`pgvector.py` (the pre-patch, full-file forks) were diffed
against upstream `open-webui/open-webui` main at the time this was
written; the *entire* difference from stock was these same 3 lines.
That's the whole patch -- nothing else in either file was ever modified.
