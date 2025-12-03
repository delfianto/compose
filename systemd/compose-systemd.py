#!/usr/bin/env python3
"""
compose-systemd.py - Docker Compose systemd management tool

Installation and dependency management for docker-compose services
running under systemd with template units.
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from string import Template
from typing import List


# ANSI color codes
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"  # No Color


# Installation paths
SCRIPT_DEST = Path("/usr/local/bin/compose.py")
SYSTEMD_UNIT_DEST = Path("/etc/systemd/system/docker-compose@.service")
ENV_FILE_DEST = Path("/etc/systemd/system/docker-compose.env")

# Get script directory for template files
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


def check_dependencies() -> List[str]:
    """Check for required system dependencies."""
    missing = []

    for cmd in ["docker", "systemctl", "python3"]:
        if not shutil.which(cmd):
            missing.append(cmd)

    return missing


def backup_file(filepath: Path):
    """Backup existing file with timestamp."""
    if filepath.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = filepath.with_suffix(f"{filepath.suffix}.backup.{timestamp}")
        print_warning(f"Backing up existing file to: {backup_path}")
        shutil.copy2(filepath, backup_path)


def systemctl(*args, check=True) -> subprocess.CompletedProcess:
    """Execute systemctl command."""
    return subprocess.run(
        ["systemctl", *args], capture_output=True, text=True, check=check
    )


def get_service_name(project: str) -> str:
    """Convert project name to systemd service name."""
    return f"docker-compose@{project}.service"


def get_override_dir(project: str) -> Path:
    """Get override directory for a service."""
    service = get_service_name(project)
    return Path(f"/etc/systemd/system/{service}.d")


def get_override_file(project: str) -> Path:
    """Get dependencies override file for a service."""
    return get_override_dir(project) / "dependencies.conf"


def load_template(filename: str) -> str:
    """
    Load template file from script directory.

    Args:
        filename: Name of the template file

    Returns:
        Template content as string
    """
    template_path = SCRIPT_DIR / filename

    if not template_path.exists():
        print_error(f"Template file not found: {template_path}")
        print_info(f"Please ensure {filename} is in the same directory as this script")
        sys.exit(1)

    print_info(f"Loading template: {template_path}")
    return template_path.read_text()


def generate_env_file(args) -> str:
    """
    Generate environment file content from template and arguments.

    This generates the global environment file that all docker-compose services
    will inherit. The file provides default values that can be overridden by
    individual project .env files.

    Default directories:
        DATA_BASE_DIR: /srv/appdata
            - Where application data (databases, configs, etc.) is stored
            - Each compose project typically creates a subdirectory here
            - Example: /srv/appdata/mongodb, /srv/appdata/postgres

        PROJ_BASE_DIR: /srv/compose
            - Where compose project files are located
            - This is where compose.py will look for projects
            - Example: /srv/compose/database, /srv/compose/genai-ollama

    ACME configuration:
        TRAEFIK_ACME_DOMAIN: Required, no default
            - Primary domain for Let's Encrypt certificates
            - Example: example.com or *.example.com for wildcard

        TRAEFIK_ACME_EMAIL: Required, no default
            - Email for Let's Encrypt notifications (renewals, issues)

        TRAEFIK_ACME_SERVER: https://acme-v02.api.letsencrypt.org/directory
            - Let's Encrypt production server
            - Use https://acme-staging-v02.api.letsencrypt.org/directory for testing

    Args:
        args: Parsed command line arguments

    Returns:
        Filled environment file content
    """
    template_str = load_template("docker-compose.env.template")

    # Create Template object using Python's string.Template
    template = Template(template_str)

    # Prepare substitution values with defaults
    # Only DATA_BASE_DIR, PROJ_BASE_DIR, and ACME_SERVER have defaults
    values = {
        "data_base_dir": args.data_base_dir or "/srv/appdata",
        "proj_base_dir": args.proj_base_dir or "/srv/compose",
        "acme_domain": args.acme_domain,  # Required, no default
        "acme_email": args.acme_email,  # Required, no default
        "acme_server": args.acme_server
        or "https://acme-v02.api.letsencrypt.org/directory",
    }

    try:
        return template.substitute(**values)
    except KeyError as e:
        print_error(f"Missing required template variable: {e}")
        sys.exit(1)


# Installations
def cmd_install(args):
    """Install compose.py and systemd template."""
    check_root()

    # Validate required ACME arguments
    if not args.acme_domain:
        print_error("--acme-domain is required for installation")
        print_info("Example: --acme-domain example.com")
        sys.exit(1)

    if not args.acme_email:
        print_error("--acme-email is required for installation")
        print_info("Example: --acme-email admin@example.com")
        sys.exit(1)

    print_section("Docker Compose Systemd Installation")
    print()

    # Check dependencies
    missing = check_dependencies()
    if missing:
        print_error(f"Missing required dependencies: {', '.join(missing)}")
        sys.exit(1)

    # Check for required files
    compose_src = SCRIPT_DIR / "compose.py"
    systemd_template = SCRIPT_DIR / "docker-compose@.service"
    env_template = SCRIPT_DIR / "docker-compose.env.template"

    required_files = [
        ("compose.py", compose_src),
        ("docker-compose@.service", systemd_template),
        ("docker-compose.env.template", env_template),
    ]

    missing_files = []
    for name, path in required_files:
        if not path.exists():
            missing_files.append(name)

    if missing_files:
        print_error(f"Missing required files: {', '.join(missing_files)}")
        print_info(f"Please ensure all files are in: {SCRIPT_DIR}")
        sys.exit(1)

    # Install compose.py
    print_info(f"Installing compose.py to {SCRIPT_DEST}")
    backup_file(SCRIPT_DEST)
    shutil.copy2(compose_src, SCRIPT_DEST)
    os.chmod(SCRIPT_DEST, 0o755)
    print_success("compose.py installed")

    # Install systemd unit template
    print_info(f"Installing systemd unit template to {SYSTEMD_UNIT_DEST}")
    backup_file(SYSTEMD_UNIT_DEST)
    shutil.copy2(systemd_template, SYSTEMD_UNIT_DEST)
    os.chmod(SYSTEMD_UNIT_DEST, 0o644)
    print_success("Systemd unit template installed")

    # Generate and install environment file
    print_info(f"Generating environment file at {ENV_FILE_DEST}")
    backup_file(ENV_FILE_DEST)

    env_content = generate_env_file(args)
    ENV_FILE_DEST.write_text(env_content)
    os.chmod(ENV_FILE_DEST, 0o644)

    print_success("Environment file created")
    print_info(f"ACME domain: {args.acme_domain}")
    print_info(f"ACME email: {args.acme_email}")

    # Reload systemd
    print_info("Reloading systemd daemon")
    try:
        systemctl("daemon-reload")
        print_success("Systemd daemon reloaded")
    except subprocess.CalledProcessError:
        print_error("Failed to reload systemd daemon")
        sys.exit(1)

    print()
    print_section("Installation Complete!")
    print()
    print_info("Next steps:")
    print("  1. Review environment file: sudo nano", ENV_FILE_DEST)
    print("  2. Disable restart policies in docker-compose.yml files")
    print(
        "  3. Enable services: sudo systemctl enable docker-compose@<project>.service"
    )
    print(
        "  4. Manage dependencies: sudo compose-systemd.py deps add <service> <dependency>"
    )
    print()


def cmd_check_status(args):
    """Check installation status."""
    print_section("Installation Status Check")
    print()

    # Check if running as root for some checks
    is_root = os.geteuid() == 0

    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        print_error(f"Missing dependencies: {', '.join(missing_deps)}")
    else:
        print_success("All system dependencies found")

    # Check template files
    print()
    print_info("Template files (in script directory):")
    template_files = [
        ("compose.py", SCRIPT_DIR / "compose.py"),
        ("systemd template", SCRIPT_DIR / "docker-compose@.service"),
        ("env template", SCRIPT_DIR / "docker-compose.env.template"),
    ]

    for name, path in template_files:
        if path.exists():
            print_success(f"  {name}: {path}")
        else:
            print_warning(f"  {name}: NOT FOUND")

    # Check installed files
    print()
    print_info("Installed files:")
    files_to_check = [
        ("compose.py", SCRIPT_DEST),
        ("systemd unit template", SYSTEMD_UNIT_DEST),
        ("environment file", ENV_FILE_DEST),
    ]

    for name, path in files_to_check:
        if path.exists():
            print_success(f"  {name}: {path}")
        else:
            print_error(f"  {name}: NOT FOUND")

    # Show environment file content if exists
    if ENV_FILE_DEST.exists():
        print()
        print_info("Environment configuration:")
        with ENV_FILE_DEST.open() as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    print(f"  {line}")

    # List enabled services
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


# Dependency Management
def cmd_deps_add(args):
    """Add a dependency between services."""
    check_root()

    service = args.service
    dependency = args.dependency
    dep_type = args.type

    if dep_type not in ["requires", "wants"]:
        print_error("Dependency type must be 'requires' or 'wants'")
        sys.exit(1)

    dep_unit = get_service_name(dependency)
    override_dir = get_override_dir(service)
    override_file = get_override_file(service)

    # Create override directory
    override_dir.mkdir(parents=True, exist_ok=True)

    # Check if dependency already exists
    if override_file.exists():
        content = override_file.read_text()
        if dep_unit in content:
            print_warning("Dependency already exists, updating...")
            # Remove old entries for this dependency
            lines = [line for line in content.split("\n") if dep_unit not in line]
            content = "\n".join(lines)
            override_file.write_text(content)

    # Capitalize first letter for systemd directive
    dep_directive = dep_type.capitalize()

    # Add new dependency
    with override_file.open("a") as f:
        f.write(f"{dep_directive}={dep_unit}\n")
        f.write(f"After={dep_unit}\n")

    # Reload systemd
    systemctl("daemon-reload")

    print_success(f"Added dependency: {service} -> {dependency} ({dep_type})")


def cmd_deps_remove(args):
    """Remove a dependency between services."""
    check_root()

    service = args.service
    dependency = args.dependency

    dep_unit = get_service_name(dependency)
    override_file = get_override_file(service)

    if not override_file.exists():
        print_error(f"No dependencies found for {service}")
        sys.exit(1)

    # Remove lines containing the dependency
    content = override_file.read_text()
    lines = [line for line in content.split("\n") if dep_unit not in line]
    new_content = "\n".join(lines).strip()

    if new_content:
        override_file.write_text(new_content + "\n")
    else:
        # Remove file if empty
        override_file.unlink()
        try:
            override_file.parent.rmdir()
        except OSError:
            pass  # Directory not empty

    # Reload systemd
    systemctl("daemon-reload")

    print_success(f"Removed dependency: {service} -> {dependency}")


def cmd_deps_list(args):
    """List dependencies for a service."""
    service = args.service
    service_unit = get_service_name(service)

    print_info(f"Dependencies for {service}:")
    print()

    try:
        # Get dependencies using systemctl show
        result = systemctl(
            "show",
            service_unit,
            "-p",
            "Requires",
            "-p",
            "Wants",
            "-p",
            "After",
            "--no-pager",
            check=False,
        )

        if result.returncode != 0:
            print_error(f"Service {service_unit} not found")
            sys.exit(1)

        for line in result.stdout.split("\n"):
            if not line.strip():
                continue

            if "=" in line:
                directive, deps = line.split("=", 1)

                # Filter only docker-compose services
                compose_deps = [d for d in deps.split() if "docker-compose@" in d]

                if compose_deps:
                    print(f"{Colors.BLUE}{directive}:{Colors.NC}")
                    for dep in compose_deps:
                        clean_dep = dep.replace("docker-compose@", "").replace(
                            ".service", ""
                        )
                        print(f"  - {clean_dep}")

    except Exception as e:
        print_error(f"Error listing dependencies: {e}")
        sys.exit(1)


def cmd_deps_check(args):
    """Check dependency chain for a service."""
    service = args.service
    service_unit = get_service_name(service)

    print_info(f"Dependency chain for {service}:")
    print()

    try:
        # Show the dependency tree
        result = systemctl(
            "list-dependencies", service_unit, "--plain", "--no-pager", check=False
        )

        if result.returncode != 0:
            print_error(f"Service {service_unit} not found")
            sys.exit(1)

        compose_deps = [
            line for line in result.stdout.split("\n") if "docker-compose@" in line
        ]
        if compose_deps:
            for dep in compose_deps:
                clean_dep = (
                    dep.strip()
                    .replace("├", "")
                    .replace("└", "")
                    .replace("│", "")
                    .replace("─", "")
                    .strip()
                )
                print(f"  {clean_dep}")
        else:
            print_warning("  No compose dependencies found")

        print()
        print_info("Reverse dependencies (services that depend on this):")
        print()

        result = systemctl(
            "list-dependencies",
            "--reverse",
            service_unit,
            "--plain",
            "--no-pager",
            check=False,
        )

        compose_deps = [
            line for line in result.stdout.split("\n") if "docker-compose@" in line
        ]

        if compose_deps:
            for dep in compose_deps:
                clean_dep = (
                    dep.strip()
                    .replace("├", "")
                    .replace("└", "")
                    .replace("│", "")
                    .replace("─", "")
                    .strip()
                )
                print(f"  {clean_dep}")
        else:
            print_warning("  No reverse dependencies found")

    except Exception as e:
        print_error(f"Error checking dependencies: {e}")
        sys.exit(1)


# Main CLI
def main():
    parser = argparse.ArgumentParser(
        prog="compose-systemd",
        description="Docker Compose systemd management tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Install with required ACME configuration
  sudo compose-systemd.py --install \\
    --acme-domain example.com \\
    --acme-email admin@example.com

  # Install with custom paths
  sudo compose-systemd.py --install \\
    --acme-domain example.com \\
    --acme-email admin@example.com \\
    --data-base-dir /opt/appdata \\
    --proj-base-dir /opt/compose

  # Check installation status
  compose-systemd.py --check-status

  # Dependency management
  sudo compose-systemd.py deps add genai-open-webui database requires
  sudo compose-systemd.py deps add genai-embedding genai-ollama wants
  compose-systemd.py deps list genai-open-webui
  compose-systemd.py deps check genai-open-webui
  sudo compose-systemd.py deps remove genai-open-webui database
""",
    )

    # Global options
    parser.add_argument(
        "--install", action="store_true", help="Install compose.py and systemd template"
    )

    parser.add_argument(
        "--check-status", action="store_true", help="Check installation status"
    )

    # Installation configuration arguments
    parser.add_argument(
        "--acme-domain",
        metavar="DOMAIN",
        help="ACME domain for Let's Encrypt SSL (required for --install)",
    )

    parser.add_argument(
        "--acme-email",
        metavar="EMAIL",
        help="ACME email for Let's Encrypt notifications (required for --install)",
    )

    parser.add_argument(
        "--acme-server",
        metavar="URL",
        help="ACME server URL (default: Let's Encrypt production)",
    )

    parser.add_argument(
        "--data-base-dir",
        metavar="PATH",
        help="Base directory for application data (default: /srv/appdata)",
    )

    parser.add_argument(
        "--proj-base-dir",
        metavar="PATH",
        help="Base directory for compose projects (default: /srv/compose)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # deps command group
    deps_parser = subparsers.add_parser("deps", help="Manage service dependencies")
    deps_subparsers = deps_parser.add_subparsers(dest="deps_command", required=True)

    # deps add
    deps_add_parser = deps_subparsers.add_parser("add", help="Add a dependency")
    deps_add_parser.add_argument(
        "service", help="Service name (e.g., genai-open-webui)"
    )
    deps_add_parser.add_argument("dependency", help="Dependency name (e.g., database)")
    deps_add_parser.add_argument(
        "type",
        nargs="?",
        default="wants",
        choices=["requires", "wants"],
        help="Dependency type (default: wants)",
    )
    deps_add_parser.set_defaults(func=cmd_deps_add)

    # deps remove
    deps_remove_parser = deps_subparsers.add_parser(
        "remove", help="Remove a dependency"
    )
    deps_remove_parser.add_argument("service", help="Service name")
    deps_remove_parser.add_argument("dependency", help="Dependency name")
    deps_remove_parser.set_defaults(func=cmd_deps_remove)

    # deps list
    deps_list_parser = deps_subparsers.add_parser(
        "list", help="List dependencies for a service"
    )
    deps_list_parser.add_argument("service", help="Service name")
    deps_list_parser.set_defaults(func=cmd_deps_list)

    # deps check
    deps_check_parser = deps_subparsers.add_parser(
        "check", help="Check dependency chain"
    )
    deps_check_parser.add_argument("service", help="Service name")
    deps_check_parser.set_defaults(func=cmd_deps_check)

    # Parse arguments
    args = parser.parse_args()

    # Handle no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # Handle global flags
    if args.install:
        cmd_install(args)
    elif args.check_status:
        cmd_check_status(args)
    elif args.command == "deps":
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warning("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
