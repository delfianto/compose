#!/usr/bin/env python3
"""
Applies small, targeted source patches to open_webui's config.py and
pgvector.py so PGVECTOR_INDEX_METHOD=vchordrq works with VectorChord's
index syntax.

This replaces bind-mounting full frozen copies of both files (the
previous approach here), which would silently shadow whatever a newer
open-webui image actually ships -- upstream bug fixes and features in
those files would never take effect, and a future upstream refactor
could leave the frozen fork subtly incompatible with the rest of the
(newer) codebase, with no signal that anything was wrong.

Each patch below is an exact (old, new) string pair matched against
whatever the image currently ships:
  - If `old` is found, it's replaced with `new` (patch applied).
  - If `new` is already present, upstream already ships this or a
    previous run already patched it -- skip, no error.
  - If neither is found, upstream changed the code this patch targets.
    Fail loudly (non-zero exit -> container refuses to start) instead
    of guessing or silently running unpatched/incompatible code. See
    patches/README.md for how to update the patch in that case.
"""

import sys
from pathlib import Path

BACKEND = Path("/app/backend/open_webui")

PATCHES = [
    (
        BACKEND / "config.py",
        "if PGVECTOR_INDEX_METHOD not in ('ivfflat', 'hnsw', ''):",
        "if PGVECTOR_INDEX_METHOD not in ('ivfflat', 'hnsw', 'vchordrq', ''):",
    ),
    (
        BACKEND / "retrieval/vector/dbs/pgvector.py",
        "        if index_method == 'hnsw':\n"
        "            index_options = f'WITH (m = {PGVECTOR_HNSW_M}, ef_construction = {PGVECTOR_HNSW_EF_CONSTRUCTION})'\n"
        "        else:\n",
        "        if index_method == 'hnsw':\n"
        "            index_options = f'WITH (m = {PGVECTOR_HNSW_M}, ef_construction = {PGVECTOR_HNSW_EF_CONSTRUCTION})'\n"
        "        elif index_method == 'vchordrq':\n"
        '            index_options = f"WITH (options = $$ [build.internal] lists = [{PGVECTOR_IVFFLAT_LISTS}] $$)"\n'
        "        else:\n",
    ),
]


def main() -> int:
    for path, old, new in PATCHES:
        text = path.read_text()

        if new in text:
            print(f"[vchordrq-patch] {path}: already applied, skipping")
            continue

        if old not in text:
            print(
                f"[vchordrq-patch] FATAL: expected code not found in {path}.\n"
                "open-webui changed this file upstream -- update "
                "ai/openwebui/patches/apply.py (see patches/README.md) "
                "before this image can start.",
                file=sys.stderr,
            )
            return 1

        path.write_text(text.replace(old, new, 1))
        print(f"[vchordrq-patch] {path}: patched")

    return 0


if __name__ == "__main__":
    sys.exit(main())
