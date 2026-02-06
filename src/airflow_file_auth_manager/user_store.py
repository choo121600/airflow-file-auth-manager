"""YAML-based user storage management."""

from __future__ import annotations

import fcntl
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from airflow_file_auth_manager.password import hash_password, verify_password
from airflow_file_auth_manager.user import FileUser

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

DEFAULT_USERS_FILE = "users.yaml"

# Hot reload check interval in seconds
HOT_RELOAD_CHECK_INTERVAL = 5.0


class UserStore:
    """Manages user storage in YAML file.

    Features:
    - Atomic file writes (tempfile + rename)
    - File locking for concurrent access safety
    - Hot reload support (auto-detects file changes)
    """

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
        self._last_mtime: float = 0.0
        self._last_check_time: float = 0.0

    @property
    def file_path(self) -> Path:
        """Return the users file path."""
        return self._file_path

    def _check_hot_reload(self) -> None:
        """Check if file has changed and reload if necessary."""
        current_time = time.time()

        # Only check periodically to avoid excessive stat calls
        if current_time - self._last_check_time < HOT_RELOAD_CHECK_INTERVAL:
            return

        self._last_check_time = current_time

        if not self._file_path.exists():
            return

        try:
            current_mtime = self._file_path.stat().st_mtime
            if current_mtime > self._last_mtime:
                logger.info("Users file changed, reloading: %s", self._file_path)
                self.reload()
        except OSError as e:
            logger.debug("Failed to stat users file: %s", e)

    def _ensure_loaded(self) -> None:
        """Ensure users are loaded from file."""
        if not self._loaded:
            self.load()
        else:
            # Check for hot reload
            self._check_hot_reload()

    def load(self) -> None:
        """Load users from YAML file with file locking."""
        self._users = {}

        if not self._file_path.exists():
            logger.warning("Users file not found: %s", self._file_path)
            self._loaded = True
            return

        try:
            with open(self._file_path, encoding="utf-8") as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = yaml.safe_load(f) or {}
                    # Record file modification time for hot reload
                    self._last_mtime = self._file_path.stat().st_mtime
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

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
        """Save users to YAML file atomically with file locking.

        Uses tempfile + rename pattern for atomic writes to prevent
        file corruption on crash.
        """
        data = {
            "version": "1.0",
            "users": [user.to_dict() for user in self._users.values()],
        }

        # Ensure parent directory exists
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file first, then atomically rename
        fd = None
        temp_path = None
        try:
            # Create temp file in same directory for atomic rename
            fd, temp_path = tempfile.mkstemp(
                suffix=".tmp",
                prefix=".users_",
                dir=self._file_path.parent,
            )

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                fd = None  # os.fdopen takes ownership
                # Acquire exclusive lock for writing
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Set same permissions as original file or secure default
            if self._file_path.exists():
                original_mode = self._file_path.stat().st_mode
                os.chmod(temp_path, original_mode)
            else:
                # Secure default: readable only by owner
                os.chmod(temp_path, 0o600)

            # Atomic rename
            os.replace(temp_path, self._file_path)
            temp_path = None  # Successfully renamed

            # Update mtime tracking
            self._last_mtime = self._file_path.stat().st_mtime

            logger.info("Saved %d users to %s", len(self._users), self._file_path)

        except Exception:
            # Clean up temp file on error
            if fd is not None:
                os.close(fd)
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

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
            logger.warning("Authentication failed - user not found: %s", username)
            return None

        if not user.is_active:
            logger.warning("Authentication failed - user inactive: %s", username)
            return None

        if not verify_password(password, user.password_hash):
            logger.warning("Authentication failed - invalid password: %s", username)
            return None

        logger.info("User authenticated successfully: %s", username)
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
        logger.warning("AUDIT: User created: %s (role: %s)", username, role)
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
        changes = []

        if password is not None:
            user.password_hash = hash_password(password)
            changes.append("password")
        if role is not None:
            if role not in ("admin", "editor", "viewer"):
                raise ValueError(f"Invalid role: {role}")
            old_role = user.role
            user.role = role
            changes.append(f"role: {old_role} -> {role}")
        if email is not None:
            user.email = email
            changes.append("email")
        if first_name is not None:
            user.first_name = first_name
            changes.append("first_name")
        if last_name is not None:
            user.last_name = last_name
            changes.append("last_name")
        if active is not None:
            old_active = user.active
            user.active = active
            changes.append(f"active: {old_active} -> {active}")

        logger.warning("AUDIT: User updated: %s (changes: %s)", username, ", ".join(changes))
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
        logger.warning("AUDIT: User deleted: %s", username)

    def user_exists(self, username: str) -> bool:
        """Check if user exists."""
        self._ensure_loaded()
        return username in self._users
