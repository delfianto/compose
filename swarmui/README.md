# SwarmUI Docker Setup

A containerized deployment of [SwarmUI](https://github.com/mcmonkeyprojects/SwarmUI) - a powerful web interface for Stable Diffusion image generation with ComfyUI backend support.

## 🚀 Quick Start

1. Clone this repository to your local machine
2. Create your `.env.local` file with machine-specific configurations
3. Run the deployment command:

```bash
docker compose --env-file .env --env-file .env.local up --force-recreate -d
```

## 📋 Prerequisites

- Docker Engine with Docker Compose support
- NVIDIA GPU with CUDA support (for GPU acceleration)
- NVIDIA Container Toolkit installed
- Sufficient disk space for models and generated images

## 🔧 Configuration

### Environment Files

This setup uses two environment files to separate general configuration from machine-specific settings:

#### `.env` (Included in repository)
Contains default SwarmUI configuration that should work for most users:

```env
SWARMUI_PORT=7801                     # Port where SwarmUI web interface will be accessible
SWARMUI_ROOT=/SwarmUI                 # Container's internal SwarmUI installation path
SWARMUI_EXTS=/SwarmUI/src/Extensions  # Extensions directory path
SWARMUI_COMF=/SwarmUI/src/BuiltinExtensions/ComfyUIBackend  # ComfyUI backend path
```

#### `.env.local` (Must be created manually)
Contains machine-specific configurations that vary per deployment:

```env
UID=1000                              # User ID for file permissions (run `id -u` to get yours)
GID=1000                              # Group ID for file permissions (run `id -g` to get yours)
DATA_DIR=/srv/stablediff              # Host path where models and outputs will be stored
SWARMUI_DATA=/srv/stablediff/swarmui        # Host path for SwarmUI configuration data
TRAEFIK_ACME_DOMAIN=my-awesome-domain.com   # Domain for Traefik reverse proxy
```

### Important Environment Variables

| Variable | Description | Location |
|----------|-------------|----------|
| `UID` | User ID for proper file permissions between host and container | `.env.local` |
| `GID` | Group ID for proper file permissions | `.env.local` |
| `DATA_DIR` | Base directory on host for all Stable Diffusion data | `.env.local` |
| `SWARMUI_DATA` | Directory for SwarmUI-specific configuration and data | `.env.local` |
| `SWARMUI_PORT` | Port where the web interface will be accessible | `.env` |
| `TRAEFIK_ACME_DOMAIN` | Domain name if using Traefik reverse proxy | `.env.local` |

## 📁 Directory Structure

After configuration, your host directories will be organized as follows:

```
${DATA_DIR}/
├── models/           # Stable Diffusion models (mapped to container's /SwarmUI/Models)
├── output/           # Generated images (mapped to container's /SwarmUI/Output)
└── swarmui/
    ├── Home/         # User home directory with settings
    ├── Data/         # SwarmUI application data
    ├── Back/         # Backend configurations
    ├── Exts/         # Custom extensions
    ├── Node/         # ComfyUI custom nodes
    └── Work/         # Custom ComfyUI workflows
```

## 🏃 Running the Container

### Start Command Explained

```bash
docker compose --env-file .env --env-file .env.local up --force-recreate -d
```

**Command breakdown:**
- `docker compose`: Invokes Docker Compose to manage multi-container applications
- `--env-file .env`: Loads the default environment variables
- `--env-file .env.local`: Loads your machine-specific variables (overrides defaults if duplicated)
- `up`: Creates and starts the containers
- `--force-recreate`: Forces recreation of containers even if configuration hasn't changed (ensures clean state)
- `-d`: Runs containers in detached mode (background)

### Other Useful Commands

```bash
# View logs
docker compose logs -f swarmui

# Stop the container
docker compose down

# Rebuild after Dockerfile changes
docker compose build --no-cache

# Check container status
docker compose ps
```

## 🌐 Accessing SwarmUI

Once running, SwarmUI will be accessible at:
- **Local access**: `http://localhost:7801`
- **With Traefik**: `https://swarmui.YOUR_DOMAIN` (replace with your `TRAEFIK_ACME_DOMAIN`)

## 🎯 Features

- **GPU Acceleration**: Full NVIDIA GPU support for fast image generation
- **ComfyUI Backend**: Integrated ComfyUI backend for advanced workflows
- **Persistent Storage**: All models, outputs, and configurations persist on the host
- **Security**: Runs with minimal privileges (drops all unnecessary capabilities)
- **Traefik Integration**: Ready for reverse proxy with automatic SSL certificates
- **Homepage Integration**: Includes labels for Homepage dashboard integration

## 🔒 Security Considerations

- The container runs with dropped capabilities for enhanced security
- User namespace isolation is enabled
- Runs as non-root user with specified UID/GID
- Ensure your `DATA_DIR` has appropriate permissions for the specified UID/GID

## 🐛 Troubleshooting

### Permission Issues
If you encounter permission errors, ensure your UID and GID in `.env.local` match your current user:
```bash
echo "UID=$(id -u)"
echo "GID=$(id -g)"
```

### GPU Not Detected
Verify NVIDIA Container Toolkit installation:
```bash
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

### Port Already in Use
Change `SWARMUI_PORT` in `.env` to an available port

### Storage Issues
Ensure the directories specified in `DATA_DIR` and `SWARMUI_DATA` exist and have proper permissions:
```bash
mkdir -p /srv/stablediff/{models,output,swarmui}
chown -R $(id -u):$(id -g) /srv/stablediff
```

## 📦 What's Included

- SwarmUI latest version from official repository
- Python 3.11 with required dependencies
- .NET SDK 8.0 runtime
- FFmpeg for video processing
- ComfyUI backend integration
- All necessary system libraries
