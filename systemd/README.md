# Docker Compose Systemd Manager

A reliable systemd-based management system for Docker Compose projects that solves the notorious unreliability of Docker's built-in container auto-start mechanisms.

## The Problem: Why Docker Auto-Start is Unreliable

Docker's built-in restart policies (`restart: always`, `restart: unless-stopped`) suffer from several fundamental issues that make them unsuitable for actual deployments:

### 1. Race Conditions at Boot

Docker starts containers in parallel without understanding dependencies. When your system reboots:

- Database containers may not be fully initialized when application containers start
- Networks might not be ready when containers try to bind to them
- Services fail health checks because their dependencies aren't available yet

### 2. No Dependency Management

Docker has no reliable way to manage service startup order. The `depends_on` directive in docker-compose only ensures containers _start_ in order, not that services are _ready_.

### 3. Restart Policy Inconsistencies

The `always` restart policy is frequently ignored or behaves unpredictably:

- May not work after host reboots (only after `systemctl restart docker`)
- Often fails after 3-4 successive reboots for unexplained reasons
- Restart limits can cause containers to give up and remain stopped

### 4. Unhealthy State Handling

Docker doesn't automatically restart unhealthy containers by default. Health checks are purely diagnostic—containers can sit in an unhealthy state indefinitely without intervention.

### 5. Single Point of Failure

All containers depend on the Docker daemon. If the daemon crashes, hangs, or requires an update, all containers stop. Systemd, by contrast, runs services directly under its supervision with automatic recovery.

## The Solution: Systemd-Managed Compose Projects

This toolkit leverages systemd's battle-tested service management to provide:

- ✅ **Explicit dependency chains** - Define which services must start before others
- ✅ **Proper startup ordering** - Services wait for dependencies to be fully ready
- ✅ **Reliable restart behavior** - Systemd's proven restart mechanisms
- ✅ **Fine-grained control** - Different restart policies per service
- ✅ **Better logging** - Integration with journalctl for centralized logs
- ✅ **Socket activation support** - Start services on-demand

## Components

### 1. compose.py - Enhanced Docker Compose Wrapper

A Python wrapper around `docker compose` that provides:

- Automatic environment file discovery
- Sensible default flags for common commands
- Support for hyphenated project names (e.g., `genai-ollama` → `genai/ollama`)
- Transparent command execution with full visibility

```bash
# Usage examples
compose.py up      # Start with sensible defaults
compose.py logs    # Follow last 100 log lines
compose.py ps      # Pretty table format
compose.py down    # Clean shutdown with volume removal
```

### 2. docker-compose@.service - Systemd Template Unit

A systemd template that creates service instances for each compose project. Features:

- Template-based instantiation (one unit file, multiple instances)
- Automatic environment loading
- Project name resolution via `COMPOSE_PROJECT` variable
- 5-minute startup timeout for complex stacks
- Restart on failure with 10-second delay

### 3. compose-systemd.py - Management Tool

Central management utility for installation and dependency configuration:

#### Installation

```bash
sudo ./compose-systemd.py --install \
  --acme-domain example.com \
  --acme-email admin@example.com
```

#### Dependency Management

```bash
# Add hard dependency (service won't start if dependency fails)
sudo ./compose-systemd.py deps add genai-open-webui database requires

# Add soft dependency (service starts even if dependency fails)
sudo ./compose-systemd.py deps add genai-embedding genai-ollama wants

# List dependencies
./compose-systemd.py deps list genai-open-webui

# Check full dependency chain
./compose-systemd.py deps check genai-open-webui

# Remove dependency
sudo ./compose-systemd.py deps remove genai-open-webui database
```

#### Status Checking

```bash
./compose-systemd.py --check-status
```

### 4. docker-compose.env.template - Global Environment Template

Template for the global environment file that all compose services inherit:

- `DATA_BASE_DIR` - Where application data is stored (default: `/srv/appdata`)
- `PROJ_BASE_DIR` - Where compose projects live (default: `/srv/compose`)
- `TRAEFIK_ACME_*` - Let's Encrypt SSL configuration
- Additional Docker-related environment variables

## Installation

### Prerequisites

- Docker and Docker Compose
- Python 3.6+
- systemd-based Linux distribution
- Root/sudo access

### Setup Steps

1. **Clone or download this repository** with all components:

    ```
    compose-systemd.py
    compose.py
    docker-compose@.service
    docker-compose.env.template
    ```

2. **Run the installer** with your ACME credentials:

    ```bash
    sudo ./compose-systemd.py --install \
      --acme-domain yourdomain.com \
      --acme-email your@email.com
    ```

    Optional: Override default directories

    ```bash
    sudo ./compose-systemd.py --install \
      --acme-domain yourdomain.com \
      --acme-email your@email.com \
      --data-base-dir /opt/appdata \
      --proj-base-dir /opt/compose
    ```

3. **Disable Docker's built-in restart policies** in all your docker-compose.yml files:

    ```yaml
    services:
        myservice:
            # Remove or set to "no"
            restart: "no"
    ```

4. **Enable your compose projects** as systemd services:

    ```bash
    # For flat projects
    sudo systemctl enable docker-compose@database.service

    # For nested projects (hyphenated paths)
    sudo systemctl enable docker-compose@genai-ollama.service
    sudo systemctl enable docker-compose@genai-open-webui.service
    ```

5. **Configure dependencies** between services:

    ```bash
    # open-webui requires both database and ollama
    sudo ./compose-systemd.py deps add genai-open-webui database requires
    sudo ./compose-systemd.py deps add genai-open-webui genai-ollama requires

    # embedding wants (soft dependency) ollama
    sudo ./compose-systemd.py deps add genai-embedding genai-ollama wants
    ```

6. **Start your services**:

    ```bash
    # Start individual service (dependencies start automatically)
    sudo systemctl start docker-compose@genai-open-webui.service

    # Start all enabled services
    sudo systemctl start docker-compose@*.service
    ```

## Directory Structure

Your compose projects should follow this structure:

```
/srv/compose/                    # PROJ_BASE_DIR
├── database/
│   └── docker-compose.yml
├── genai/                       # Prefix for related services
│   ├── ollama/
│   │   └── docker-compose.yml
│   ├── open-webui/
│   │   └── docker-compose.yml
│   └── embedding/
│       └── docker-compose.yml
└── panel/
    └── docker-compose.yml

/srv/appdata/                    # DATA_BASE_DIR
├── mongodb/                     # Application data
├── postgres/
└── ollama/
```

## How It Works

### Project Name Resolution

The systemd template uses `%i` (instance identifier) to determine which project to run:

- `docker-compose@database.service` → `/srv/compose/database`
- `docker-compose@genai-ollama.service` → `/srv/compose/genai/ollama`

Hyphens in the service name are automatically converted to directory separators by `compose.py`.

### Dependency Chain Example

When you start `genai-open-webui`:

1. Systemd checks dependencies (database, genai-ollama)
2. Starts database first, waits for it to be "ready" (RemainAfterExit=yes)
3. Starts genai-ollama, waits for it to be ready
4. Finally starts genai-open-webui
5. All services remain under systemd supervision with automatic restart on failure

### Drop-in Configuration

Dependencies are stored as systemd drop-in files:

```
/etc/systemd/system/docker-compose@genai-open-webui.service.d/
└── dependencies.conf
```

This keeps the base template clean and allows per-service customization.

## Managing Services

### Start/Stop/Restart

```bash
sudo systemctl start docker-compose@database.service
sudo systemctl stop docker-compose@database.service
sudo systemctl restart docker-compose@database.service
```

### Check Status

```bash
sudo systemctl status docker-compose@database.service
```

### View Logs

```bash
# Follow logs
journalctl -u docker-compose@database.service -f

# Last 100 lines
journalctl -u docker-compose@database.service -n 100

# Since boot
journalctl -u docker-compose@database.service -b
```

### Enable/Disable Auto-start

```bash
# Enable (start at boot)
sudo systemctl enable docker-compose@database.service

# Disable (don't start at boot)
sudo systemctl disable docker-compose@database.service
```

## Advantages Over Docker Auto-Restart

| Feature                      | Docker `restart: always`  | Systemd-managed            |
| ---------------------------- | ------------------------- | -------------------------- |
| Dependency ordering          | ❌ No                     | ✅ Yes (After=, Requires=) |
| Waits for dependencies ready | ❌ No                     | ✅ Yes                     |
| Reliable after reboot        | ⚠️ Inconsistent           | ✅ Reliable                |
| Single point of failure      | ❌ Docker daemon          | ✅ No (systemd recovery)   |
| Centralized logging          | ⚠️ Limited                | ✅ journalctl integration  |
| Fine-grained restart control | ⚠️ Limited                | ✅ Per-service policies    |
| Startup timeout control      | ❌ No                     | ✅ Configurable            |
| Health check restart         | ❌ No (manual workaround) | ✅ Via restart policies    |

## Troubleshooting

### Service fails to start

```bash
# Check detailed status
sudo systemctl status docker-compose@project.service

# View full logs
journalctl -u docker-compose@project.service -n 50

# Check if dependencies are running
sudo ./compose-systemd.py deps check project
```

### Dependency not working

```bash
# Verify dependency configuration
sudo ./compose-systemd.py deps list project

# Check drop-in files
cat /etc/systemd/system/docker-compose@project.service.d/dependencies.conf

# Reload systemd after manual changes
sudo systemctl daemon-reload
```

### compose.py not found

```bash
# Verify installation
which compose.py
ls -l /usr/local/bin/compose.py

# Reinstall if needed
sudo ./compose-systemd.py --install --acme-domain ... --acme-email ...
```

## Advanced Usage

### Using Staging ACME Server

For testing Let's Encrypt integration without hitting rate limits:

```bash
sudo ./compose-systemd.py --install \
  --acme-domain yourdomain.com \
  --acme-email your@email.com \
  --acme-server https://acme-staging-v02.api.letsencrypt.org/directory
```

### Custom Directory Layouts

If you prefer different directory structures:

```bash
sudo ./compose-systemd.py --install \
  --acme-domain yourdomain.com \
  --acme-email your@email.com \
  --data-base-dir /mnt/data/apps \
  --proj-base-dir /home/user/projects
```

### Creating Service Groups

Use systemd targets to group related services:

```bash
# Create a target file
sudo nano /etc/systemd/system/docker-compose-genai.target
```

```ini
[Unit]
Description=All GenAI Docker Compose Services
Wants=docker-compose@genai-ollama.service
Wants=docker-compose@genai-open-webui.service
Wants=docker-compose@genai-embedding.service
After=docker.service

[Install]
WantedBy=multi-user.target
```

Then control all GenAI services as one unit:

```bash
sudo systemctl enable docker-compose-genai.target
sudo systemctl start docker-compose-genai.target
```

## Environment Variables

The global environment file (`/etc/systemd/system/docker-compose.env`) provides these variables to all compose services:

- `DATA_BASE_DIR` - Base directory for persistent data
- `PROJ_BASE_DIR` - Base directory for compose project files
- `TRAEFIK_ACME_DOMAIN` - Primary domain for SSL certificates
- `TRAEFIK_ACME_EMAIL` - Email for certificate notifications
- `TRAEFIK_ACME_SERVER` - ACME server URL (Let's Encrypt)
- `DOCKER_PG_FORMAT` - Docker build progress format (optional)
- `DOCKER_PS_FORMAT` - Docker ps output format (optional)

Individual compose projects can override these by creating local `.env` files.

## Best Practices

1. **Always define dependencies** - Even if services seem independent, explicit dependencies prevent race conditions
2. **Use `requires` for critical dependencies** - Databases, message queues, etc.
3. **Use `wants` for optional dependencies** - Monitoring, logging sidecars
4. **Test with `--check-status`** - Verify installation before enabling services
5. **Monitor logs during first boot** - Use `journalctl -f` to watch services start
6. **Document your dependencies** - Keep notes on why each dependency exists
7. **Regular backups** - Back up `/etc/systemd/system/docker-compose*.{service,env}` files

## Performance Considerations

- **Startup time**: Systemd waits for each dependency sequentially. For large stacks, consider parallelizing independent branches.
- **Resource usage**: Each service runs as a separate systemd unit with minimal overhead (~100KB memory per service).
- **Log rotation**: Configure journald to prevent excessive disk usage from verbose containers.

## Security Notes

- The installer requires root access to install files in `/usr/local/bin` and `/etc/systemd/system`
- Environment files are world-readable by default - avoid storing secrets there
- Use docker secrets or external secret management for sensitive data
- ACME credentials in the environment file are used only for Let's Encrypt registration

## Migration from Docker Auto-Restart

1. **Audit existing services**: List all containers with `docker ps -a --filter "restart-policy=always"`
2. **Document dependencies**: Map out which services depend on others
3. **Disable restart policies**: Set `restart: "no"` in all docker-compose.yml files
4. **Install systemd manager**: Run the installer with your configuration
5. **Enable services one by one**: Start with independent services (databases), then dependent services
6. **Add dependencies gradually**: Test each dependency relationship
7. **Monitor first reboot**: Verify all services start correctly after a full system restart

## FAQ

**Q: Can I mix systemd-managed and Docker-managed containers?**  
A: Yes, but it's not recommended. Mixing strategies makes troubleshooting difficult.

**Q: What happens if a dependency fails?**  
A: With `requires`, the dependent service won't start. With `wants`, it starts anyway.

**Q: Can I use this with Docker Swarm or Kubernetes?**  
A: No, this is designed for standalone Docker Compose deployments on single hosts.

**Q: Does this work with rootless Docker?**  
A: Yes, but you'll need to install systemd units in user directories and adjust paths.

**Q: How do I update a running service?**  
A: Use `sudo systemctl restart docker-compose@project.service` after pulling new images or changing compose files.

**Q: Can I use environment variables in dependency definitions?**  
A: No, systemd dependencies must be literal service names. Use scripting for dynamic dependencies.
