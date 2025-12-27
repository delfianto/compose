#!/usr/bin/env python3

"""
compose.py - Docker Compose command wrapper with automatic
env file discovery, and sensible default flags.
"""

import os
import subprocess
import sys
from pathlib import Path

DEFAULT_ARGS = {
    "up": ["--remove-orphans", "--detach"],
    "down": ["--remove-orphans", "--volumes"],
    "exec": ["/bin/bash"],
    "build": ["--no-cache"],
    "logs": ["-f", "--tail=100"],
    "ps": ["--format", "table {{.Name}}\\t{{.State}}\\t{{.Status}}\\t{{.Ports}}"],
    "pull": ["--ignore-pull-failures"],
    "restart": [],
    "start": [],
    "stop": [],
}

HELP_CONTENT = """compose - Enhanced Docker Compose wrapper

Usage: compose [args...]

Available commands:
  up, down, ps, build, logs, exec, ...

Smart features:
  • Includes some sensible command-specific default flags
  • Discovers any compose file inside the directory
  • Includes all .env* files as --env-file
  • Prints final command before execution
  • Supports hyphenated paths (e.g., genai-ollama → genai/ollama)

Examples:
  compose up              # Start with defaults
  compose ps              # Pretty table format
  compose logs            # Follow latest 100 lines
  compose down            # Clean shutdown

Environment variables:
  COMPOSE_PROJECT         # Override project name (e.g., genai-ollama)
  COMPOSE_BASE            # Base directory (default: current dir)
  DOCKER_PG_FORMAT        # Build progress style
  DOCKER_PS_FORMAT        # Override ps format
"""


def stderr(msg):
    print(msg, file=sys.stderr)


def stdout(msg):
    print(msg, file=sys.stdout)


def cat_help():
    """Display embedded help content."""
    print(HELP_CONTENT)


def resolve_project_directory():
    """
    Resolve the working directory for the compose project.

    If COMPOSE_PROJECT env var contains hyphens (e.g., 'genai-ollama'),
    treat it as a path with subdirectories (e.g., 'genai/ollama').

    Returns:
        Path object pointing to the project directory
    """
    base_dir = Path(os.getenv("COMPOSE_BASE", "."))
    project_name = os.getenv("COMPOSE_PROJECT", "")

    if not project_name:
        return Path.cwd()

    if "-" in project_name:
        project_path = project_name.replace("-", os.sep)
        target_dir = base_dir / project_path

        if target_dir.is_dir():
            stdout(f"# Resolved project path: {project_name} → {target_dir}")
            return target_dir
        else:
            stderr(f"Warning: Hyphenated path {target_dir} does not exist")
            stderr(f"Falling back to direct path: {base_dir / project_name}")

    return base_dir / project_name


def find_compose_file(project_dir):
    """Find docker-compose.yml or compose.yaml variants in project directory."""
    candidates = []
    patterns = (
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
    )

    try:
        files = os.listdir(project_dir)
    except FileNotFoundError:
        stderr(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)
    except PermissionError:
        stderr(f"Error: Permission denied accessing: {project_dir}")
        sys.exit(1)

    for f in files:
        if f in patterns:
            candidates.append(f)

    if len(candidates) == 0:
        stderr(f"Error: No compose file found in {project_dir}")
        sys.exit(1)

    if len(candidates) > 1:
        stderr(f"Error: Multiple compose files found: {', '.join(candidates)}")
        stderr("Please remove or rename conflicting files")
        sys.exit(1)

    return project_dir / candidates[0]


def find_env_files(project_dir):
    """Return all .env* files in project directory."""
    try:
        files = os.listdir(project_dir)
        env_files = [
            str(project_dir / f)
            for f in files
            if f.startswith(".env") and (project_dir / f).is_file()
        ]
        return env_files
    except (FileNotFoundError, PermissionError):
        return []


def deduplicate_flags(combined_args):
    """Deduplicate flags, preserving order and handling --flag=value patterns."""
    all_flags = []
    for flag in combined_args:
        if flag in all_flags:
            continue

        if "=" in flag:
            flag_name = flag.split("=")[0]
            if any(f.startswith(flag_name) for f in all_flags):
                continue

        all_flags.append(flag)

    return all_flags


def build_docker_command(cmd, extra_args, compose_file, env_files, project_dir):
    """
    Build the complete docker compose command with all flags and special case handling.

    Args:
        cmd: The docker compose subcommand (up, down, ps, etc.)
        extra_args: Additional user-provided arguments
        compose_file: Path to the compose file
        env_files: List of environment files to include
        project_dir: Working directory for the compose project

    Returns:
        Tuple of (command_list, working_directory)
    """
    docker_cmd = ["docker", "compose", "--file", str(compose_file)]

    for env_file in env_files:
        docker_cmd.extend(["--env-file", env_file])

    # Special case: Build progress from DOCKER_PG_FORMAT env var
    if cmd == "build" and os.getenv("DOCKER_PG_FORMAT"):
        docker_cmd.append(f"--progress={os.getenv('DOCKER_PG_FORMAT')}")

    docker_cmd.append(cmd)

    default_flags = DEFAULT_ARGS[cmd].copy()

    # Special case: ps format override from environment variable
    if cmd == "ps" and os.getenv("DOCKER_PS_FORMAT"):
        default_flags = [f for f in default_flags if f != "--format"]
        default_flags = [
            f
            for i, f in enumerate(default_flags)
            if i == 0 or default_flags[i - 1] != "--format"
        ]
        default_flags.extend(["--format", os.getenv("DOCKER_PS_FORMAT")])

    combined_args = default_flags + extra_args
    all_flags = deduplicate_flags(combined_args)
    docker_cmd.extend(all_flags)

    return docker_cmd, project_dir


def format_command_for_display(docker_cmd):
    """Format command list for display, quoting arguments with special characters."""
    quoted_cmd = []
    for arg in docker_cmd:
        if " " in arg or "\n" in arg or "\t" in arg:
            quoted_cmd.append(f'"{arg}"')
        else:
            quoted_cmd.append(arg)
    return " ".join(quoted_cmd)


def main():
    if len(sys.argv) < 2:
        cat_help()
        sys.exit(1)

    if sys.argv[1] == "--print-workdir":
        project_dir = resolve_project_directory()
        print(project_dir)
        sys.exit(0)

    cmd = sys.argv[1]
    extra_args = sys.argv[2:]

    if cmd not in DEFAULT_ARGS:
        stderr(f"Error: Invalid command '{cmd}'.")
        stderr("Valid commands: " + ", ".join(sorted(DEFAULT_ARGS.keys())))
        sys.exit(1)

    project_dir = resolve_project_directory()
    compose_file = find_compose_file(project_dir)
    env_files = find_env_files(project_dir)

    docker_cmd, working_dir = build_docker_command(
        cmd, extra_args, compose_file, env_files, project_dir
    )

    stdout(f"# Working directory: {working_dir}")
    stdout(format_command_for_display(docker_cmd))
    stdout("")

    try:
        subprocess.run(docker_cmd, check=True, cwd=working_dir)
    except subprocess.CalledProcessError as e:
        stderr(f"Command failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        stderr("Error: 'docker' command not found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
