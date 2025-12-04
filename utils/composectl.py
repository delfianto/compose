#!/usr/bin/env python3

"""
compose-ctl.py - Systemctl wrapper for docker-compose@ services

Simplifies systemctl commands for docker-compose@ template services
by automatically handling the service naming convention.
"""

import argparse
import subprocess
import sys
from typing import List


# ANSI color codes
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    MAGENTA = "\033[0;35m"
    NC = "\033[0m"  # No Color


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


def get_service_name(project: str) -> str:
    """Convert project name to systemd service name."""
    # Handle both with and without .service suffix
    if project.endswith(".service"):
        if project.startswith("docker-compose@"):
            return project
        else:
            # Remove .service and add docker-compose@ prefix
            project = project[:-8]

    if not project.startswith("docker-compose@"):
        return f"docker-compose@{project}.service"

    return f"{project}.service" if not project.endswith(".service") else project


def systemctl(*args, check=True, capture=True) -> subprocess.CompletedProcess:
    """Execute systemctl command."""
    cmd = ["systemctl", *args]

    if capture:
        return subprocess.run(cmd, capture_output=True, text=True, check=check)
    else:
        # For interactive commands like status, don't capture output
        return subprocess.run(cmd, check=check)


def is_root() -> bool:
    """Check if running as root."""
    import os

    return os.geteuid() == 0


def check_sudo_needed(action: str) -> bool:
    """Check if sudo is needed for the action."""
    non_root_actions = ["status", "list", "is-enabled", "is-active"]
    return action not in non_root_actions


def run_systemctl_action(action: str, services: List[str], sudo: bool = False):
    """
    Run a systemctl action on one or more services.

    Args:
        action: The systemctl action (start, stop, status, etc.)
        services: List of service names (project names)
        sudo: Whether to use sudo (auto-detected if not specified)
    """
    # Check if sudo is needed
    needs_sudo = check_sudo_needed(action) and not is_root()

    if needs_sudo and not sudo:
        print_warning(f"Action '{action}' requires root privileges")
        print_info("Retrying with sudo...")

    # Convert project names to full service names
    service_names = [get_service_name(svc) for svc in services]

    # Special handling for status - run separately for each service
    if action == "status":
        for svc_name in service_names:
            print_section(f"Status: {svc_name}")
            cmd = (
                ["sudo", "systemctl", action, svc_name]
                if needs_sudo
                else ["systemctl", action, svc_name]
            )
            try:
                subprocess.run(cmd, check=False)
                print()
            except KeyboardInterrupt:
                print()
                sys.exit(130)
        return

    # For other commands, we can batch them
    cmd = (
        ["sudo", "systemctl", action] + service_names
        if needs_sudo
        else ["systemctl", action] + service_names
    )

    # Print the command we're running
    print_info(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)

        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        if result.returncode == 0:
            print_success(f"Action '{action}' completed successfully")
        else:
            print_error(f"Action '{action}' failed with exit code {result.returncode}")
            sys.exit(result.returncode)

    except KeyboardInterrupt:
        print()
        print_warning("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Failed to execute command: {e}")
        sys.exit(1)


def cmd_list(args):
    """List all docker-compose services."""
    print_section("Docker Compose Services")
    print()

    try:
        # List all docker-compose@ services
        result = systemctl(
            "list-units",
            "--all",
            "--type=service",
            "docker-compose@*.service",
            "--no-pager",
            "--plain",
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            print(result.stdout)
        else:
            print_warning("No docker-compose services found")

        # Also show which ones are enabled
        print()
        print_section("Enabled at Boot")
        print()

        result = systemctl(
            "list-unit-files", "docker-compose@*.service", "--no-pager", check=False
        )

        if result.returncode == 0 and result.stdout.strip():
            print(result.stdout)
        else:
            print_warning("No enabled docker-compose services found")

    except Exception as e:
        print_error(f"Failed to list services: {e}")
        sys.exit(1)


def cmd_logs(args):
    """View logs for services using journalctl."""
    services = args.services
    service_names = [get_service_name(svc) for svc in services]

    # Build journalctl command
    cmd = ["journalctl"]

    # Add each service as a unit
    for svc_name in service_names:
        cmd.extend(["-u", svc_name])

    # Add common journalctl flags
    if args.follow:
        cmd.append("-f")
    if args.lines:
        cmd.extend(["-n", str(args.lines)])
    if args.since:
        cmd.extend(["--since", args.since])
    if args.until:
        cmd.extend(["--until", args.until])

    cmd.append("--no-pager") if not args.follow else None

    print_info(f"Running: {' '.join(cmd)}")
    print()

    try:
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print()
        sys.exit(130)


def cmd_action(args):
    """Handle systemctl actions (start, stop, restart, etc.)."""
    action = args.action
    services = args.services

    if not services:
        print_error(f"No services specified for action '{action}'")
        print_info(f"Usage: compose-ctl {action} <service1> [service2] ...")
        sys.exit(1)

    run_systemctl_action(action, services, args.sudo)


def cmd_is_active(args):
    """Check if services are active."""
    services = args.services
    service_names = [get_service_name(svc) for svc in services]

    all_active = True
    for svc_name in service_names:
        result = systemctl("is-active", svc_name, check=False)
        state = result.stdout.strip()

        if state == "active":
            print(
                f"{Colors.GREEN}●{Colors.NC} {svc_name}: {Colors.GREEN}{state}{Colors.NC}"
            )
        else:
            print(
                f"{Colors.RED}●{Colors.NC} {svc_name}: {Colors.RED}{state}{Colors.NC}"
            )
            all_active = False

    sys.exit(0 if all_active else 1)


def cmd_is_enabled(args):
    """Check if services are enabled."""
    services = args.services
    service_names = [get_service_name(svc) for svc in services]

    all_enabled = True
    for svc_name in service_names:
        result = systemctl("is-enabled", svc_name, check=False)
        state = result.stdout.strip()

        if state == "enabled":
            print(
                f"{Colors.GREEN}●{Colors.NC} {svc_name}: {Colors.GREEN}{state}{Colors.NC}"
            )
        else:
            print(
                f"{Colors.YELLOW}●{Colors.NC} {svc_name}: {Colors.YELLOW}{state}{Colors.NC}"
            )
            all_enabled = False

    sys.exit(0 if all_enabled else 1)


def main():
    parser = argparse.ArgumentParser(
        prog="compose-ctl",
        description="Systemctl wrapper for docker-compose@ services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start services
  compose-ctl start database genai-ollama
  sudo compose-ctl start database genai-ollama

  # Stop services
  sudo compose-ctl stop genai-open-webui

  # Restart services
  sudo compose-ctl restart database

  # Check status
  compose-ctl status database genai-ollama

  # Enable at boot
  sudo compose-ctl enable database genai-ollama

  # Disable from boot
  sudo compose-ctl disable genai-embedding

  # Check if active
  compose-ctl is-active database

  # Check if enabled
  compose-ctl is-enabled database genai-ollama

  # List all services
  compose-ctl list

  # View logs
  compose-ctl logs database
  compose-ctl logs -f genai-ollama  # Follow logs
  compose-ctl logs -n 50 database   # Last 50 lines
  compose-ctl logs --since "1 hour ago" database

Note: The 'docker-compose@' prefix and '.service' suffix are added automatically.
""",
    )

    # Global flags
    parser.add_argument(
        "--sudo",
        action="store_true",
        help="Force using sudo (auto-detected by default)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start services")
    start_parser.add_argument("services", nargs="+", help="Service names")
    start_parser.set_defaults(func=cmd_action, action="start")

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop services")
    stop_parser.add_argument("services", nargs="+", help="Service names")
    stop_parser.set_defaults(func=cmd_action, action="stop")

    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart services")
    restart_parser.add_argument("services", nargs="+", help="Service names")
    restart_parser.set_defaults(func=cmd_action, action="restart")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show service status")
    status_parser.add_argument("services", nargs="+", help="Service names")
    status_parser.set_defaults(func=cmd_action, action="status")

    # Enable command
    enable_parser = subparsers.add_parser("enable", help="Enable services at boot")
    enable_parser.add_argument("services", nargs="+", help="Service names")
    enable_parser.set_defaults(func=cmd_action, action="enable")

    # Disable command
    disable_parser = subparsers.add_parser("disable", help="Disable services at boot")
    disable_parser.add_argument("services", nargs="+", help="Service names")
    disable_parser.set_defaults(func=cmd_action, action="disable")

    # Is-active command
    is_active_parser = subparsers.add_parser(
        "is-active", help="Check if services are active"
    )
    is_active_parser.add_argument("services", nargs="+", help="Service names")
    is_active_parser.set_defaults(func=cmd_is_active)

    # Is-enabled command
    is_enabled_parser = subparsers.add_parser(
        "is-enabled", help="Check if services are enabled"
    )
    is_enabled_parser.add_argument("services", nargs="+", help="Service names")
    is_enabled_parser.set_defaults(func=cmd_is_enabled)

    # List command
    list_parser = subparsers.add_parser("list", help="List all docker-compose services")
    list_parser.set_defaults(func=cmd_list)

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View service logs (journalctl)")
    logs_parser.add_argument("services", nargs="+", help="Service names")
    logs_parser.add_argument(
        "-f", "--follow", action="store_true", help="Follow log output"
    )
    logs_parser.add_argument("-n", "--lines", type=int, help="Number of lines to show")
    logs_parser.add_argument(
        "--since", help="Show logs since (e.g., '1 hour ago', '2025-12-01')"
    )
    logs_parser.add_argument("--until", help="Show logs until")
    logs_parser.set_defaults(func=cmd_logs)

    # Parse arguments
    args = parser.parse_args()

    # Show help if no command specified
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Execute command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print()
        print_warning("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
