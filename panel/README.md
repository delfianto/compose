# Management panels

Dashboards for finding services, inspecting containers, and managing image
updates. These projects connect to the same rootless Docker daemon as the
applications they display.

| Project | Purpose | Integration |
| --- | --- | --- |
| [Homepage](homepage/) | Service dashboard with links and application widgets | Discovers `homepage.*` container labels; persistent dashboard configuration and custom icons; `home.${TRAEFIK_ACME_DOMAIN}` |
| [Portainer](portainer/) | Browser-based Docker and container management | Persistent management state and Docker API access; `panel.${TRAEFIK_ACME_DOMAIN}` |
| [Tugtainer](tugtainer/) | Tracks and manages container image updates | Persistent update-manager state; self-protection label; `updates.${TRAEFIK_ACME_DOMAIN}` |

## Discovery and access

All three web interfaces use Traefik on `proxy`. Homepage also joins `metrics`
and reads application-specific widget endpoints where configured. Service
labels supply display names, groups, icons, URLs, and widget configuration;
they do not create application routes or DNS records on their own.

`DOCKER_SOCK` must identify the rootless daemon's socket. A read-only socket
bind mount does not make the Docker API read-only: the daemon's API determines
which operations a connected application can perform. Keep application access
consistent with that level of control.

## Image updates

Custom local images need their build workflow; a registry pull cannot
rebuild ComfyUI, ComfyUI MCP, or Strata's source.

The companion `docker upgrade` command from
[docker-conf](https://github.com/delfianto/docker-conf) refreshes local images
host-wide and prunes dangling images; it is not limited to the panel category
and does not itself rebuild custom images or restart every service.

[Repository guide](../README.md) · [Traefik routing](../infra/README.md)
