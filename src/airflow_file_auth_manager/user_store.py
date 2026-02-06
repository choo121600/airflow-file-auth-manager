"""YAML-based user storage management."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from airflow_file_auth_manager.password import hash_password, verify_password
from airflow_file_auth_manager.user import FileUser

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

DEFAULT_USERS_FILE = "users.yaml"


class UserStore:
    """Manages user storage in YAML file."""

    def __init__(self, users_file: str | Path | None = None) -> None:
        """Initialize UserStore.

        Args:
            users_file: Path to YAML file. If None, uses AIRFLOW_FILE_AUTH_USERS_FILE
                       env var or defaults to 'users.yaml' in AIRFLOW_HOME.
        """
        if users_file:
            self._file_path = Path(users_file)
        else:
            env_path = os.environ.get("AIRFLOW_FILE_AUTH_USERS_FILE")
            if env_path:
                self._file_path = Path(env_path)
            else:
                airflow_home = os.environ.get("AIRFLOW_HOME", "~/airflow")
                self._file_path = Path(airflow_home).expanduser() / DEFAULT_USERS_FILE

        self._users: dict[str, FileUser] = {}
        self._loaded = False

    @property
    def file_path(self) -> Path:
        """Return the users file path."""
        return self._file_path

    def _ensure_loaded(self) -> None:
        """Ensure users are loaded from file."""
        if not self._loaded:
            self.load()

    def load(self) -> None:
        """Load users from YAML file."""
        self._users = {}

        if not self._file_path.exists():
            logger.warning("Users file not found: %s", self._file_path)
            self._loaded = True
            return

        try:
            with open(self._file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            version = data.get("version", "1.0")
            if version != "1.0":
                logger.warning("Unknown users file version: %s", version)

            users_data = data.get("users", [])
            for user_data in users_data:
                try:
                    user = FileUser.from_dict(user_data)
                    self._users[user.username] = user
                except (KeyError, ValueError) as e:
                    logger.error("Invalid user entry: %s - %s", user_data, e)

            logger.info("Loaded %d users from %s", len(self._users), self._file_path)
            self._loaded = True

        except yaml.YAMLError as e:
            logger.error("Failed to parse users file: %s", e)
            self._loaded = True
        except OSError as e:
            logger.error("Failed to read users file: %s", e)
            self._loaded = True

    def reload(self) -> None:
        """Reload users from file."""
        self._loaded = False
        self.load()

    def save(self) -> None:
        """Save users to YAML file."""
        data = {
            "version": "1.0",
            "users": [user.to_dict() for user in self._users.values()],
        }

        # Ensure parent directory exists
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self._file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)

        logger.info("Saved %d users to %s", len(self._users), self._file_path)

    def get_user(self, username: str) -> FileUser | None:
        """Get user by username."""
        self._ensure_loaded()
        return self._users.get(username)

    def get_all_users(self) -> list[FileUser]:
        """Get all users."""
        self._ensure_loaded()
        return list(self._users.values())

    def authenticate(self, username: str, password: str) -> FileUser | None:
        """Authenticate user with username and password.

        Args:
            username: Username to authenticate.
            password: Plain text password.

        Returns:
            FileUser if authentication succeeds, None otherwise.
        """
        self._ensure_loaded()
        user = self._users.get(username)

        if not user:
            logger.debug("User not found: %s", username)
            return None

        if not user.is_active:
            logger.debug("User is inactive: %s", username)
            return None

        if not verify_password(password, user.password_hash):
            logger.debug("Invalid password for user: %s", username)
            return None

        logger.info("User authenticated: %s", username)
        return user

    def add_user(
        self,
        username: str,
        password: str,
        role: str,
        email: str = "",
        first_name: str = "",
        last_name: str = "",
        active: bool = True,
    ) -> FileUser:
        """Add a new user.

        Args:
            username: Unique username.
            password: Plain text password (will be hashed).
            role: User role (admin, editor, viewer).
            email: Optional email address.
            first_name: Optional first name.
            last_name: Optional last name.
            active: Whether user is active.

        Returns:
            Created FileUser.

        Raises:
            ValueError: If username already exists.
        """
        self._ensure_loaded()

        if username in self._users:
            raise ValueError(f"User already exists: {username}")

        password_hash = hash_password(password)
        user = FileUser(
            username=username,
            password_hash=password_hash,
            role=role,
            email=email,
            first_name=first_name,
            last_name=last_name,
            active=active,
        )

        self._users[username] = user
        logger.info("Added user: %s with role: %s", username, role)
        return user

    def update_user(
        self,
        username: str,
        *,
        password: str | None = None,
        role: str | None = None,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        active: bool | None = None,
    ) -> FileUser:
        """Update an existing user.

        Args:
            username: Username to update.
            password: New password (will be hashed).
            role: New role.
            email: New email.
            first_name: New first name.
            last_name: New last name.
            active: New active status.

        Returns:
            Updated FileUser.

        Raises:
            ValueError: If user doesn't exist.
        """
        self._ensure_loaded()

        if username not in self._users:
            raise ValueError(f"User not found: {username}")

        user = self._users[username]

        if password is not None:
            user.password_hash = hash_password(password)
        if role is not None:
            if role not in ("admin", "editor", "viewer"):
                raise ValueError(f"Invalid role: {role}")
            user.role = role
        if email is not None:
            user.email = email
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if active is not None:
            user.active = active

        logger.info("Updated user: %s", username)
        return user

    def delete_user(self, username: str) -> None:
        """Delete a user.

        Args:
            username: Username to delete.

        Raises:
            ValueError: If user doesn't exist.
        """
        self._ensure_loaded()

        if username not in self._users:
            raise ValueError(f"User not found: {username}")

        del self._users[username]
        logger.info("Deleted user: %s", username)

    def user_exists(self, username: str) -> bool:
        """Check if user exists."""
        self._ensure_loaded()
        return username in self._users
