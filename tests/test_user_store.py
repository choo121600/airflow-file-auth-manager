"""Tests for UserStore."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

from airflow_file_auth_manager.password import verify_password
from airflow_file_auth_manager.user_store import UserStore

if TYPE_CHECKING:
    pass


class TestUserStoreLoad:
    """Tests for UserStore loading."""

    def test_load_users_from_file(self, user_store: UserStore) -> None:
        """Should load users from YAML file."""
        users = user_store.get_all_users()
        assert len(users) == 4

    def test_load_missing_file(self, temp_dir: Path) -> None:
        """Should handle missing file gracefully."""
        store = UserStore(temp_dir / "nonexistent.yaml")
        users = store.get_all_users()
        assert len(users) == 0

    def test_load_empty_file(self, temp_dir: Path) -> None:
        """Should handle empty file."""
        empty_file = temp_dir / "empty.yaml"
        empty_file.write_text("")
        store = UserStore(empty_file)
        users = store.get_all_users()
        assert len(users) == 0

    def test_load_invalid_yaml(self, temp_dir: Path) -> None:
        """Should handle invalid YAML."""
        invalid_file = temp_dir / "invalid.yaml"
        invalid_file.write_text("{ invalid yaml [")
        store = UserStore(invalid_file)
        users = store.get_all_users()
        assert len(users) == 0


class TestUserStoreGetUser:
    """Tests for getting users."""

    def test_get_existing_user(self, user_store: UserStore) -> None:
        """Should return existing user."""
        user = user_store.get_user("admin")
        assert user is not None
        assert user.username == "admin"
        assert user.role == "admin"

    def test_get_nonexistent_user(self, user_store: UserStore) -> None:
        """Should return None for nonexistent user."""
        user = user_store.get_user("nonexistent")
        assert user is None


class TestUserStoreAuthenticate:
    """Tests for user authentication."""

    def test_authenticate_valid_credentials(self, user_store: UserStore) -> None:
        """Should authenticate with valid credentials."""
        user = user_store.authenticate("admin", "admin123")
        assert user is not None
        assert user.username == "admin"

    def test_authenticate_invalid_password(self, user_store: UserStore) -> None:
        """Should reject invalid password."""
        user = user_store.authenticate("admin", "wrong_password")
        assert user is None

    def test_authenticate_nonexistent_user(self, user_store: UserStore) -> None:
        """Should reject nonexistent user."""
        user = user_store.authenticate("nonexistent", "password")
        assert user is None

    def test_authenticate_inactive_user(self, user_store: UserStore) -> None:
        """Should reject inactive user."""
        user = user_store.authenticate("inactive", "inactive123")
        assert user is None


class TestUserStoreAddUser:
    """Tests for adding users."""

    def test_add_new_user(self, user_store: UserStore) -> None:
        """Should add a new user."""
        user = user_store.add_user(
            username="newuser",
            password="newpass123",
            role="editor",
            email="new@example.com",
        )
        assert user.username == "newuser"
        assert user.role == "editor"
        assert verify_password("newpass123", user.password_hash)

    def test_add_duplicate_user(self, user_store: UserStore) -> None:
        """Should raise error for duplicate username."""
        with pytest.raises(ValueError, match="already exists"):
            user_store.add_user(
                username="admin",
                password="newpass",
                role="admin",
            )

    def test_add_user_invalid_role(self, user_store: UserStore) -> None:
        """Should raise error for invalid role."""
        with pytest.raises(ValueError, match="Invalid role"):
            user_store.add_user(
                username="baduser",
                password="pass123",
                role="superuser",  # Invalid
            )


class TestUserStoreUpdateUser:
    """Tests for updating users."""

    def test_update_user_role(self, user_store: UserStore) -> None:
        """Should update user role."""
        user = user_store.update_user("editor", role="admin")
        assert user.role == "admin"

    def test_update_user_password(self, user_store: UserStore) -> None:
        """Should update user password."""
        user_store.update_user("editor", password="newpass123")
        # Verify new password works
        user = user_store.authenticate("editor", "newpass123")
        assert user is not None

    def test_update_nonexistent_user(self, user_store: UserStore) -> None:
        """Should raise error for nonexistent user."""
        with pytest.raises(ValueError, match="not found"):
            user_store.update_user("nonexistent", role="admin")


class TestUserStoreDeleteUser:
    """Tests for deleting users."""

    def test_delete_user(self, user_store: UserStore) -> None:
        """Should delete user."""
        user_store.delete_user("viewer")
        assert user_store.get_user("viewer") is None

    def test_delete_nonexistent_user(self, user_store: UserStore) -> None:
        """Should raise error for nonexistent user."""
        with pytest.raises(ValueError, match="not found"):
            user_store.delete_user("nonexistent")


class TestUserStoreSave:
    """Tests for saving users."""

    def test_save_users(self, user_store: UserStore, users_file: Path) -> None:
        """Should save users to file."""
        user_store.add_user(
            username="saveduser",
            password="pass123",
            role="viewer",
        )
        user_store.save()

        # Reload and verify
        new_store = UserStore(users_file)
        user = new_store.get_user("saveduser")
        assert user is not None
        assert user.role == "viewer"

    def test_save_creates_directory(self, temp_dir: Path) -> None:
        """Should create parent directories if needed."""
        nested_file = temp_dir / "nested" / "deep" / "users.yaml"
        store = UserStore(nested_file)
        store.add_user(
            username="test",
            password="pass123",
            role="admin",
        )
        store.save()
        assert nested_file.exists()
