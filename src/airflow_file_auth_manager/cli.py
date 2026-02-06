"""CLI commands for managing file auth users."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from airflow_file_auth_manager.password import hash_password
from airflow_file_auth_manager.user_store import UserStore

if TYPE_CHECKING:
    pass


def add_user(args: argparse.Namespace) -> None:
    """Add a new user to the users file."""
    store = UserStore(args.file)

    # Get password interactively if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: Passwords do not match", file=sys.stderr)
            sys.exit(1)

    if not password:
        print("Error: Password cannot be empty", file=sys.stderr)
        sys.exit(1)

    try:
        user = store.add_user(
            username=args.username,
            password=password,
            role=args.role,
            email=args.email or "",
            first_name=args.firstname or "",
            last_name=args.lastname or "",
        )
        store.save()
        print(f"User '{user.username}' added with role '{user.role}'")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def update_user(args: argparse.Namespace) -> None:
    """Update an existing user."""
    store = UserStore(args.file)

    # Get password interactively if flag is set
    password = None
    if args.password:
        password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: Passwords do not match", file=sys.stderr)
            sys.exit(1)

    try:
        user = store.update_user(
            username=args.username,
            password=password,
            role=args.role,
            email=args.email,
            first_name=args.firstname,
            last_name=args.lastname,
            active=args.active,
        )
        store.save()
        print(f"User '{user.username}' updated")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def delete_user(args: argparse.Namespace) -> None:
    """Delete a user."""
    store = UserStore(args.file)

    if not args.yes:
        confirm = input(f"Delete user '{args.username}'? [y/N]: ")
        if confirm.lower() != "y":
            print("Aborted")
            return

    try:
        store.delete_user(args.username)
        store.save()
        print(f"User '{args.username}' deleted")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def list_users(args: argparse.Namespace) -> None:
    """List all users."""
    store = UserStore(args.file)
    users = store.get_all_users()

    if not users:
        print("No users found")
        return

    # Table header
    print(f"{'Username':<20} {'Role':<10} {'Email':<30} {'Active':<8}")
    print("-" * 70)

    for user in users:
        active = "Yes" if user.is_active else "No"
        print(f"{user.username:<20} {user.role:<10} {user.email:<30} {active:<8}")

    print(f"\nTotal: {len(users)} user(s)")


def hash_password_cmd(args: argparse.Namespace) -> None:
    """Generate a password hash."""
    password = args.password
    if not password:
        password = getpass.getpass("Password: ")

    if not password:
        print("Error: Password cannot be empty", file=sys.stderr)
        sys.exit(1)

    hashed = hash_password(password)
    print(hashed)


def init_file(args: argparse.Namespace) -> None:
    """Initialize a new users file with an admin user."""
    file_path = Path(args.file)

    if file_path.exists() and not args.force:
        print(f"Error: File already exists: {file_path}", file=sys.stderr)
        print("Use --force to overwrite", file=sys.stderr)
        sys.exit(1)

    # Get admin password
    password = args.password
    if not password:
        password = getpass.getpass("Admin password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: Passwords do not match", file=sys.stderr)
            sys.exit(1)

    if not password:
        print("Error: Password cannot be empty", file=sys.stderr)
        sys.exit(1)

    store = UserStore(file_path)
    store.add_user(
        username="admin",
        password=password,
        role="admin",
        email=args.email or "",
    )
    store.save()
    print(f"Created users file: {file_path}")
    print("Admin user created with username 'admin'")


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="airflow file-auth",
        description="Manage file-based authentication users",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # add-user command
    add_parser = subparsers.add_parser("add-user", help="Add a new user")
    add_parser.add_argument("-f", "--file", required=True, help="Path to users YAML file")
    add_parser.add_argument("-u", "--username", required=True, help="Username")
    add_parser.add_argument("-p", "--password", help="Password (will prompt if not provided)")
    add_parser.add_argument(
        "-r", "--role",
        required=True,
        choices=["admin", "editor", "viewer"],
        help="User role",
    )
    add_parser.add_argument("-e", "--email", help="Email address")
    add_parser.add_argument("--firstname", help="First name")
    add_parser.add_argument("--lastname", help="Last name")
    add_parser.set_defaults(func=add_user)

    # update-user command
    update_parser = subparsers.add_parser("update-user", help="Update a user")
    update_parser.add_argument("-f", "--file", required=True, help="Path to users YAML file")
    update_parser.add_argument("-u", "--username", required=True, help="Username to update")
    update_parser.add_argument("-p", "--password", action="store_true", help="Change password")
    update_parser.add_argument(
        "-r", "--role",
        choices=["admin", "editor", "viewer"],
        help="New role",
    )
    update_parser.add_argument("-e", "--email", help="New email")
    update_parser.add_argument("--firstname", help="New first name")
    update_parser.add_argument("--lastname", help="New last name")
    update_parser.add_argument("--active", type=lambda x: x.lower() == "true", help="Set active status (true/false)")
    update_parser.set_defaults(func=update_user)

    # delete-user command
    delete_parser = subparsers.add_parser("delete-user", help="Delete a user")
    delete_parser.add_argument("-f", "--file", required=True, help="Path to users YAML file")
    delete_parser.add_argument("-u", "--username", required=True, help="Username to delete")
    delete_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    delete_parser.set_defaults(func=delete_user)

    # list-users command
    list_parser = subparsers.add_parser("list-users", help="List all users")
    list_parser.add_argument("-f", "--file", required=True, help="Path to users YAML file")
    list_parser.set_defaults(func=list_users)

    # hash-password command
    hash_parser = subparsers.add_parser("hash-password", help="Generate bcrypt password hash")
    hash_parser.add_argument("-p", "--password", help="Password to hash (will prompt if not provided)")
    hash_parser.set_defaults(func=hash_password_cmd)

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize users file with admin user")
    init_parser.add_argument("-f", "--file", required=True, help="Path for new users YAML file")
    init_parser.add_argument("-p", "--password", help="Admin password (will prompt if not provided)")
    init_parser.add_argument("-e", "--email", help="Admin email")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing file")
    init_parser.set_defaults(func=init_file)

    return parser


def main(args: list[str] | None = None) -> None:
    """Main entry point for CLI."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        sys.exit(1)

    parsed_args.func(parsed_args)


# Airflow plugin for CLI integration (optional)
try:
    from airflow.plugins_manager import AirflowPlugin

    class FileAuthCLIPlugin(AirflowPlugin):
        """Airflow plugin to register file-auth CLI commands."""

        name = "file_auth_cli"
        # Note: Airflow 3.x CLI plugin registration differs from 2.x
        # For now, the CLI can be used directly via `python -m airflow_file_auth_manager.cli`

except ImportError:
    # Airflow not installed, CLI can still be used standalone
    pass


if __name__ == "__main__":
    main()
