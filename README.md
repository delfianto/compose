# Docker Compose Orchestration Project

Welcome to this **comprehensive Docker Compose orchestration project** for self-hosted homelab infrastructure!

This repository provides a production-ready, modular collection of Docker Compose files and management tools for orchestrating a complete self-hosted environment including AI/ML services, media streaming, databases, and system management tools.

## What is This Project?

This is a **systemd-managed Docker Compose framework** designed to reliably orchestrate multiple interdependent containerized services. The project solves Docker's unreliable container auto-start mechanisms through proper dependency management and service orchestration.

### Key Services Included

- **Core Infrastructure**: Traefik reverse proxy with automatic SSL/TLS (Let's Encrypt), Portainer container management, Homepage dashboard
- **AI/ML Stack**: Ollama LLM inference, Open WebUI, LibreChat, Text Embedding services (HuggingFace TEI), SwarmUI (Stable Diffusion), RisuAI
- **Database Layer**: MongoDB, PostgreSQL with pgvector extension, Qdrant vector database
- **Media Services**: Plex Media Server with GPU transcoding, Tautulli analytics
- **Content Management**: StashApp for media indexing and metadata management

### Core Features

- **Systemd Integration**: Reliable service orchestration with proper dependency management
- **Modular Architecture**: Independent, reusable service stacks with clear separation of concerns
- **Network Isolation**: Multiple isolated Docker networks for security (proxy, database, genai, auth, metrics)
- **GPU Acceleration**: NVIDIA GPU support for AI inference, transcoding, and image generation
- **SSL/TLS**: Automatic certificate management via Traefik and Cloudflare DNS challenge
- **Persistent Storage**: Proper volume management for data persistence
- **Environment Management**: Flexible `.env` and `.env.local` configuration system

## Prerequisites

### Required Knowledge

**This project assumes you have at least a basic understanding of:**

- Linux command-line interface (CLI) operations
- Docker and Docker Compose fundamentals
- Basic networking concepts (ports, DNS, reverse proxies)
- Text editing in a terminal environment
- File permissions and system administration

### Platform Support

- **Tested on**: Linux (specifically tested on Arch Linux with kernel 6.17.9)
- **Untested on**: macOS and Windows
- **Requirements**:
    - Systemd-based Linux distribution
    - Docker Engine and Docker Compose V2
    - Python 3.6 or higher
    - Root/sudo access
    - (Optional) NVIDIA GPU with Container Toolkit for AI/ML acceleration

**Note**: While this project may work on macOS or Windows with appropriate modifications, it has not been tested on these platforms. The systemd integration is Linux-specific and would require alternative service management solutions on other operating systems.

## Getting Started

### Recommended Installation Method

**Use the helper script in the `systemd/` folder for proper system integration:**

1. **Clone the repository:**

    ```bash
    git clone https://github.com/delfianto/compose.git
    cd compose
    ```

2. **Install the systemd management framework:**

    ```bash
    cd systemd
    sudo python3 systemd.py install \
      --acme-domain yourdomain.com \
      --acme-email your@email.com
    ```

    This installs:
    - `/usr/local/bin/compose` - Enhanced Docker Compose wrapper
    - `/usr/local/bin/composectl` - Systemd service controller
    - `/etc/systemd/system/docker-compose@.service` - Systemd template unit
    - Global environment configuration

3. **Configure individual services:**

    ```bash
    cd /srv/compose/panel  # or any service directory
    cp .env .env.local     # Customize for your environment
    ```

4. **Start services with dependency management:**

    ```bash
    # Start core infrastructure
    sudo composectl start panel

    # Start databases
    sudo composectl start database

    # Start AI services (dependencies start automatically)
    sudo composectl start genai-ollama genai-open-webui
    ```

5. **Enable auto-start on boot:**
    ```bash
    sudo composectl enable panel database genai-ollama
    ```

### Manual Docker Compose Usage

If you prefer not to use the systemd integration:

```bash
cd panel  # or any service directory
docker compose up -d
```

**Note**: Docker does not actually provide dependency management or reliable auto-restart on system reboot. The systemd integration is strongly recommended for actual day to day use.

## Project Structure

```
/srv/compose/
├── systemd/              # System integration scripts (RECOMMENDED)
├── panel/                # Traefik, Portainer, Homepage
├── database/             # MongoDB, PostgreSQL, Qdrant
├── genai/                # AI/ML services (Ollama, WebUI, embeddings, etc.)
├── plex/                 # Plex Media Server, Tautulli
├── stash/                # StashApp content management
└── docker/               # Docker network and configuration files
```

## Security Notice

> **Never commit real secrets, API keys, or private keys to this repository!**
> Use `.env.local` or Docker secrets for sensitive data.

## Disclaimer

This project comes **without any warranty** of any kind.
By using this software, you accept all risks, including but not limited to:

- The Borg may invade your neighborhood.
- Your dog may suddenly hate you.
- Coffee may taste slightly more bitter.
- Spontaneous interpretive dance outbreaks are possible.
- The universe may collapse into a potato.

**I am not responsible for any of these (or other) outcomes. Use at your own risk!**

## License

See [LICENSE](LICENSE).
