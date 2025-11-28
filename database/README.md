# Database Stack

A Docker Compose stack providing essential database services for AI/ML and general application development.

## Services

### MongoDB (Port 27017)

- **Image**: `mongo:8.2-noble`
- **Purpose**: NoSQL document database
- **Auth**: Runs without authentication (internal network only)
- **Data**: Persisted to `${DATA_DIR}/mongo`

### pgvector (Port 5432)

- **Image**: `pgvector/pgvector:${PGVECTOR_TAG}`
- **Purpose**: PostgreSQL with vector similarity search extension
- **Config**: Max 200 connections
- **Data**: Persisted to `${DATA_DIR}/postgres`
- **Init Scripts**: Place SQL files in `${PROJ_DIR}/initdb.d/` for initialization

### Qdrant (Ports 6333, 6334)

- **Image**: `qdrant/qdrant:${QDRANT_TAG}`
- **Purpose**: Vector database for semantic search and AI applications
- **GPU**: NVIDIA GPU support enabled
- **Web UI**: Exposed via Traefik at `qdrant.${TRAEFIK_ACME_DOMAIN}`
- **Data**: Persisted to `${DATA_DIR}/qdrant`

## Configuration

### Environment Files

The stack uses multiple environment files for modular configuration:

| File                    | Purpose                               |
| ----------------------- | ------------------------------------- |
| `file.env`              | Base configuration and defaults       |
| `mongodb.env`           | MongoDB connection pool settings      |
| `pgvector.env`          | PostgreSQL database and user config   |
| `qdrant.env`            | Qdrant service ports and GPU settings |
| `compose.override.yaml` | secrets and overrides                 |

### Important Variables

#### Image Tags

```
PGVECTOR_TAG=pg18-trixie    # PostgreSQL + pgvector version
QDRANT_TAG=v1.15-gpu-nvidia # Qdrant with NVIDIA GPU support
```

#### System Configuration

```
UID=1000 # User ID for file permissions
GID=1000 # Group ID for file permissions
GPU_ID=0 # NVIDIA GPU device ID (0, 1, etc.)
```

#### Directory Paths

```
DATA_DIR=/srv/docker/database  # Persistent data storage location
PROJ_DIR=/srv/compose/database # Project directory (for init scripts)
```

#### Security

`POSTGRES_PASSWORD=user_provided   # PostgreSQL password (override in compose.override.yaml)`

#### Networking

`TRAEFIK_ACME_DOMAIN=mydomain.com  # Domain for Traefik reverse proxy`

## Overriding Configuration

For deployment-specific settings (secrets, production domains, GPU IDs, or even custom directories), create a `compose.override.yaml` file:

```compose.override.yaml (DO NOT COMMIT)
services:
  pgvector:
    environment:
      POSTGRES_PASSWORD: your_database_password_here
  qdrant:
    labels:
      - "traefik.http.routers.qdrant.rule=Host(`your_domain_name_here`)"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              # Use GPU 1 instead of default GPU 0
              device_ids: ['1']
              capabilities: [gpu]

```

Docker Compose automatically merges `compose.yaml` with `compose.override.yaml` at runtime.

## Usage

### Start the stack

`docker compose up -d`

### View logs

`docker compose logs -f [service_name]`

### Stop the stack

`docker compose down`

### Connect to databases

**PostgreSQL:**
`psql -h localhost -p 5432 -U postgres -d postgres`

**MongoDB:**
`mongosh mongodb://localhost:27017`

**Qdrant:**

- HTTP API: `http://localhost:6333`
- gRPC: `localhost:6334`
- Web UI: `https://qdrant.${TRAEFIK_ACME_DOMAIN}` (if Traefik configured)

## Network Configuration

- **database**: Internal network for database communication
- **proxy**: External network for Traefik integration (Qdrant only)

Both networks must be created before starting the stack:

```
docker network create database
docker network create proxy
```

## Data Persistence

All data is stored under `${DATA_DIR}`:

```
/srv/docker/database/
├── mongo/ # MongoDB data
├── postgres/ # PostgreSQL data
└── qdrant/ # Qdrant vector storage
```

## GPU Requirements

Qdrant is configured to use NVIDIA GPUs for accelerated indexing. Ensure:

1. NVIDIA drivers are installed on the host
2. [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) is installed
3. `GPU_ID` points to an available GPU (check with `nvidia-smi`)

## Auto-Start on Boot

To enable automatic startup after system reboot, use Docker's restart policy (already configured as `restart: on-failure:3`).

For systemd integration, create `/etc/systemd/system/database-stack.service`:

```
[Unit]
Description=Database Stack
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/srv/compose/database
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
```

Then enable:

```
sudo systemctl daemon-reload
sudo systemctl enable database-stack.service
```

## Troubleshooting

### Containers fail to start after reboot

- Ensure `compose.override.yaml` exists with correct values
- Check that Docker networks (`database`, `proxy`) exist
- Verify GPU availability with `nvidia-smi`

### Permission errors on data volumes

- Check that `UID` and `GID` in `file.env` match your user
- Verify data directory permissions: `chown -R 1000:1000 /srv/docker/database`

### PostgreSQL connection refused

- Wait 10-15 seconds for initialization on first start
- Check logs: `docker compose logs pgvector`
- Verify password in `compose.override.yaml` matches connection string

## Security Notes

⚠️ **Never commit `compose.override.yaml`** - it contains the password and other`.

⚠️ **MongoDB runs without authentication** - only expose on trusted networks.

⚠️ **PostgreSQL password** must be overridden in via `compose.override.yaml`.
