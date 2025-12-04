#!/usr/bin/env python3
"""
Common utilities for Docker CLI plugins
"""

import json
import subprocess
import sys
from typing import Any, Dict, List, Optional

# ANSI color codes
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
CYAN = "\033[1;36m"
NC = "\033[0m"


def handle_metadata(metadata: Dict[str, Any]) -> None:
    """
    Handle Docker CLI plugin metadata requests.

    Args:
        metadata: Plugin metadata dictionary with SchemaVersion, Vendor,
                  Version, and ShortDescription keys
    """
    if len(sys.argv) > 1 and sys.argv[1] == "docker-cli-plugin-metadata":
        print(json.dumps(metadata, indent=2))
        sys.exit(0)


def parse_plugin_args(parser, plugin_names: List[str], skip_dashes: bool = True) -> Any:
    """
    Parse arguments for a Docker CLI plugin, handling the plugin name argument.

    Args:
        parser: Configured argparse.ArgumentParser instance
        plugin_names: List of possible plugin names (e.g., ["nbs", "docker-nbs"])
        skip_dashes: Whether to skip arguments starting with "-"

    Returns:
        Parsed arguments namespace
    """
    # Docker passes the plugin name as the first argument after the script name
    # Example: docker nbs --file foo.toml -> sys.argv = ['docker-nbs', 'nbs', '--file', 'foo.toml']
    args_to_parse = sys.argv[1:]

    # Skip the plugin name if it's the first argument
    if args_to_parse and args_to_parse[0] in plugin_names:
        args_to_parse = args_to_parse[1:]

    return parser.parse_args(args_to_parse)


def run_docker_command(
    args: List[str],
    check: bool = True,
    capture_output: bool = True,
    timeout: Optional[int] = None,
) -> subprocess.CompletedProcess:
    """
    Execute a docker command and return the result.

    Args:
        args: Command arguments (without 'docker' prefix)
        check: Whether to raise exception on non-zero exit code
        capture_output: Whether to capture stdout/stderr
        timeout: Command timeout in seconds

    Returns:
        CompletedProcess instance with returncode, stdout, stderr
    """
    try:
        result = subprocess.run(
            ["docker"] + args,
            capture_output=capture_output,
            text=True,
            check=check,
            timeout=timeout,
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error running docker command: {e}{NC}", file=sys.stderr)
        raise
    except subprocess.TimeoutExpired as e:
        print(f"{RED}Command timed out: {e}{NC}", file=sys.stderr)
        raise
    except FileNotFoundError:
        print(f"{RED}Docker command not found{NC}", file=sys.stderr)
        sys.exit(1)


def check_docker_daemon(timeout: int = 5) -> bool:
    """
    Check if Docker daemon is accessible.

    Returns:
        True if daemon is accessible, False otherwise
    """
    print(f"{YELLOW}[*]{NC} Checking Docker daemon...")
    try:
        run_docker_command(["info"], timeout=timeout)
        print(f"{GREEN}✓ Docker daemon is running{NC}\\n")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print(f"{RED}✗ Docker daemon is not accessible{NC}")
        return False


def print_error(message: str) -> None:
    """Print error message in red."""
    print(f"{RED}{message}{NC}", file=sys.stderr)


def print_success(message: str) -> None:
    """Print success message in green."""
    print(f"{GREEN}{message}{NC}")


def print_info(message: str) -> None:
    """Print info message in cyan."""
    print(f"{CYAN}{message}{NC}")


def print_warning(message: str) -> None:
    """Print warning message in yellow."""
    print(f"{YELLOW}{message}{NC}")
