# Self-Hosted LLM Stack

This project provides a complete, self-hosted Large Language Model (LLM) stack using Docker Compose. It leverages a powerful local hardware setup for private and GPU-accelerated AI and seamlessly integrates with various cloud LLM providers.

Do note that this setup is intended for users with a good understanding of Docker, Docker Compose, and basic Linux command-line operations. This guide assumes you have a compatible GPU and sufficient VRAM to run local models and that you are comfortable managing Docker containers.

This project is not tested on Apple Silicon hardware or Windows system, it is primarily designed for Linux system running on x86_64 architecture with NVIDIA GPUs.

### Key Components

  * **Traefik**: Serves as a reverse proxy, handling all incoming web traffic, automatic HTTPS/SSL certificate management (via Let's Encrypt and Cloudflare DNS challenge), and routing traffic to the correct services.
  * **PostgreSQL with `pgvector`**: A robust, persistent database for both Open WebUI and LiteLLM. The `pgvector` extension enables Retrieval-Augmented Generation (RAG) for local document analysis.
  * **Ollama**: A self-hosted service for running and managing local LLMs. It is configured to utilize your GPU for accelerated inference.
  * **LiteLLM**: An intelligent proxy that abstracts cloud LLM APIs. It provides a single interface to manage both local models (from Ollama) and various cloud providers (e.g., OpenAI, Anthropic, Google).
  * **Open WebUI**: A user-friendly, web-based interface for interacting with your LLMs. It uses LiteLLM as a backend to give you a unified chat experience with all your models.

### Prerequisites

  * **Sufficient Hardware**: A machine with a capable GPU (e.g., NVIDIA RTX 4000 series) and enough VRAM to run the models you intend to use.
  * **NVIDIA Drivers**: The `ollama.yml` service is configured to use your NVIDIA GPU. Ensure the `nvidia-container-toolkit` and appropriate drivers are installed on your machine.
  * **Docker & Docker Compose**: Ensure you have Docker and Docker Compose installed. Your `docker compose` version should support the `include` directive.
  * **Persistent Storage**: A dedicated disk or partition for storing Docker volumes, databases, and model data. Update the `DATA_DIR` variable in the `.env.local` file to point to this location.
  * **Cloud LLM API Keys**: If you plan to use cloud LLMs via LiteLLM, obtain API keys from providers like OpenAI, Anthropic, and Google Gemini.

### Special Requirements for Traefik

  * **Docker Network**: On the compose file Traefik requires a dedicated Docker network named `proxy`
  * **Cloudflare Account**: For Traefik's DNS Challenge, a Cloudflare account and DNS API token are required to manage DNS records automatically.
  * **Domain Name**: A domain name (e.g., `foo.app`) with its DNS records pointed to your server's public IP address.
  * Refer to the documentation of the portainer project inside this repo for detailed instructions on setting up Traefik with Cloudflare DNS challenge.

### Project Structure

Your project directory should be structured as follows:

```
/home/vexel/projects/compose/local-llm/
├── compose.yml
├── litellm.yml
├── ollama.yml
├── openwebui.yml
├── postgres.yml
├── .env.local
└── initdb.d/
    └── postgresql-init.sh
```

### Configuration

All custom and sensitive configuration variables are stored in the `.env.local` file. You must fill this out before deploying.

#### `.env.local`

This file contains sensitive information like API keys and passwords. **Do not commit this file to a public repository.**

```ini
# .env.local
# Root directory for all persistent data
DATA_DIR=/mnt/your_disk/containers

# Project directory to correctly map the init script
PROJ_DIR=/home/vexel/projects/compose/local-llm

# Traefik domain and email for Let's Encrypt certificates
TRAEFIK_ACME_DOMAIN=mydomain.com
TRAEFIK_ACME_EMAIL=admin@mydomain.com

# LiteLLM and PostgreSQL credentials
LITELLM_SALT_KEY=Pxx-your-salt-key-xxP
LITELLM_MASTER_KEY=Pxx-your-master-key-xxP
POSTGRES_PASSWORD=Pxx-your-db-password-xxP

# Cloud LLM API keys
# Fill these in with your own keys
ANTHROPIC_API_KEY=sk-ant-***
OPENAI_API_KEY=sk-proj-***
GEMINI_API_KEY=AI-***
```

#### Initialization Script (`initdb.d/postgresql-init.sh`)

This script is crucial for automating the database setup for Open WebUI and LiteLLM. It is executed automatically by the PostgreSQL container on its first start with an empty data volume. It creates the necessary users and databases and enables the `pgvector` extension.

```bash
#!/bin/bash
set -e

# These are the environment variables passed to the container
POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"
POSTGRES_USER="${POSTGRES_USER}"
POSTGRES_DB="${POSTGRES_DB}"

# The psql command will connect via Unix-domain socket
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE USER openwebui WITH PASSWORD '$POSTGRES_PASSWORD';"
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE DATABASE openwebui OWNER openwebui;"
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "GRANT ALL PRIVILEGES ON DATABASE openwebui TO openwebui;"

# Create a new user and database for LiteLLM
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE USER litellm WITH PASSWORD '$POSTGRES_PASSWORD';"
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE DATABASE litellm OWNER litellm;"
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "GRANT ALL PRIVILEGES ON DATABASE litellm TO litellm;"

# Connect to the new database and enable the vector extension for Open WebUI
psql -U "$POSTGRES_USER" -d "openwebui" -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

-----

### Deployment

1.  **Configure Environment Variables**: Create a `.env.local` file in your project root and fill in the values as shown above.

2.  **Run Docker Compose**: From your project root directory, run the following command to bring up the entire stack.

    ```bash
    docker compose --env-file .env.local up -d
    ```

    On the first run, this will:

      * Pull all necessary Docker images.
      * Create a Docker network named `proxy`.
      * Initialize the PostgreSQL database using the `postgresql-init.sh` script.
      * Set up all services and configure Traefik for automatic SSL.

### Post-Deployment & Usage

Once all containers are up and running, you can access your services via the following URLs:

  * **Open WebUI**: `https://webui.mydomain.com`
  * **LiteLLM**: `https://litellm.mydomain.com`
  * **Ollama**: `https://ollama.mydomain.com`

### Troubleshooting

If you encounter issues, here are some basic troubleshooting steps:

  * **Containers not starting**: Check the container logs for errors.
    ```bash
    docker logs <container-name>
    ```
  * **Traefik is not routing traffic**: Check the Traefik dashboard for the status of your routers and services.
      * Make sure your DNS records for `*.mydomain.com` are correctly pointed to your server's IP.
      * Check the Traefik logs for certificate resolution errors.
    ```bash
    docker logs traefik
    ```
