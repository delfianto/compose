# Docker Compose Orchestration Project

Welcome to this **comprehensive Docker Compose orchestration project** for self-hosted homelab infrastructure!

This repository provides a production-ready, modular collection of Docker Compose files and management tools for orchestrating a complete self-hosted environment including AI/ML services, media streaming, databases, and system management tools.

## What is This Project?

This is a **systemd-managed Docker Compose framework** designed to reliably orchestrate multiple interdependent containerized services. The project solves Docker's unreliable container auto-start mechanisms through proper dependency management and service orchestration.

### Key Services Included

- **Core Infrastructure**: Traefik reverse proxy with automatic SSL/TLS (Let's Encrypt), Portainer container management, Homepage dashboard
- **AI/ML Stack**: Ollama LLM inference, Open WebUI, LibreChat, Text Embedding services (HuggingFace TEI), SwarmUI (Stable Diffusion), RisuAI
- **Database Layer**: MongoDB, PostgreSQL with pgvector extension, Qdrant vector database
- **Media Services**: StashApp, Plex Media Server with GPU transcoding, Tautulli analytics

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

### IMPORTANT: Read the Utils Directory README First

**Before proceeding, read [utils/README.md](utils/README.md) for comprehensive installation and usage documentation.**

The utils directory contains the systemd integration framework that is **essential** for proper operation of this project. It provides reliable service orchestration, dependency management, and automatic environment file handling.

### Recommended Installation Method

**Use the helper script in the `utils/` folder for proper system integration:**

1. **Clone the repository:**

    ```bash
    git clone https://github.com/delfianto/compose.git
    cd compose
    ```

2. **Install the systemd management framework:**

    ```bash
    cd utils
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

### Manual Docker Compose Usage (NOT RECOMMENDED)

**Warning: Manual `docker compose` usage is NOT recommended and should be avoided.**

While technically possible, using `docker compose` directly is:

- **Tedious**: Requires specifying multiple `--env-file` arguments for every command
- **Error-Prone**: Easy to forget `.env.local` files containing critical secrets
- **Inconsistent**: No standardized defaults across different services
- **Unreliable**: No dependency management or reliable auto-restart on reboot
- **Fragile**: Manual tracking of which env files to include for each service

**Example of what you'd have to type manually:**

```bash
cd /srv/compose/database
docker compose --env-file .env --env-file .env.local up -d --remove-orphans
docker compose --env-file .env --env-file .env.local logs -f --tail=100
docker compose --env-file .env --env-file .env.local down --remove-orphans --volumes
# Repeat for EVERY service, EVERY time...
```

**With projects having multiple `.env` files** (root `.env`, `.env.local`, `env/service.env`, `env/service.env.local`), manual management becomes extremely error-prone. Forgetting even one file can lead to containers starting with wrong configurations or missing critical environment variables.

**Instead, use the installed tools:**

```bash
cd /srv/compose/database
compose up      # Automatically handles all .env files
compose logs    # Sensible defaults
compose down    # Consistent cleanup
```

**Or use systemd integration:**

```bash
sudo composectl start database   # Handles everything automatically
```

**Bottom line**: The systemd integration and compose helper are **essential tools** that make operating with the compose project a lot more simple and easy. Manual docker compose commands defeats the purpose of this orchestration framework (unless one love to type long commands).

### Domain Name and TLS Requirement

**This project assumes you own a domain name for TLS termination.**

#### Why a Domain Name is Required

This project uses **Traefik** as a reverse proxy with automatic SSL/TLS certificate management via Let's Encrypt. This architecture provides:

- **Secure HTTPS access** to all web services (Open WebUI, Qdrant, Portainer, etc.)
- **Automatic certificate renewal** - no manual certificate management
- **Centralized access point** - single domain with service-specific subdomains
- **Professional homelab setup** - proper encryption even for internal services

#### Homelab Deployment Scenario (Recommended)

For homelab deployments, the recommended approach is:

1. **Own a domain name** (e.g., `mydomain.com` from any registrar)
2. **Use Cloudflare DNS** (free tier is sufficient)
3. **Configure Traefik with Cloudflare DNS challenge** for automatic Let's Encrypt certificates
4. **Access services via subdomains**:
    - `https://webui.mydomain.com` - Open WebUI
    - `https://qdrant.mydomain.com` - Qdrant vector database
    - `https://portainer.mydomain.com` - Container management
    - `https://traefik.mydomain.com` - Traefik dashboard

**Benefits of DNS Challenge with Cloudflare:**

- No need to expose ports 80/443 to the internet
- Works behind NAT/firewall (perfect for homelabs)
- Wildcard certificates supported
- Private homelab with valid SSL certificates

#### Getting Started with Cloudflare ACME

**Step 1: Register Domain and Set Up Cloudflare**

1. Register a domain name at any registrar (Namecheap, Google Domains, etc.)
2. Create a free [Cloudflare account](https://www.cloudflare.com/)
3. Add your domain to Cloudflare and update nameservers at your registrar
4. Wait for DNS propagation (usually 24-48 hours)

**Step 2: Create Cloudflare API Token**

1. Go to Cloudflare Dashboard → Profile → API Tokens
2. Click "Create Token"
3. Use "Edit zone DNS" template
4. Configure:
    - **Permissions**: Zone → DNS → Edit
    - **Zone Resources**: Include → Specific zone → your domain
5. Create token and **save it securely** (shown only once)

**Step 3: Configure This Project**

```bash
# Store Cloudflare token in secret file (gitignored)
cd /srv/compose/panel
echo "your_cloudflare_api_token_here" > secret/cf_dns.secret
chmod 600 secret/cf_dns.secret

# Install with your domain
cd /srv/compose/utils
sudo python3 systemd.py install \
  --acme-domain yourdomain.com \
  --acme-email your@email.com
```

**Recommended Guides:**

- **Cloudflare DNS Setup**: [Cloudflare - Add a Site](https://developers.cloudflare.com/fundamentals/setup/account-setup/add-site/)
- **API Token Creation**: [Cloudflare - API Tokens](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)
- **Traefik + Cloudflare**: [Traefik Cloudflare DNS Challenge](https://doc.traefik.io/traefik/https/acme/#dnschallenge)
- **Let's Encrypt DNS Challenge**: [Let's Encrypt DNS Validation](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge)

#### Alternative: Local Development Without Domain

If you're testing locally without a domain, you can:

1. **Use HTTP only** (not recommended for production)
2. **Use self-signed certificates** (browser warnings)
3. **Access services via localhost:port** (no reverse proxy)

However, the Traefik + Cloudflare approach is **strongly recommended** even for homelab use, as it provides production-grade security without exposing your homelab to the internet.

## Environment Configuration System

This project uses a multi-layered environment configuration system to separate concerns between shell interpolation, container environment variables, and deployment-specific secrets.

### Understanding .env vs env/\*.env Files

The project uses **two different patterns** for environment configuration:

#### 1. Root-level .env File (Shell Interpolation)

**Location**: `.env` in the project root (e.g., `/srv/compose/database/.env`)

**Purpose**: Variables used for **shell interpolation** in `compose.yaml` files

**When it's read**: By Docker Compose **before** parsing the YAML file

**Example**:

```yaml
# compose.yaml
services:
    mongodb:
        volumes:
            - ${DATA_DIR}/mongo:/data/db # ${DATA_DIR} replaced during YAML parsing
```

These variables are used to **interpolate values into the compose.yaml** file itself. They are **NOT** passed into containers as environment variables unless explicitly defined in `environment:` or `env_file:` sections.

#### 2. env/\*.env Files (Container Environment Variables)

**Location**: `env/service.env` files in subdirectories (e.g., `/srv/compose/database/env/mongodb.env`)

**Purpose**: Variables passed **into the container** as environment variables

**When it's read**: After compose.yaml is parsed, loaded into the container at runtime

**Example**:

```yaml
# compose.yaml
services:
    mongodb:
        env_file:
            - ./env/mongodb.env # Variables loaded INTO the container
            - ./env/mongodb.env.local
```

These variables become **actual environment variables inside the running container**, accessible to the application.

### Shell Interpolation vs Container Environment Variables

Understanding the difference is critical:

```yaml
services:
    pgvector:
        image: pgvector/pgvector:${PGVECTOR_TAG} # ← Shell interpolation (.env)
        env_file:
            - ./env/pgvector.env # ← Container environment (env/*.env)
        environment:
            POSTGRES_DB: ${POSTGRES_DB} # ← Both! Interpolated THEN set in container
        volumes:
            - ${DATA_DIR}/postgres:/var/lib/postgresql # ← Shell interpolation only
```

**Shell Interpolation** (from `.env`):

- Happens **before** Docker Compose processes the YAML
- Used for: image tags, volume paths, port mappings, network names
- Variables are **not** visible inside containers unless explicitly passed
- Example: `${DATA_DIR}`, `${UID}`, `${GPU_ID}`

**Container Environment Variables** (from `env_file:`):

- Loaded **into the container** at runtime
- Used by: the application running inside the container
- Not used for compose.yaml structure
- Example: `POSTGRES_DB`, `MONGO_MAX_POOL_SIZE`, `QDRANT__SERVICE__HTTP_PORT`

### The .local Override Pattern

The project uses `.local` files for machine-specific overrides and secrets:

#### Base Configuration (Committed to Git)

```bash
# .env (root level - shell interpolation)
DATA_DIR=/srv/appdata
UID=1000
GID=1000

# env/pgvector.env (container environment)
POSTGRES_DB=postgres
POSTGRES_USER=postgres
```

#### Local Overrides (NOT Committed - Gitignored)

```bash
# .env.local (optional - shell interpolation overrides)
DATA_DIR=/mnt/storage/appdata
GPU_ID=1

# env/pgvector.env.local (container environment - secrets!)
POSTGRES_PASSWORD=super_secret_password_here
```

**How Docker Compose Merges Them**:

1. **Shell Interpolation** (`.env` files):
    - Reads `.env` first
    - Reads `.env.local` second (overrides `.env` values)
    - Interpolates variables into compose.yaml

2. **Container Environment** (`env_file:`):

    ```yaml
    env_file:
        - ./env/service.env # Base configuration
        - ./env/service.env.local # Overrides and secrets
    ```

    - Files listed later override earlier values
    - Both files loaded into container
    - Last value wins for duplicate keys

**Why This Pattern?**

- **Separation of Secrets**: Base config in git, secrets in `.local` files (gitignored)
- **Machine-Specific Settings**: Different paths, GPU IDs, domains per deployment
- **Team Collaboration**: Share base config, customize locally
- **Security**: Never commit passwords, API keys, or tokens

### Environment Variable Precedence

Docker Compose loads environment variables in this order (last wins):

1. `.env` file (root level - shell interpolation)
2. `.env.local` file (root level overrides)
3. `env_file:` entries in compose.yaml (container environment)
4. `environment:` section in compose.yaml (container environment)
5. Command-line `-e` flags (highest priority)

**Example**:

```bash
# .env
DATA_DIR=/srv/appdata

# .env.local
DATA_DIR=/mnt/storage  # ← Wins for shell interpolation

# env/service.env
APP_DEBUG=false

# env/service.env.local
APP_DEBUG=true  # ← Wins for container environment

# Command line (highest priority)
docker compose -e APP_DEBUG=false up  # ← Overrides everything
```

### Best Practices

1. **Use .env for structure**: Paths, image tags, UIDs/GIDs, GPU IDs
2. **Use env/\*.env for app config**: Application-specific settings without secrets
3. **Use .env.local for secrets**: Passwords, API keys, tokens
4. **Never commit .local files**: Ensure `.gitignore` includes `*.local`
5. **Use compose helper**: Install systemd integration for automatic env file handling
6. **Document required variables**: Add `.env.example` showing required keys (without values)

### Troubleshooting Environment Issues

**Problem**: "Variable not set" error in compose.yaml

```bash
# Solution: Add to .env or .env.local (shell interpolation)
echo "MISSING_VAR=value" >> .env.local
```

**Problem**: Application complains about missing environment variable

```bash
# Solution: Add to env/service.env.local (container environment)
echo "APP_CONFIG=value" >> env/service.env.local
```

**Problem**: Changes not reflected after editing .env

```bash
# Solution: Recreate containers (Docker Compose caches)
compose down
compose up
```

**Problem**: Don't know which file to edit

```bash
# Check where variable is used:
grep -r "VARIABLE_NAME" compose.yaml env/

# If in compose.yaml structure → .env or .env.local
# If in env_file: list → env/*.env or env/*.env.local
```

## Project Structure

```
/srv/compose/
├── utils/                # System integration scripts (RECOMMENDED)
├── panel/                # Traefik, Portainer, Homepage
├── database/             # MongoDB, PostgreSQL, Qdrant
├── genai/                # AI/ML services (Ollama, WebUI, embeddings, etc.)
├── plex/                 # Plex Media Server, Tautulli
├── stash/                # StashApp content server
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
