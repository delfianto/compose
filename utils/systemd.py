#!/usr/bin/env python3

"""
systemd.py - Docker Compose systemd management tool

Central management utility for installation and dependency configuration.
Wraps helper_inst.py and helper_deps.py functionality.
"""

import argparse
import sys

import helper_deps
import helper_inst
from helper_base import print_error, print_warning


def main():
    parser = argparse.ArgumentParser(
        prog="composeinst",
        description="Docker Compose systemd management tool",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Install Command ---
    install_parser = subparsers.add_parser(
        "install", help="Install compose and systemd template"
    )
    install_parser.add_argument(
        "--acme-domain",
        metavar="DOMAIN",
        help="ACME domain for Let's Encrypt SSL (required for fresh install, optional for reinstall)",
    )
    install_parser.add_argument(
        "--acme-email",
        metavar="EMAIL",
        help="ACME email for Let's Encrypt notifications (required for fresh install, optional for reinstall)",
    )
    install_parser.add_argument(
        "--acme-server",
        metavar="URL",
        help="ACME server URL (default: Let's Encrypt production)",
    )
    install_parser.add_argument(
        "--data-base-dir",
        metavar="PATH",
        help="Base directory for application data (default: /srv/appdata)",
    )
    install_parser.add_argument(
        "--proj-base-dir",
        metavar="PATH",
        help="Base directory for compose projects (default: /srv/compose)",
    )

    # --- Check Status Command ---
    subparsers.add_parser("check-status", help="Check installation status")

    # --- Dependencies Command ---
    deps_parser = subparsers.add_parser("deps", help="Manage service dependencies")
    deps_subs = deps_parser.add_subparsers(dest="deps_command", required=True)

    # deps add
    add_p = deps_subs.add_parser("add", help="Add a dependency")
    add_p.add_argument("service", help="Service name (e.g., genai-open-webui)")
    add_p.add_argument("dependency", help="Dependency name (e.g., database)")
    add_p.add_argument(
        "type",
        nargs="?",
        default="wants",
        choices=["requires", "wants"],
        help="Dependency type (default: wants)",
    )

    # deps remove
    rm_p = deps_subs.add_parser("remove", help="Remove a dependency")
    rm_p.add_argument("service", help="Service name")
    rm_p.add_argument("dependency", help="Dependency name")

    # deps list
    ls_p = deps_subs.add_parser("list", help="List dependencies for a service")
    ls_p.add_argument("service", help="Service name")

    # deps check
    chk_p = deps_subs.add_parser("check", help="Check dependency chain")
    chk_p.add_argument("service", help="Service name")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Dispatch to appropriate helper
    try:
        if args.command == "install":
            helper_inst.run_install(args)

        elif args.command == "check-status":
            helper_inst.run_check_status(args)

        elif args.command == "deps":
            if args.deps_command == "add":
                helper_deps.add_dependency(args.service, args.dependency, args.type)
            elif args.deps_command == "remove":
                helper_deps.remove_dependency(args.service, args.dependency)
            elif args.deps_command == "list":
                helper_deps.list_dependencies(args.service)
            elif args.deps_command == "check":
                helper_deps.check_dependency_chain(args.service)

    except KeyboardInterrupt:
        print()
        print_warning("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
