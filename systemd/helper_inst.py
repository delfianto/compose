#!/usr/bin/env python3

"""
helper_inst.py - Installation and status checking logic
"""

import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Dict, List, Optional

from helper_base import (
    SCRIPT_DIR,
    check_root,
    print_error,
    print_info,
    print_section,
    print_success,
    print_warning,
    systemctl,
)

# Installation paths
COMPOSE_DEST = Path("/usr/local/bin/compose")
COMPCTL_DEST = Path("/usr/local/bin/composectl")
COMPOSEDEPS_DEST = Path("/usr/local/bin/compose-deps")
SYSTEMD_UNIT_DEST = Path("/etc/systemd/system/docker-compose@.service")
ENV_FILE_DEST = Path("/etc/systemd/system/docker-compose.env")


def check_dependencies() -> List[str]:
    """Check for required system dependencies."""
    missing: List[str] = []
    for cmd in ["docker", "systemctl", "python3"]:
        if not shutil.which(cmd):
            missing.append(cmd)
    return missing


def backup_file(filepath: Path):
    """Backup existing file with timestamp."""
    if filepath.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if filepath.suffix:
            backup_path = filepath.with_suffix(f"{filepath.suffix}.backup.{timestamp}")
        else:
            backup_path = Path(f"{filepath}.backup.{timestamp}")
        print_warning(f"Backing up existing file to: {backup_path}")
        shutil.copy2(filepath, backup_path)


def parse_env_file(env_file: Path) -> Dict[str, str]:
    """Parse environment file and extract key-value pairs."""
    env_vars: Dict[str, str] = {}
    if not env_file.exists():
        return env_vars

    try:
        with env_file.open() as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
                if match:
                    key, value = match.groups()
                    value = value.strip('"').strip("'")
                    env_vars[key] = value
        return env_vars
    except Exception as e:
        print_warning(f"Failed to parse environment file: {e}")
        return {}


def get_existing_config() -> Optional[Dict[str, Optional[str]]]:
    """Get existing configuration from installed environment file."""
    if not ENV_FILE_DEST.exists():
        return None

    env_vars = parse_env_file(ENV_FILE_DEST)
    if not env_vars:
        return None

    config: Dict[str, Optional[str]] = {
        "acme_domain": env_vars.get("TRAEFIK_ACME_DOMAIN"),
        "acme_email": env_vars.get("TRAEFIK_ACME_EMAIL"),
        "acme_server": env_vars.get("TRAEFIK_ACME_SERVER"),
        "data_base_dir": env_vars.get("DOCKER_DATA_DIR"),
        "proj_base_dir": env_vars.get("DOCKER_PROJ_DIR"),
    }

    if config["acme_domain"] and config["acme_email"]:
        return config
    return None


def load_template(filename: str) -> str:
    """Load template file from script directory."""
    template_path = SCRIPT_DIR / filename
    if not template_path.exists():
        print_error(f"Template file not found: {template_path}")
        print_info(f"Please ensure {filename} is in the same directory as this script")
        sys.exit(1)

    print_info(f"Loading template: {template_path}")
    return template_path.read_text()


def generate_env_file(args) -> str:
    """Generate environment file content from template and arguments."""
    template_str = load_template("docker-compose.env.template")
    template = Template(template_str)

    values = {
        "data_base_dir": args.data_base_dir or "/srv/appdata",
        "proj_base_dir": args.proj_base_dir or "/srv/compose",
        "acme_domain": args.acme_domain,
        "acme_email": args.acme_email,
        "acme_server": args.acme_server
        or "https://acme-v02.api.letsencrypt.org/directory",
    }

    try:
        return template.substitute(**values)
    except KeyError as e:
        print_error(f"Missing required template variable: {e}")
        sys.exit(1)


def run_install(args):
    """Install compose, compctl, compose-deps, and systemd template."""
    check_root()

    existing_config = get_existing_config()
    is_reinstall = existing_config is not None

    if is_reinstall:
        print_section("Docker Compose Systemd Reinstallation")
        print()
        print_info("Existing installation detected")
        print_info(f"  ACME Domain: {existing_config['acme_domain']}")
        print_info(f"  ACME Email: {existing_config['acme_email']}")
        print()

        if not args.acme_domain:
            args.acme_domain = existing_config["acme_domain"]
            print_info("Using existing ACME domain")

        if not args.acme_email:
            args.acme_email = existing_config["acme_email"]
            print_info("Using existing ACME email")

        if not args.acme_server and existing_config["acme_server"]:
            args.acme_server = existing_config["acme_server"]
            print_info("Using existing ACME server")

        if not args.data_base_dir and existing_config["data_base_dir"]:
            args.data_base_dir = existing_config["data_base_dir"]

        if not args.proj_base_dir and existing_config["proj_base_dir"]:
            args.proj_base_dir = existing_config["proj_base_dir"]

        print()
    else:
        print_section("Docker Compose Systemd Installation")
        print()
        print_info("Fresh installation detected")
        print()

        if not args.acme_domain:
            print_error("--acme-domain is required for fresh installation")
            print_info("Example: --acme-domain example.com")
            sys.exit(1)

        if not args.acme_email:
            print_error("--acme-email is required for fresh installation")
            print_info("Example: --acme-email admin@example.com")
            sys.exit(1)

    missing = check_dependencies()
    if missing:
        print_error(f"Missing required dependencies: {', '.join(missing)}")
        sys.exit(1)

    # NOTE: In this split version, we expect the main orchestrator script
    # to be what we install as 'compose-systemd'.
    # We still install the other tools separately.

    compose_src = SCRIPT_DIR / "compose.py"
    compctl_src = SCRIPT_DIR / "composectl.py"
    # compose-deps logic is now integrated into the main script or helper_deps
    # but for compatibility we might want to install the main script as 'compose-deps'
    # or keep it separate. For this logic, we'll assume we are installing
    # the tools found in the dir.

    systemd_template = SCRIPT_DIR / "docker-compose@.service"
    env_template = SCRIPT_DIR / "docker-compose.env.template"

    required_files = [
        ("compose.py", compose_src),
        ("composectl.py", compctl_src),
        ("docker-compose@.service", systemd_template),
        ("docker-compose.env.template", env_template),
    ]

    missing_files: List[str] = []
    for name, path in required_files:
        if not path.exists():
            missing_files.append(name)

    if missing_files:
        print_error(f"Missing required files: {', '.join(missing_files)}")
        print_info(f"Please ensure all files are in: {SCRIPT_DIR}")
        sys.exit(1)

    print_info(f"Installing compose.py to {COMPOSE_DEST}")
    backup_file(COMPOSE_DEST)
    shutil.copy2(compose_src, COMPOSE_DEST)
    os.chmod(COMPOSE_DEST, 0o755)
    print_success("compose installed (accessible as 'compose' command)")

    print_info(f"Installing composectl.py to {COMPCTL_DEST}")
    backup_file(COMPCTL_DEST)
    shutil.copy2(compctl_src, COMPCTL_DEST)
    os.chmod(COMPCTL_DEST, 0o755)
    print_success("composectl installed (accessible as 'composectl' command)")

    # We skip installing 'composedeps.py' as a standalone since it's now part
    # of the unified CLI, but we can symlink the main script if needed later.

    print_info(f"Installing systemd unit template to {SYSTEMD_UNIT_DEST}")
    backup_file(SYSTEMD_UNIT_DEST)

    systemd_content = systemd_template.read_text()
    systemd_content = systemd_content.replace(
        "/usr/local/bin/compose.py", "/usr/local/bin/compose"
    )

    SYSTEMD_UNIT_DEST.write_text(systemd_content)
    os.chmod(SYSTEMD_UNIT_DEST, 0o644)
    print_success("Systemd unit template installed")

    if is_reinstall:
        print_info(f"Updating environment file at {ENV_FILE_DEST}")
    else:
        print_info(f"Generating environment file at {ENV_FILE_DEST}")

    backup_file(ENV_FILE_DEST)
    env_content = generate_env_file(args)
    ENV_FILE_DEST.write_text(env_content)
    os.chmod(ENV_FILE_DEST, 0o644)
    print_success("Environment file created")
    print_info(f"  ACME domain: {args.acme_domain}")
    print_info(f"  ACME email: {args.acme_email}")

    print_info("Reloading systemd daemon")
    try:
        systemctl("daemon-reload", capture=True)
        print_success("Systemd daemon reloaded")
    except Exception:
        print_error("Failed to reload systemd daemon")
        sys.exit(1)

    print()
    if is_reinstall:
        print_section("Reinstallation Complete!")
    else:
        print_section("Installation Complete!")

    print()
    if not is_reinstall:
        print_info("Next steps:")
        print(" 1. Review environment file: sudo nano", ENV_FILE_DEST)
        print(" 2. Disable restart policies in docker-compose.yml files")
        print(" 3. Enable services: sudo composectl enable <project>")
        print(
            " 4. Manage dependencies: sudo compose-systemd deps add <service> <dependency> [requires|wants]"
        )
        print(" 5. Start services: sudo composectl start <project>")
        print(" 6. Check status: composectl status <project>")
        print()


def run_check_status(args):
    """Check installation status."""
    print_section("Installation Status Check")
    print()

    is_root = os.geteuid() == 0

    existing_config = get_existing_config()
    if existing_config:
        print_info("Installation type: Reinstall mode available")
        print_info(f"  Existing ACME domain: {existing_config['acme_domain']}")
        print_info(f"  Existing ACME email: {existing_config['acme_email']}")
        print()
    else:
        print_info("Installation type: Fresh install required")
        print()

    missing_deps = check_dependencies()
    if missing_deps:
        print_error(f"Missing dependencies: {', '.join(missing_deps)}")
    else:
        print_success("All system dependencies found")

    print()
    print_info("Template files (in script directory):")
    template_files = [
        ("compose.py", SCRIPT_DIR / "compose.py"),
        ("composectl.py", SCRIPT_DIR / "composectl.py"),
        ("systemd template", SCRIPT_DIR / "docker-compose@.service"),
        ("env template", SCRIPT_DIR / "docker-compose.env.template"),
    ]

    for name, path in template_files:
        if path.exists():
            print_success(f"  {name}: {path}")
        else:
            print_warning(f"  {name}: NOT FOUND")

    print()
    print_info("Installed files:")
    files_to_check = [
        ("compose", COMPOSE_DEST),
        ("composectl", COMPCTL_DEST),
        ("systemd unit template", SYSTEMD_UNIT_DEST),
        ("environment file", ENV_FILE_DEST),
    ]

    for name, path in files_to_check:
        if path.exists():
            print_success(f"  {name}: {path}")
        else:
            print_error(f"  {name}: NOT FOUND")

    if ENV_FILE_DEST.exists():
        print()
        print_info("Environment configuration:")
        with ENV_FILE_DEST.open() as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    print(f"  {line}")

    if is_root or shutil.which("systemctl"):
        print()
        print_info("Enabled docker-compose services:")
        try:
            result = systemctl(
                "list-unit-files", "docker-compose@*.service", check=False
            )
            if result.returncode == 0:
                lines = [
                    line
                    for line in result.stdout.split("\n")
                    if "docker-compose@" in line
                ]
                if lines:
                    for line in lines:
                        print(f"  {line}")
                else:
                    print_warning("  No services enabled yet")
            else:
                print_warning("  Unable to list services")
        except Exception as e:
            print_warning(f"  Unable to check services: {e}")

    print()
