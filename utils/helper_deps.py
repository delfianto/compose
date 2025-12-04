#!/usr/bin/env python3

"""
helper_deps.py - Dependency management logic
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

from helper_base import (
    check_root,
    get_compose_service_name,
    print_error,
    print_info,
    print_success,
    print_warning,
    systemctl,
)


def get_override_dir(project: str) -> Path:
    """Get override directory for a service."""
    service = get_compose_service_name(project)
    return Path(f"/etc/systemd/system/{service}.d")


def get_override_file(project: str) -> Path:
    """Get dependencies override file for a service."""
    return get_override_dir(project) / "dependencies.conf"


def service_template_exists() -> bool:
    """Check if the docker-compose@.service template unit exists."""
    template_path = Path("/etc/systemd/system/docker-compose@.service")
    return template_path.exists()


def parse_override_file(override_file: Path) -> Dict[str, List[str]]:
    """
    Parse systemd override file and extract dependencies by type.

    Returns:
        Dict with keys 'Requires', 'Wants', 'After' containing lists of services.
    """
    deps: Dict[str, List[str]] = {"Requires": [], "Wants": [], "After": []}

    if not override_file.exists():
        return deps

    current_section: Optional[str] = None
    with override_file.open() as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            # Track sections
            if line.startswith("[") and line.endswith("]"):
                current_section = line.strip("[]")
                continue

            # Only process lines in [Unit] section
            if current_section != "Unit":
                continue

            # Parse directives
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key in deps and value:
                    deps[key].append(value)

    return deps


def write_override_file(override_file: Path, deps: Dict[str, List[str]]):
    """
    Write systemd override file with proper formatting.

    Args:
        override_file: Path to the override file
        deps: Dictionary of dependency types and their values
    """
    lines: List[str] = ["[Unit]"]

    for dep_type in ["Requires", "Wants", "After"]:
        for service in deps.get(dep_type, []):
            lines.append(f"{dep_type}={service}")

    override_file.write_text("\n".join(lines) + "\n")


def add_dependency(service: str, dependency: str, dep_type: str = "wants"):
    """
    Add a dependency between services.

    Args:
        service: The service that will depend on another (project name)
        dependency: The service to depend on (project name)
        dep_type: Either 'requires' (hard) or 'wants' (soft)
    """
    check_root()

    service = service.strip()
    dependency = dependency.strip()

    if not service or not dependency:
        print_error("Service and dependency names must not be empty")
        sys.exit(1)

    if service == dependency:
        print_error("Service cannot depend on itself")
        sys.exit(1)

    if dep_type not in ["requires", "wants"]:
        print_error("Dependency type must be 'requires' or 'wants'")
        sys.exit(1)

    if not service_template_exists():
        print_error(
            "Service template docker-compose@.service not found. Is compose-systemd installed?"
        )
        sys.exit(1)

    dep_unit = get_compose_service_name(dependency)
    override_dir = get_override_dir(service)
    override_file = get_override_file(service)

    override_dir.mkdir(parents=True, exist_ok=True)

    deps = parse_override_file(override_file)
    dep_directive = dep_type.capitalize()

    if dep_unit in deps.get(dep_directive, []):
        print_warning(
            f"Dependency already exists: {service} -> {dependency} ({dep_type})"
        )
        return

    deps.setdefault(dep_directive, []).append(dep_unit)

    # Always add After directive for ordering
    deps.setdefault("After", [])
    if dep_unit not in deps["After"]:
        deps["After"].append(dep_unit)

    write_override_file(override_file, deps)

    try:
        systemctl("daemon-reload")
        print_success(f"Added dependency: {service} -> {dependency} ({dep_type})")
    except Exception as e:
        print_error(f"Failed to reload systemd: {e}")
        sys.exit(1)


def remove_dependency(service: str, dependency: str):
    """
    Remove a dependency between services.

    Args:
        service: The service to remove dependency from
        dependency: The dependency to remove
    """
    check_root()

    service = service.strip()
    dependency = dependency.strip()

    dep_unit = get_compose_service_name(dependency)
    override_file = get_override_file(service)

    if not override_file.exists():
        print_error(f"No dependencies found for {service}")
        sys.exit(1)

    deps = parse_override_file(override_file)
    found = False

    for dep_type in ["Requires", "Wants", "After"]:
        if dep_unit in deps.get(dep_type, []):
            deps[dep_type].remove(dep_unit)
            found = True

    if not found:
        print_warning(f"Dependency not found: {service} -> {dependency}")
        return

    has_deps = any(deps.get(dt) for dt in ["Requires", "Wants"])

    if has_deps:
        write_override_file(override_file, deps)
    else:
        override_file.unlink(missing_ok=True)
        try:
            override_file.parent.rmdir()
        except OSError:
            pass

    try:
        systemctl("daemon-reload")
        print_success(f"Removed dependency: {service} -> {dependency}")
    except Exception as e:
        print_error(f"Failed to reload systemd: {e}")
        sys.exit(1)


def list_dependencies(service: str):
    """
    List dependencies for a service (using systemd show).

    Args:
        service: The service to list dependencies for
    """
    service_unit = get_compose_service_name(service)

    print_info(f"Dependencies for {service}:")
    print()

    try:
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

        found_any = False
        for line in result.stdout.split("\n"):
            if not line.strip() or "=" not in line:
                continue

            directive, deps = line.split("=", 1)
            compose_deps = [d for d in deps.split() if "docker-compose@" in d]

            if compose_deps:
                found_any = True
                print(f"{directive}:")
                for dep in compose_deps:
                    clean = dep.replace("docker-compose@", "").replace(".service", "")
                    print(f" - {clean}")

        if not found_any:
            print_warning(" No compose dependencies found")

    except Exception as e:
        print_error(f"Error listing dependencies: {e}")
        sys.exit(1)


def check_dependency_chain(service: str):
    """
    Check full dependency chain for a service.

    Args:
        service: The service to check dependencies for
    """
    service_unit = get_compose_service_name(service)

    print_info(f"Dependency chain for {service}:")
    print()

    try:
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
                clean = (
                    dep.strip()
                    .replace("├", "")
                    .replace("└", "")
                    .replace("│", "")
                    .replace("─", "")
                    .strip()
                )
                print(f" {clean}")
        else:
            print_warning(" No compose dependencies found")

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
                clean = (
                    dep.strip()
                    .replace("├", "")
                    .replace("└", "")
                    .replace("│", "")
                    .replace("─", "")
                    .strip()
                )
                print(f" {clean}")
        else:
            print_warning(" No reverse dependencies found")

    except Exception as e:
        print_error(f"Error checking dependencies: {e}")
        sys.exit(1)


def detect_cycles(
    service: str, visited: Optional[Set[str]] = None, path: Optional[List[str]] = None
) -> Optional[List[str]]:
    """
    Detect circular dependencies based on override files (Requires/Wants only).

    Returns list representing the cycle if found, None otherwise.
    """
    if visited is None:
        visited = set()
    if path is None:
        path = []

    if service in path:
        idx = path.index(service)
        return path[idx:] + [service]

    if service in visited:
        return None

    visited.add(service)
    path.append(service)

    override_file = get_override_file(service)
    deps = parse_override_file(override_file)

    for dep_list in [deps.get("Requires", []), deps.get("Wants", [])]:
        for dep_unit in dep_list:
            name = (
                dep_unit.replace("docker-compose@", "").replace(".service", "").strip()
            )
            cycle = detect_cycles(name, visited, path.copy())
            if cycle:
                return cycle

    return None
