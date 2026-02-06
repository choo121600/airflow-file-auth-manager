"""Pytest fixtures for file auth manager tests."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
import yaml

# Mock Airflow modules before importing our modules
# Airflow 3.0 is not yet released on PyPI
if "airflow" not in sys.modules:
    airflow_mock = MagicMock()
    sys.modules["airflow"] = airflow_mock
    sys.modules["airflow.configuration"] = MagicMock()
    sys.modules["airflow.auth"] = MagicMock()
    sys.modules["airflow.auth.managers"] = MagicMock()
    sys.modules["airflow.auth.managers.base_auth_manager"] = MagicMock()
    sys.modules["airflow.auth.managers.models"] = MagicMock()
    sys.modules["airflow.auth.managers.models.resource_details"] = MagicMock()
    sys.modules["airflow.providers"] = MagicMock()
    sys.modules["airflow.providers.fab"] = MagicMock()
    sys.modules["airflow.providers.fab.auth_manager"] = MagicMock()
    sys.modules["airflow.providers.fab.auth_manager.models"] = MagicMock()
    sys.modules["airflow.www"] = MagicMock()
    sys.modules["airflow.www.extensions"] = MagicMock()
    sys.modules["airflow.www.extensions.init_appbuilder"] = MagicMock()

from airflow_file_auth_manager.password import hash_password
from airflow_file_auth_manager.user import FileUser
from airflow_file_auth_manager.user_store import UserStore

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_users_data() -> dict:
    """Sample users data for testing."""
    return {
        "version": "1.0",
        "users": [
            {
                "username": "admin",
                "password_hash": hash_password("admin123"),
                "role": "admin",
                "email": "admin@example.com",
                "active": True,
            },
            {
                "username": "editor",
                "password_hash": hash_password("editor123"),
                "role": "editor",
                "email": "editor@example.com",
                "active": True,
            },
            {
                "username": "viewer",
                "password_hash": hash_password("viewer123"),
                "role": "viewer",
                "email": "viewer@example.com",
                "active": True,
            },
            {
                "username": "inactive",
                "password_hash": hash_password("inactive123"),
                "role": "viewer",
                "email": "inactive@example.com",
                "active": False,
            },
        ],
    }


@pytest.fixture
def users_file(temp_dir: Path, sample_users_data: dict) -> Path:
    """Create a temporary users file."""
    file_path = temp_dir / "users.yaml"
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(sample_users_data, f)
    return file_path


@pytest.fixture
def user_store(users_file: Path) -> UserStore:
    """Create a UserStore with test data."""
    return UserStore(users_file)


@pytest.fixture
def admin_user() -> FileUser:
    """Create an admin user."""
    return FileUser(
        username="admin",
        password_hash=hash_password("admin123"),
        role="admin",
        email="admin@example.com",
    )


@pytest.fixture
def editor_user() -> FileUser:
    """Create an editor user."""
    return FileUser(
        username="editor",
        password_hash=hash_password("editor123"),
        role="editor",
        email="editor@example.com",
    )


@pytest.fixture
def viewer_user() -> FileUser:
    """Create a viewer user."""
    return FileUser(
        username="viewer",
        password_hash=hash_password("viewer123"),
        role="viewer",
        email="viewer@example.com",
    )
