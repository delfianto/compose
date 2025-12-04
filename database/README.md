# Database Stack

A comprehensive Docker Compose stack providing essential database services for AI/ML applications and general application development. This stack includes NoSQL document storage, SQL with vector search capabilities, and specialized vector databases for semantic search.

## What is This Stack?

This database stack provides the persistence layer for the compose orchestration project, specifically designed to support:

- **AI/ML Applications**: Vector databases for embeddings, semantic search, and RAG (Retrieval-Augmented Generation)
- **Chat Services**: Document storage for conversation history, user profiles, and application state
- **General Applications**: Traditional SQL and NoSQL database needs

## Services

### MongoDB (Port 27017)

- **Image**: `mongo:8.2-noble`
- **Purpose**: NoSQL document database for flexible schema storage
- **Authentication**: Configured with root username (password in `.env.local`)
- **Use Cases**: Chat history, user profiles, application configurations
- **Connection Pool**: Optimized for 10 concurrent connections with auto-indexing
- **Data Persistence**: `${DATA_DIR}/mongo`
- **Network**: Internal `database` network only

### pgvector (PostgreSQL with Vector Extension) (Port 5432)

- **Image**: `pgvector/pgvector:${PGVECTOR_TAG}` (PostgreSQL 18 + pgvector)
- **Purpose**: Relational database with vector similarity search extension for AI/ML
- **Configuration**: Maximum 200 concurrent connections
- **Use Cases**:
    - Structured data with ACID compliance
    - Vector embeddings storage and similarity search
    - Full-text search with PostgreSQL's built-in capabilities
    - Hybrid queries combining SQL and vector operations
- **Data Persistence**: `${DATA_DIR}/postgres`
- **Init Scripts**: SQL files in `${PROJ_DIR}/initdb.d/` run automatically on first startup
- **Network**: Internal `database` network only

### Qdrant (Vector Database) (Ports 6333, 6334)

- **Image**: `qdrant/qdrant:${QDRANT_TAG}` (v1.15 with NVIDIA GPU support)
- **Purpose**: Specialized vector database optimized for semantic search and AI applications
- **GPU Acceleration**: NVIDIA GPU support for accelerated indexing and search
- **Protocols**:
    - HTTP API on port 6333
    - gRPC API on port 6334
- **Web UI**: Accessible via Traefik reverse proxy at `qdrant.${TRAEFIK_ACME_DOMAIN}`
- **Use Cases**:
    - High-performance vector similarity search
    - Neural search applications
    - Recommendation systems
    - RAG (Retrieval-Augmented Generation) pipelines
- **Data Persistence**: `${DATA_DIR}/qdrant`
- **Networks**: Both `database` (internal) and `proxy` (Traefik) networks

## Prerequisites

### Required Knowledge

This stack assumes you understand:

- Basic database concepts (SQL, NoSQL, vector databases)
- Docker networking and volumes
- Linux file permissions
- Environment variable configuration

### Platform Support

- **Tested on**: Linux (Arch Linux with kernel 6.17.9)
- **Untested on**: macOS and Windows
- **Requirements**:
    - Docker Engine and Docker Compose V2
    - (Optional) NVIDIA GPU with Container Toolkit for Qdrant acceleration
    - Sufficient disk space for database storage

### Network Requirements

The following Docker networks must exist before starting this stack:

- `database` - Internal network for database communication
- `proxy` - External network for Traefik reverse proxy (Qdrant web UI)

If using the systemd installation method from the main compose project, these networks are created automatically. Otherwise, create them manually:

```bash
docker network create database
docker network create proxy
```

## Configuration

### Environment Files

The stack uses a modular environment file structure with base configuration and local overrides:

| File                     | Purpose                                    | Committed |
| ------------------------ | ------------------------------------------ | --------- |
| `env/mongodb.env`        | MongoDB connection pool settings           | Yes       |
| `env/mongodb.env.local`  | Local MongoDB overrides (password)         | No        |
| `env/pgvector.env`       | PostgreSQL database and user config        | Yes       |
| `env/pgvector.env.local` | Local PostgreSQL overrides (password)      | No        |
| `env/qdrant.env`         | Qdrant service ports and GPU settings      | Yes       |
| `env/qdrant.env.local`   | Local Qdrant overrides                     | No        |
| `compose.override.yaml`  | Deployment-specific overrides (not in git) | No        |

**Configuration Pattern**: Base `.env` files contain defaults and are committed to git. Local `.env.local` files contain secrets and machine-specific settings and are gitignored.

### Important Variables

#### Image Tags (from systemd global env or local override)

```bash
PGVECTOR_TAG=pg18-trixie     # PostgreSQL 18 + pgvector extension
QDRANT_TAG=v1.15-gpu-nvidia  # Qdrant with NVIDIA GPU support
```

#### System Configuration (from systemd global env)

```bash
UID=1000    # User ID for container file permissions
GID=1000    # Group ID for container file permissions
GPU_ID=0    # NVIDIA GPU device ID (0, 1, 2, etc.)
```

#### Directory Paths (from systemd global env)

```bash
DATA_DIR=/srv/appdata           # Persistent data storage base
PROJ_DIR=/srv/compose/database  # Project directory (for init scripts)
```

Actual data locations:

- MongoDB: `${DATA_DIR}/mongo`
- PostgreSQL: `${DATA_DIR}/postgres`
- Qdrant: `${DATA_DIR}/qdrant`

#### Security (in .env.local files)

```bash
# MongoDB (env/mongodb.env.local)
MONGO_INITDB_ROOT_PASSWORD=your_secure_password_here

# PostgreSQL (env/pgvector.env.local)
POSTGRES_PASSWORD=your_secure_password_here
```

#### Networking (from systemd global env)

```bash
TRAEFIK_ACME_DOMAIN=yourdomain.com  # Domain for Traefik reverse proxy (Qdrant web UI)
```

### MongoDB Configuration (env/mongodb.env)

```bash
MONGO_MAX_POOL_SIZE=10           # Maximum connection pool size
MONGO_MIN_POOL_SIZE=10           # Minimum connection pool size
MONGO_MAX_CONNECTING=10          # Max concurrent connections being established
MONGO_MAX_IDLE_TIME_MS=30000     # Connection idle timeout (30 seconds)
MONGO_WAIT_QUEUE_TIMEOUT_MS=10000 # Queue timeout for connections
MONGO_AUTO_INDEX=true            # Automatically create indexes
MONGO_AUTO_CREATE=true           # Automatically create databases
MONGO_INITDB_ROOT_USERNAME=mongo # Root username
```

### PostgreSQL Configuration (env/pgvector.env)

```bash
POSTGRES_DB=postgres    # Default database name
POSTGRES_USER=postgres  # Default username
# POSTGRES_PASSWORD set in env/pgvector.env.local
```

The PostgreSQL service is configured with:

- Maximum 200 concurrent connections
- pgvector extension pre-installed for vector operations
- Auto-initialization from SQL scripts in `initdb.d/`

### Qdrant Configuration (env/qdrant.env)

```bash
QDRANT__SERVICE__HTTP_PORT=6333  # HTTP API port
QDRANT__SERVICE__GRPC_PORT=6334  # gRPC API port
QDRANT__GPU__INDEXING=1          # Enable GPU-accelerated indexing
```

## Usage

### Recommended: Using Systemd Integration

If you've installed the systemd management framework from the main compose project:

```bash
# Start the database stack
sudo composectl start database

# Check status
composectl status database

# View logs
composectl logs database
composectl logs -f database  # Follow logs

# Stop the stack
sudo composectl stop database

# Enable auto-start on boot
sudo composectl enable database
```

### Using compose Helper (Standalone)

The `compose` helper script (installed at `/usr/local/bin/compose`) provides automatic environment file detection and sensible defaults:

```bash
# Navigate to database directory
cd /srv/compose/database

# Start all services (automatically detects .env and .env.local)
compose up

# Start specific service
compose up mongodb

# View logs (follows last 100 lines by default)
compose logs
compose logs pgvector  # Specific service

# Check running containers
compose ps

# Stop the stack (removes orphans and volumes)
compose down

# Stop without removing volumes
compose stop

# Restart services
compose restart
compose restart qdrant  # Specific service
```

### Connecting to Databases

**PostgreSQL:**

```bash
# Using psql
psql -h localhost -p 5432 -U postgres -d postgres

# Connection string
postgresql://postgres:your_password@localhost:5432/postgres
```

**MongoDB:**

```bash
# Using mongosh
mongosh mongodb://mongo:your_password@localhost:27017

# Connection string format
mongodb://mongo:your_password@localhost:27017/dbname
```

**Qdrant:**

- HTTP API: `http://localhost:6333`
- gRPC: `localhost:6334`
- Web UI: `https://qdrant.${TRAEFIK_ACME_DOMAIN}` (via Traefik)

**Python Example:**

```python
# Qdrant client
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)
```

## Data Persistence

All database data is persisted to the host filesystem under `${DATA_DIR}`:

```
/srv/appdata/  (or ${DATA_DIR})
├── mongo/         # MongoDB data files
├── postgres/      # PostgreSQL data files
└── qdrant/        # Qdrant vector storage
```

**Backup Recommendations:**

- MongoDB: Use `mongodump` for logical backups
- PostgreSQL: Use `pg_dump` or `pg_basebackup`
- Qdrant: Backup the entire `${DATA_DIR}/qdrant` directory

## GPU Support

Qdrant is configured with NVIDIA GPU acceleration for faster vector indexing and search operations.

**Requirements:**

1. NVIDIA GPU with compute capability 6.0+ (Pascal or newer)
2. NVIDIA drivers installed on the host
3. [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed
4. `GPU_ID` environment variable set to available GPU (check with `nvidia-smi`)

**Verify GPU access:**

```bash
# Check GPU availability
nvidia-smi

# Verify Docker can access GPU
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

## Troubleshooting

### Containers fail to start after reboot

**Symptoms**: Services don't start automatically after system reboot

**Solutions**:

- If using systemd integration: `sudo composectl enable database`
- Verify Docker networks exist: `docker network ls | grep -E 'database|proxy'`
- Check Qdrant GPU access: `nvidia-smi`

### Permission errors on data volumes

**Symptoms**: "Permission denied" errors in container logs

**Solutions**:

- Verify `UID` and `GID` match your user: `id`
- Fix data directory permissions: `sudo chown -R 1000:1000 ${DATA_DIR}`
- Check that user namespaces are not conflicting

### PostgreSQL connection refused

**Symptoms**: "Connection refused" or "FATAL: password authentication failed"

**Solutions using compose helper**:

```bash
cd /srv/compose/database

# Wait 10-15 seconds for initialization on first start
sleep 15

# Check logs
compose logs pgvector

# Verify container is running
compose ps
```

**Solutions using composectl**:

```bash
# Check service status
composectl status database

# View logs
composectl logs database

# Restart if needed
sudo composectl restart database
```

Additional checks:

- Verify password in `env/pgvector.env.local` matches connection attempts
- Ensure PostgreSQL container is running: `compose ps | grep pgvector`

### MongoDB authentication failed

**Symptoms**: "Authentication failed" when connecting

**Solutions**:

```bash
# Check logs
compose logs mongodb

# Verify password in env/mongodb.env.local
cat env/mongodb.env.local

# Wait for MongoDB initialization (first start takes longer)
# Then try connecting again
```

- Use correct username (`mongo` by default)
- Check that `MONGO_INITDB_ROOT_PASSWORD` is set

### Qdrant GPU not detected

**Symptoms**: Qdrant falls back to CPU, slower performance

**Solutions**:

```bash
# Check Qdrant logs
compose logs qdrant

# Verify NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# Check GPU_ID environment variable
echo $GPU_ID

# Verify GPU availability
nvidia-smi
```

### Init scripts not running (PostgreSQL)

**Symptoms**: Expected tables/databases not created

**Solutions**:

- Place SQL files in `${PROJ_DIR}/initdb.d/` directory
- Init scripts only run on first startup (empty data volume)
- !WARNING! the following command will remove any existing postgres data
- To re-run:
    ```bash
    cd /srv/compose/database
    compose down
    sudo rm -rf ${DATA_DIR}/postgres
    compose up
    ```

## Quick Reference

### Common Commands (with compose helper)

```bash
cd /srv/compose/database

# Start everything
compose up

# Start specific service
compose up mongodb

# View all logs
compose logs

# View specific service logs
compose logs -f pgvector

# Check status
compose ps

# Stop everything
compose down

# Restart service
compose restart qdrant
```

### Common Commands (with composectl)

```bash
# Start/stop/restart
sudo composectl start database
sudo composectl stop database
sudo composectl restart database

# Status and logs
composectl status database
composectl logs database
composectl logs -f database

# Enable/disable auto-start
sudo composectl enable database
sudo composectl disable database
```

### Connection Strings

```bash
# PostgreSQL
postgresql://postgres:PASSWORD@localhost:5432/postgres

# MongoDB
mongodb://mongo:PASSWORD@localhost:27017/

# Qdrant HTTP
http://localhost:6333

# Qdrant gRPC
localhost:6334
```
