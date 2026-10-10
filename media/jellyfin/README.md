# Jellyfin

Start with `composectl start media-jellyfin --json`. To start at boot, use
`composectl enable media-jellyfin --json`.

Open http://192.168.10.2:8096 and complete the setup wizard. Create the admin
account there, then add libraries from `/media`. Media is mounted read-only;
configuration and cache live in `/srv/appdata/jellyfin`.

In Dashboard > Playback > Transcoding, select NVIDIA NVENC to enable hardware
acceleration. GPU 1 is exposed through CDI and shared with Plex and other media
services. Enable only codecs supported by that GPU.

Traefik exposes `https://jellyfin.${TRAEFIK_ACME_DOMAIN}` and Homepage discovers
the service through labels. Android TV can connect directly to
http://192.168.10.2:8096. UDP 7359 is published for discovery; enter the address
manually if discovery does not work through rootless Docker.

There are no external service dependencies. Account credentials are created in
Jellyfin and persisted in its config directory; no credentials belong in env
files. Change the paths, LAN address, or port in `.env` as needed. The image tag
is set directly in `compose.yaml`.
