#!/usr/bin/env python3

"""
helper_base.py - Shared base utilities for compose-systemd tools
"""

import os
import subprocess
import sys
from pathlib import Path


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    MAGENTA = "\033[0;35m"
    NC = "\033[0m"  # No Color


# The directory where these scripts are located
SCRIPT_DIR = Path(__file__).parent.resolve()


def print_info(msg: str):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")


def print_success(msg: str):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")


def print_error(msg: str):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")


def print_section(msg: str):
    print(f"{Colors.CYAN}==> {msg}{Colors.NC}")


def check_root():
    """Check if running as root."""
    if os.geteuid() != 0:
        print_error("This operation must be run as root or with sudo")
        sys.exit(1)


def systemctl(*args, check=True, capture=True) -> subprocess.CompletedProcess:
    """Execute systemctl command."""
    cmd = ["systemctl", *args]
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True, check=check)
    return subprocess.run(cmd, check=check)


def get_compose_service_name(project: str) -> str:
    """Convert project name to docker-compose@ systemd unit name."""
    # Accept already-full unit names
    if project.endswith(".service"):
        if project.startswith("docker-compose@"):
            return project
        # strip .service and normalize below
        project = project[:-8]

    if not project.startswith("docker-compose@"):
        return f"docker-compose@{project}.service"
    if not project.endswith(".service"):
        return f"{project}.service"
    return project
