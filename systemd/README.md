# Docker Compose Systemd Manager

A comprehensive systemd-based management system for Docker Compose projects that solves Docker's unreliable container auto-start mechanisms through proper dependency management and service orchestration.

## The Problem: Why Docker Auto-Start is Unreliable

Docker's built-in restart policies (`restart: always`, `restart: unless-stopped`) have fundamental issues:

### Race Conditions at Boot

- Database containers may not be initialized when applications start
- Networks might not be ready when containers bind
- Services fail health checks due to unavailable dependencies

### No Dependency Management

Docker can't reliably manage service startup order, the `depends_on` directive only ensures containers start, not that services are ready.

### Restart Policy Inconsistencies

The `always` policy frequently fails after host reboots or gives up after successive failures.

## The Solution: Systemd-Managed Compose

This toolkit provides:

- ✅ Explicit dependency chains with proper ordering
- ✅ Reliable restart behavior via systemd
- ✅ Integration with journalctl for centralized logging
- ✅ Fine-grained per-service control

## Components

### 1. compose - Enhanced Docker Compose Wrapper

Located at: `/usr/local/bin/compose`

Python wrapper providing:

- Automatic `.env*` file discovery
- Sensible command defaults
- Hyphenated path support (`genai-ollama` → `genai/ollama`)
- Transparent command execution

**Supported Commands:**

- `up` - Start with `--remove-orphans --detach`
- `down` - Stop with `--remove-orphans --volumes`
- `logs` - Follow last 100 lines (`-f --tail=100`)
- `ps` - Pretty table format
- `build` - No cache (`--no-cache`)
- `exec` - Default to `/bin/bash`
- `pull` - Ignore pull failures
- `restart`, `start`, `stop` - Standard operations

**Environment Variables:**

- `COMPOSE_PROJECT` - Project name (supports hyphens)
- `COMPOSE_BASE` - Base directory (default: current dir)
- `DOCKER_PG_FORMAT` - Build progress style
- `DOCKER_PS_FORMAT` - Override ps format

**Usage:**

```bash
compose up                    # Start with defaults
compose logs                  # Follow latest logs
compose ps                    # View running containers
compose exec service-name     # Interactive bash shell
```

### 2. composectl - Systemd Service Controller

Located at: `/usr/local/bin/composectl`

Systemctl wrapper that simplifies management of `docker-compose@` services.

**Commands:**

```bash
# Service Control (requires root/sudo)
composectl start <service> [service2...]
composectl stop <service> [service2...]
composectl restart <service> [service2...]
composectl enable <service> [service2...]    # Enable at boot
composectl disable <service> [service2...]   # Disable at boot

# Status Checking (no root needed)
composectl status <service> [service2...]
composectl is-active <service> [service2...]
composectl is-enabled <service> [service2...]
composectl list                              # List all services

# Log Viewing
composectl logs <service> [service2...]
composectl logs -f <service>                 # Follow logs
composectl logs -n 50 <service>              # Last 50 lines
composectl logs --since "1 hour ago" <service>
```

**Features:**

- Auto-adds `docker-compose@` prefix and `.service` suffix
- Auto-detects when sudo is required
- Colored output for better readability
- Supports batch operations on multiple services

### 3. systemd.py - Installation & Dependency Manager

Main installer script (run as: `python3 systemd.py`)

**Installation Command:**

```bash
sudo python3 systemd.py install \
  --acme-domain example.com \
  --acme-email admin@example.com \
  [--acme-server URL] \
  [--data-base-dir /srv/appdata] \
  [--proj-base-dir /srv/compose]
```

**Options:**

- `--acme-domain` - Domain for Let's Encrypt SSL (required for fresh install)
- `--acme-email` - Email for SSL notifications (required for fresh install)
- `--acme-server` - ACME server URL (default: Let's Encrypt production)
- `--data-base-dir` - Application data directory (default: `/srv/appdata`)
- `--proj-base-dir` - Compose projects directory (default: `/srv/compose`)

**Dependency Management:**

```bash
# Add hard dependency (requires)
sudo python3 systemd.py deps add <service> <dependency> requires

# Add soft dependency (wants)
sudo python3 systemd.py deps add <service> <dependency> wants

# List dependencies
python3 systemd.py deps list <service>

# Check full dependency chain
python3 systemd.py deps check <service>

# Remove dependency
sudo python3 systemd.py deps remove <service> <dependency>
```

**Check Installation Status:**

```bash
python3 systemd.py check-status
```

### 4. docker-compose@.service - Systemd Template Unit

Systemd template file installed at: `/etc/systemd/system/docker-compose@.service`

**Features:**

- Template-based instantiation (one file, multiple instances)
- Automatic environment loading from `/etc/systemd/system/docker-compose.env`
- 5-minute startup timeout
- Restart on failure with 10-second delay
- Dependency support through drop-in files

**Service Naming:**

- Instance `database` → `/srv/compose/database`
- Instance `genai-ollama` → `/srv/compose/genai/ollama`

### 5. Environment Configuration

**Template:** `docker-compose.env.template`  
**Installed:** `/etc/systemd/system/docker-compose.env`

Global environment variables inherited by all compose services:

- `DOCKER_DATA_DIR` - Application data directory
- `DOCKER_PROJ_DIR` - Compose projects directory
- `TRAEFIK_ACME_DOMAIN` - Primary domain for SSL
- `TRAEFIK_ACME_EMAIL` - Email for certificate notifications
- `TRAEFIK_ACME_SERVER` - ACME server URL

## Installation

### Prerequisites

- Docker and Docker Compose installed
- Python 3.6+
- systemd-based Linux distribution
- Root/sudo access

### Setup Steps

**1. Prepare Files**
Ensure you have all required files:

```
systemd.py
compose.py
composectl.py
helper_base.py
helper_deps.py
helper_inst.py
docker-compose@.service
docker-compose.env.template
```

**2. Run Installation**

```bash
sudo python3 systemd.py install \
  --acme-domain yourdomain.com \
  --acme-email your@email.com
```

This installs:

- `/usr/local/bin/compose` - Compose wrapper
- `/usr/local/bin/composectl` - Service controller
- `/etc/systemd/system/docker-compose@.service` - Systemd template
- `/etc/systemd/system/docker-compose.env` - Global environment

**3. Prepare Compose Projects**
Disable Docker's restart policies:

```yaml
services:
    myservice:
        restart: "no" # Or remove the line entirely
```

**4. Enable Services**

```bash
sudo systemctl enable docker-compose@database.service
sudo systemctl enable docker-compose@genai-ollama.service
```

**5. Configure Dependencies**

```bash
# Example: open-webui requires database and ollama
sudo python3 systemd.py deps add genai-open-webui database requires
sudo python3 systemd.py deps add genai-open-webui genai-ollama requires
```

**6. Start Services**

```bash
# Start individual service (dependencies start automatically)
sudo composectl start genai-open-webui

# Or use systemctl directly
sudo systemctl start docker-compose@genai-open-webui.service
```

## Directory Structure

Expected project layout:

```
/srv/compose/                    # DOCKER_PROJ_DIR
├── database/
│   ├── docker-compose.yml
│   └── .env                     # Optional project-specific env
├── genai/
│   ├── ollama/
│   │   └── docker-compose.yml
│   ├── open-webui/
│   │   └── docker-compose.yml
│   └── embedding/
│       └── docker-compose.yml
└── panel/
    └── docker-compose.yml

/srv/appdata/                    # DOCKER_DATA_DIR
├── mongodb/
├── postgres/
└── ollama/
```

## Dependency Management

### Dependency Types

**Requires (Hard Dependency)**

- Service won't start if dependency fails
- Use for critical dependencies (databases, required APIs)

**Wants (Soft Dependency)**

- Service starts even if dependency fails
- Use for optional services (monitoring, logging)

### Configuration Files

Dependencies are stored as drop-in files:

```
/etc/systemd/system/docker-compose@<service>.service.d/
└── dependencies.conf
```

Example `dependencies.conf`:

```ini
[Unit]
Requires=docker-compose@database.service
Wants=docker-compose@monitoring.service
After=docker-compose@database.service
After=docker-compose@monitoring.service
```

### Dependency Chain Example

Starting `genai-open-webui` with dependencies:

1. Systemd checks dependencies (database, genai-ollama)
2. Starts database first, waits for readiness
3. Starts genai-ollama, waits for readiness
4. Starts genai-open-webui
5. All services supervised with automatic restart

## Service Management

### Using composectl (Recommended)

```bash
# Start/Stop
sudo composectl start database genai-ollama
sudo composectl stop database
sudo composectl restart genai-open-webui

# Status
composectl status database
composectl is-active database genai-ollama
composectl is-enabled database

# List all services
composectl list

# Logs
composectl logs database
composectl logs -f genai-ollama
composectl logs -n 100 --since "10 minutes ago" database

# Enable/Disable at boot
sudo composectl enable database genai-ollama
sudo composectl disable genai-embedding
```

### Using systemctl (Alternative)

```bash
sudo systemctl start docker-compose@database.service
sudo systemctl status docker-compose@database.service
journalctl -u docker-compose@database.service -f
sudo systemctl enable docker-compose@database.service
```

## Troubleshooting

### Service Fails to Start

```bash
# Check service status
sudo composectl status project

# View detailed logs
composectl logs -n 100 project

# Check dependencies
python3 systemd.py deps check project

# Verify dependency services are running
composectl list
```

### Dependency Issues

```bash
# List configured dependencies
python3 systemd.py deps list project

# Check drop-in configuration
cat /etc/systemd/system/docker-compose@project.service.d/dependencies.conf

# Reload after manual changes
sudo systemctl daemon-reload
```

### Installation Problems

```bash
# Check installation status
python3 systemd.py check-status

# Verify installed files
ls -l /usr/local/bin/compose /usr/local/bin/composectl
ls -l /etc/systemd/system/docker-compose@.service
cat /etc/systemd/system/docker-compose.env

# Reinstall (preserves existing configuration)
sudo python3 systemd.py install \
  --acme-domain yourdomain.com \
  --acme-email your@email.com
```

### Compose Command Not Working

```bash
# Set environment variable for project
export COMPOSE_PROJECT=database
compose ps

# Or use full path
cd /srv/compose/database
/usr/local/bin/compose ps

# Check compose wrapper
compose --print-workdir
```

## Advanced Usage

### Hyphenated Projects

Projects with hyphens in names are treated as nested paths:

```bash
# Service: genai-ollama
# Maps to: /srv/compose/genai/ollama

sudo composectl start genai-ollama
```

### Custom ACME Server (Staging)

For testing without rate limits:

```bash
sudo python3 systemd.py install \
  --acme-domain test.example.com \
  --acme-email admin@example.com \
  --acme-server https://acme-staging-v02.api.letsencrypt.org/directory
```

### Service Groups with Targets

Create systemd targets for related services:

`/etc/systemd/system/docker-compose-genai.target`:

```ini
[Unit]
Description=All GenAI Services
Wants=docker-compose@genai-ollama.service
Wants=docker-compose@genai-open-webui.service
After=docker.service

[Install]
WantedBy=multi-user.target
```

Control as group:

```bash
sudo systemctl enable docker-compose-genai.target
sudo systemctl start docker-compose-genai.target
```

### Override Compose Defaults

Set environment variables to customize behavior:

```bash
# Change docker ps format
export DOCKER_PS_FORMAT="table {{.Names}}\t{{.Status}}"
compose ps

# Change build progress format
export DOCKER_PG_FORMAT=plain
compose build
```

## Comparison: Docker vs Systemd

| Feature                      | Docker `restart: always` | Systemd-managed         |
| ---------------------------- | ------------------------ | ----------------------- |
| Dependency ordering          | ❌ No                    | ✅ Yes                  |
| Wait for dependencies ready  | ❌ No                    | ✅ Yes                  |
| Reliable after reboot        | ⚠️ Inconsistent          | ✅ Reliable             |
| Single point of failure      | ❌ Docker daemon         | ✅ Systemd recovery     |
| Centralized logging          | ⚠️ Limited               | ✅ journalctl           |
| Fine-grained restart control | ⚠️ Limited               | ✅ Per-service policies |
| Startup timeout              | ❌ No                    | ✅ Configurable         |
| Health check restart         | ❌ Manual workaround     | ✅ Via restart policies |

## Best Practices

1. **Define all dependencies explicitly** - Prevents race conditions
2. **Use `requires` for critical dependencies** - Databases, APIs
3. **Use `wants` for optional services** - Monitoring, sidecars
4. **Test with check-status first** - Verify before enabling
5. **Monitor logs during first boot** - Watch service startup
6. **Document dependencies** - Keep notes on relationships
7. **Regular backups** - Back up systemd configuration files

## Migration from Docker Auto-Restart

1. Audit: `docker ps -a --filter "restart-policy=always"`
2. Map dependencies between services
3. Set `restart: "no"` in all compose files
4. Run installer with configuration
5. Enable services incrementally
6. Add dependencies gradually
7. Test full system reboot

## FAQ

**Q: Can I mix systemd and Docker-managed containers?**  
A: Yes, but not recommended—makes troubleshooting difficult.

**Q: What if a dependency fails?**  
A: `requires` prevents start; `wants` allows start anyway.

**Q: Does this work with rootless Docker?**  
A: Yes, install units in user systemd directories.

**Q: How do I update a service?**  
A: `sudo composectl restart project` after pulling images.

**Q: Can dependencies use environment variables?**  
A: No, dependencies must be literal service names.

## Security Notes

- Installer requires root for system file installation
- Environment files are world-readable—avoid storing secrets
- Use Docker secrets for sensitive data
- ACME credentials only used for Let's Encrypt registration

## Files Installed

- `/usr/local/bin/compose` - Compose wrapper (755)
- `/usr/local/bin/composectl` - Service controller (755)
- `/etc/systemd/system/docker-compose@.service` - Template unit (644)
- `/etc/systemd/system/docker-compose.env` - Global environment (644)
- `/etc/systemd/system/docker-compose@*.service.d/` - Drop-in directories
