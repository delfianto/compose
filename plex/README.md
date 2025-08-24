# Plex & Tautulli Docker Compose Stack

This repository provides a ready-to-use [Docker Compose](https://docs.docker.com/compose/) stack to deploy **Plex Media Server** and **Tautulli** for your home or media server. Both services use official [LinuxServer.io](https://www.linuxserver.io/) container images and are pre-configured for Traefik reverse proxy integration, GPU support, and environment-based configuration.

---

## Features

- **Plex Media Server:** Stream your movies, TV shows, and music.
- **Tautulli:** Monitor Plex activity and view detailed usage analytics.
- **Traefik Reverse Proxy Integration:** Labels included for seamless HTTPS and domain routing.
- **Environment-based Configuration:** Easily adjust user IDs, file locations, and timezones.
- **External Proxy Network:** Integrates with Traefik or other reverse proxies via an external Docker network.
- **GPU Hardware Transcoding (Optional):** NVIDIA GPU support for Plex.
- **Easy Setup:** Minimal manual configuration required.

---

## Prerequisites

- **Docker** and **Docker Compose** installed.
- **External Docker network** named `proxy` (see below).
- **NVIDIA GPU drivers** and [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) for hardware transcoding (optional).
- Create a `.env.local` file with required environment variables (see below).
- [Traefik](https://doc.traefik.io/traefik/) running in your `proxy` network (see [traefik project](./traefik) in this repo for a typical setup).

---

## Quick Start

### 1. Clone the Repository

```sh
git clone https://github.com/yourusername/yourrepo.git
cd yourrepo
```

### 2. Create and Edit `.env.local`

Copy the sample file and edit to fit your environment:

```sh
cp .env .env.local
nano .env.local
```

Sample `.env.local`:
```ini
PUID=1001
PGID=1001
UMASK=022
PLEX_TZ=America/New_York
PLEX_ADVERTISE_IP=http://192.168.1.100:32400
DATA_DIR=/mnt/disk1/srv
FILE_DIR=/mnt/disk2/media
```

> **Important:**
> - Do not edit `.env`. Create and use `.env.local` for all variable overrides.
> - Set `PUID` and `PGID` to match your host user's UID/GID (`id -u`, `id -g`).

---

### 3. Create the External Proxy Network

If you haven't already, create a Docker network named `proxy`:

```sh
docker network create proxy
```

---

### 4. Run Traefik (Optional, but recommended)

See the [traefik](./traefik) directory in this repository for a sample Traefik Docker Compose setup.
You must ensure Traefik is running and attached to the `proxy` network before starting Plex and Tautulli, so they can be reached securely via your domain.

---

### 5. Start the Stack

```sh
docker compose -f compose.yml up -d
```

This will launch Plex and Tautulli as defined in `plex.yml` and `tautulli.yml`.

---

> **Note:**
> - Make sure `${TRAEFIK_ACME_DOMAIN}` is set in your environment (typically Traefik's `.env.local`).
> - You can adjust labels to suit your domain, certificate provider, and Plex internal port as needed.

**For more info and advanced configuration, see the [traefik](./traefik) project in this repository.**

---

## Access

- **Plex Web UI:**
  http://localhost:32400
  Or via your reverse proxy, e.g. `https://plex.yourdomain.com`
- **Tautulli Web UI:**
  http://localhost:32401
  Or via your reverse proxy, e.g. `https://tautulli.yourdomain.com`

---

## Data Volumes

- **Media Library:**
  `${FILE_DIR}` → `/media` (Plex)
- **Plex Config & Transcode:**
  `${DATA_DIR}/plex/config` → `/config`
  `${DATA_DIR}/plex/transcode` → `/transcode`
- **Tautulli Config:**
  `${DATA_DIR}/tautulli` → `/config` (Tautulli)

---

## GPU Hardware Acceleration

Plex is configured to use NVIDIA GPU for video transcoding:

- Ensure your host has NVIDIA drivers and [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed.

---

## Customization

- **Change Ports:**
  Edit `ports:` in `plex.yml` and `tautulli.yml`.
- **Change Volume Paths:**
  Adjust `DATA_DIR` and `FILE_DIR` in `.env.local`.
- **Update Images:**
  Run `docker compose pull` to fetch latest images.

---

## Troubleshooting

- Ensure all directories exist and are accessible.
- For GPU issues, verify NVIDIA Docker setup.
- View container logs:
  ```sh
  docker logs plex
  docker logs tautulli
  ```
- For reverse proxy issues, check Traefik logs and label configuration.

---

## References

- [Plex Documentation](https://support.plex.tv/)
- [Tautulli Documentation](https://github.com/Tautulli/Tautulli)
- [LinuxServer.io Plex](https://docs.linuxserver.io/images/docker-plex)
- [LinuxServer.io Tautulli](https://docs.linuxserver.io/images/docker-tautulli)
- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
