# Media services

Photo libraries, video streaming, and media cataloging. Application state and
source libraries have separate mounts so containers can be recreated without
moving or duplicating the media collection.

| Project | Purpose | Integration |
| --- | --- | --- |
| [Immich](immich/) | Photo/video backup, browsing, and machine-learning search | Server plus CUDA machine-learning container; PostgreSQL/VectorChord and Valkey |
| [PhotoPrism](photoprism/) | Indexes and organizes an existing photo/video library | MariaDB storage; original files mounted read-only; separate writable application storage |
| [Plex + Tautulli](plex/) | Streams a media library and reports playback activity | Plex hardware transcoding plus Tautulli monitoring in one Compose project |
| [Stash](stash/) | Catalogs and organizes an adult-media library | Persistent metadata, generated previews, and caches; hardware-accelerated image |

## Data and library mounts

Review the project's path variables before starting. Immich distinguishes its
writable upload directory from the read-only external photo library. PhotoPrism
mounts originals read-only and writes indexing state elsewhere. Plex and Stash
use separate library paths alongside their persistent configuration and caches.
Read-only behavior comes from each mount's `:ro` setting, not the category name.

Back up uploads, metadata, and databases together where the application links
them. Image updates do not migrate your source collection to a new host path.

## Networks, databases, and GPUs

Web interfaces use Traefik on `proxy`; Plex also publishes its own streaming and
discovery ports. Immich and PhotoPrism join `database` for their storage services.
Immich has recorded requirements on `db-vchord` and `db-valkey`; PhotoPrism names
MariaDB in runtime config, but that dependency is not in the current mirror.

GPU-enabled containers use their project's `GPU_ID`, currently GPU 1 on this
host. Immich's machine-learning sidecar uses CUDA; PhotoPrism, Plex, and Stash
also declare NVIDIA access. These workloads share the 3060 with AI services,
so transcoding and inference can compete for VRAM.

[Repository guide](../README.md) · [Databases](../db/README.md) · [Traefik](../infra/README.md)
