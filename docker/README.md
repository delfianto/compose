# Docker Configuration

This directory contains Docker configuration files and custom CLI plugins to enhance Docker functionality for this project.

## Directory Structure

```
docker/
├── cli-plugins/          # Custom Docker CLI plugins
│   ├── cli_helper.py     # Common utilities for plugins
│   ├── docker-img        # Image listing tool
│   ├── docker-imu        # Image update tool
│   ├── docker-nbs        # Network bootstrap tool
│   ├── docker-pps        # Pretty container status tool
│   └── docker-smi        # NVIDIA GPU checker
├── system/               # System-level configuration
│   ├── daemon.json       # Docker daemon configuration
│   ├── subgid            # Group ID mappings
│   └── subuid            # User ID mappings
├── config.json           # Docker client configuration
└── networks.toml         # Network definitions
```

## Configuration Files

### config.json

Docker client configuration that customizes output formats:

- **psFormat**: Table format for `docker ps` showing Names, Status, and Ports
- **imagesFormat**: Table format for `docker images` showing ID, Size, Repository, and Tag

### networks.toml

Defines isolated Docker networks for different service categories:

| Network  | Subnet        | Gateway    | Purpose                          | Internal |
| -------- | ------------- | ---------- | -------------------------------- | -------- |
| proxy    | 172.20.0.0/24 | 172.20.0.1 | Internet-facing services/Traefik | No       |
| metrics  | 172.21.0.0/24 | 172.21.0.1 | Monitoring stack                 | Yes      |
| database | 172.22.0.0/24 | 172.22.0.1 | Data persistence layer           | Yes      |
| genai    | 172.23.0.0/24 | 172.23.0.1 | AI/ML services                   | Yes      |
| auth     | 172.24.0.0/24 | 172.24.0.1 | Authentication services          | Yes      |

Use `docker nbs` to bootstrap these networks from the configuration file.

### system/daemon.json

Docker daemon configuration with:

- **NVIDIA Runtime**: Default runtime set to `nvidia` for GPU support
- **User Namespace Remapping**: Security feature mapping container users to host user `mipan`
- **IPv6**: Disabled

### system/subuid & system/subgid

User and group namespace mappings for Docker security isolation. Maps container UIDs/GIDs to unprivileged host ranges.

## Custom CLI Plugins

All plugins are Python-based and extend the Docker CLI with additional functionality.

### docker nbs (Network Bootstrap)

Bootstrap Docker networks from the `networks.toml` configuration file.

**Usage:**

```bash
# Create networks from default config
docker nbs

# Use custom config file
docker nbs -f /path/to/networks.toml

# Dry run (show what would be created)
docker nbs --dry-run
```

**Features:**

- Creates networks with custom subnets, gateways, and labels
- Handles existing networks gracefully
- Supports internal/external network configuration
- Shows summary with labeled networks

### docker img (Image List)

List Docker images grouped by registry and repository for better organization.

**Usage:**

```bash
docker img
```

**Output:**

```
docker.io
=========
  nginx:
    abc123def456  50MB       latest
    xyz789abc012  52MB       alpine

ghcr.io
=======
  user/project:
    def456ghi789  120MB      v1.0.0
```

### docker imu (Image Update)

Pull updates for all local Docker images with parallel or sequential processing.

**Usage:**

```bash
# Update all images sequentially
docker imu

# Update in parallel (4 workers)
docker imu --parallel

# Update with custom worker count
docker imu --parallel --workers 8

# Filter images by name
docker imu --filter nginx

# Dry run
docker imu --dry-run
```

**Features:**

- Parallel or sequential image pulls
- Configurable worker count
- Image name filtering
- Progress tracking with colored output
- Summary statistics (updated/unchanged/failed)

### docker pps (Pretty PS)

Enhanced `docker ps` with brief and verbose output formats.

**Usage:**

```bash
# Brief table format (default)
docker pps
docker pps --brief

# Verbose detailed format for all containers
docker pps --verbose
docker pps -v

# Verbose format for specific container
docker pps -v mycontainer

# Show only running containers
docker pps --running
```

**Verbose Format Shows:**

- Container name, ID, image, status
- Full command (Cmd or Entrypoint)
- Creation time and uptime
- Ports and networks
- Size and mounts
- All labels (with formatted JSON values)

### docker smi (System Management Interface)

Check NVIDIA GPU availability and configuration for Docker containers.

**Usage:**

```bash
docker smi
```

**Checks:**

1. Docker daemon accessibility
2. NVIDIA Container Toolkit installation
3. GPU availability by running `nvidia-smi` in a test container

**Useful For:**

- Verifying GPU setup after installation
- Troubleshooting GPU access issues
- Testing NVIDIA runtime configuration

## Installation

### Install CLI Plugins

1. Copy plugins to Docker's plugin directory:

```bash
# System-wide (requires sudo)
sudo cp cli-plugins/* ~/.docker/cli-plugins/

# Or for current user only
mkdir -p ~/.docker/cli-plugins
cp cli-plugins/* ~/.docker/cli-plugins/
```

2. Make plugins executable:

```bash
chmod +x ~/.docker/cli-plugins/docker-*
```

3. Verify installation:

```bash
docker --help
# You should see the custom plugins listed
```

### Apply Docker Configuration

1. **Client Configuration:**

```bash
cp config.json ~/.docker/config.json
```

2. **Daemon Configuration** (requires sudo):

```bash
sudo cp system/daemon.json /etc/docker/daemon.json
sudo systemctl restart docker
```

3. **User Namespace Mappings** (if using userns-remap):

```bash
sudo cp system/subuid /etc/subuid
sudo cp system/subgid /etc/subgid
```

### Bootstrap Networks

After installing the `docker-nbs` plugin:

```bash
cd /srv/compose/docker
docker nbs -f networks.toml
```

## Requirements

- Python 3.11+ (for CLI plugins)
- Docker Engine 20.10+
- NVIDIA Container Toolkit (for GPU support)
- Python packages: `tomllib` (built-in for Python 3.11+)

## Security Considerations

- **User Namespace Remapping**: Containers run as unprivileged users on the host
- **Internal Networks**: Most networks are isolated from external access
- **Subnet Isolation**: Each service category has its own subnet range

## Troubleshooting

### Plugin Not Found

If custom plugins don't appear in `docker --help`:

1. Ensure plugins are in `~/.docker/cli-plugins/`
2. Verify files are executable (`chmod +x`)
3. Check file names start with `docker-`

### NVIDIA GPU Not Detected

Run `docker smi` for diagnostics. Common issues:

- NVIDIA drivers not installed on host
- NVIDIA Container Toolkit not configured
- Docker daemon needs restart: `sudo systemctl restart docker`

### Network Already Exists

When running `docker nbs`, if networks already exist:

- Plugin will skip existing networks and show warning
- Use `docker network rm <network>` to recreate
- Or modify `networks.toml` and run again
