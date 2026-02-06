"""Tests for FileAuthManager."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

# Skip entire module if Airflow 3.x auth module is not available
pytest.importorskip("airflow.api_fastapi.auth.managers.base_auth_manager")

from airflow_file_auth_manager.file_auth_manager import FileAuthManager
from airflow_file_auth_manager.user import FileUser

if TYPE_CHECKING:
    pass


@pytest.fixture
def auth_manager(users_file: Path) -> FileAuthManager:
    """Create a FileAuthManager with test users."""
    with patch("airflow_file_auth_manager.file_auth_manager.conf") as mock_conf:
        mock_conf.get.return_value = str(users_file)
        manager = FileAuthManager()
        manager.init()
        return manager


class TestFileAuthManagerInit:
    """Tests for FileAuthManager initialization."""

    def test_init_loads_users(self, auth_manager: FileAuthManager) -> None:
        """Init should load users from file."""
        users = auth_manager.user_store.get_all_users()
        assert len(users) == 4


class TestFileAuthManagerUrls:
    """Tests for URL methods."""

    def test_get_url_login(self, auth_manager: FileAuthManager) -> None:
        """Should return login URL."""
        url = auth_manager.get_url_login()
        assert url == "/auth/login"

    def test_get_url_login_with_next(self, auth_manager: FileAuthManager) -> None:
        """Should include next parameter."""
        url = auth_manager.get_url_login(next_url="/dags")
        assert "/auth/login" in url
        assert "next=" in url
        assert "%2Fdags" in url or "/dags" in url

    def test_get_url_logout(self, auth_manager: FileAuthManager) -> None:
        """Should return logout URL."""
        url = auth_manager.get_url_logout()
        assert url == "/auth/logout"


class TestFileAuthManagerSerialization:
    """Tests for user serialization."""

    def test_serialize_user(self, auth_manager: FileAuthManager, admin_user: FileUser) -> None:
        """Should serialize user to dict."""
        data = auth_manager.serialize_user(admin_user)
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert "password_hash" not in data

    def test_deserialize_user_existing(self, auth_manager: FileAuthManager) -> None:
        """Should deserialize to existing user."""
        data = {"username": "admin", "role": "admin"}
        user = auth_manager.deserialize_user(data)
        assert user is not None
        assert user.username == "admin"
        assert user.email == "admin@example.com"

    def test_deserialize_user_not_found(self, auth_manager: FileAuthManager) -> None:
        """Should return None for unknown user (security fix)."""
        data = {"username": "unknown", "role": "viewer"}
        user = auth_manager.deserialize_user(data)
        assert user is None

    def test_deserialize_user_inactive(self, auth_manager: FileAuthManager) -> None:
        """Should return None for inactive user."""
        data = {"username": "inactive", "role": "viewer"}
        user = auth_manager.deserialize_user(data)
        assert user is None


class TestFileAuthManagerAuthorization:
    """Tests for authorization methods."""

    def test_is_authorized_configuration_admin(self, auth_manager: FileAuthManager, admin_user: FileUser) -> None:
        """Admin should be authorized for configuration."""
        assert auth_manager.is_authorized_configuration(method="PUT", user=admin_user)

    def test_is_authorized_configuration_viewer(self, auth_manager: FileAuthManager, viewer_user: FileUser) -> None:
        """Viewer should only read configuration."""
        assert auth_manager.is_authorized_configuration(method="GET", user=viewer_user)
        assert not auth_manager.is_authorized_configuration(method="PUT", user=viewer_user)

    def test_is_authorized_connection_admin(self, auth_manager: FileAuthManager, admin_user: FileUser) -> None:
        """Admin should be authorized for connections."""
        assert auth_manager.is_authorized_connection(method="POST", user=admin_user)

    def test_is_authorized_connection_editor(self, auth_manager: FileAuthManager, editor_user: FileUser) -> None:
        """Editor should only read connections."""
        assert auth_manager.is_authorized_connection(method="GET", user=editor_user)
        assert not auth_manager.is_authorized_connection(method="POST", user=editor_user)

    def test_is_authorized_dag_editor(self, auth_manager: FileAuthManager, editor_user: FileUser) -> None:
        """Editor should be authorized for DAGs."""
        assert auth_manager.is_authorized_dag(method="POST", user=editor_user)

    def test_is_authorized_dag_viewer(self, auth_manager: FileAuthManager, viewer_user: FileUser) -> None:
        """Viewer should only read DAGs."""
        assert auth_manager.is_authorized_dag(method="GET", user=viewer_user)
        assert not auth_manager.is_authorized_dag(method="POST", user=viewer_user)

    def test_is_authorized_variable_admin(self, auth_manager: FileAuthManager, admin_user: FileUser) -> None:
        """Admin should be authorized for variables."""
        assert auth_manager.is_authorized_variable(method="POST", user=admin_user)

    def test_is_authorized_pool_admin(self, auth_manager: FileAuthManager, admin_user: FileUser) -> None:
        """Admin should be authorized for pools."""
        assert auth_manager.is_authorized_pool(method="POST", user=admin_user)


class TestFileAuthManagerBatchAuthorization:
    """Tests for batch authorization methods."""

    def test_batch_is_authorized_dag(self, auth_manager: FileAuthManager, editor_user: FileUser) -> None:
        """Batch DAG authorization should work."""
        requests = [
            {"method": "GET", "user": editor_user},
            {"method": "POST", "user": editor_user},
        ]
        assert auth_manager.batch_is_authorized_dag(requests)

    def test_batch_is_authorized_dag_mixed(self, auth_manager: FileAuthManager, viewer_user: FileUser) -> None:
        """Batch should fail if any request fails."""
        requests = [
            {"method": "GET", "user": viewer_user},
            {"method": "POST", "user": viewer_user},  # Viewer can't POST
        ]
        assert not auth_manager.batch_is_authorized_dag(requests)


class TestFileAuthManagerMenuFiltering:
    """Tests for menu filtering."""

    def test_filter_menu_items_admin(self, auth_manager: FileAuthManager, admin_user: FileUser) -> None:
        """Admin should see all menu items."""
        # Create mock MenuItem objects with name attribute (simulating enum)
        class MockMenuItem:
            def __init__(self, name: str):
                self.name = name

        items = [MockMenuItem("DAGs"), MockMenuItem("Connections"), MockMenuItem("Variables")]
        filtered = auth_manager.filter_authorized_menu_items(items, user=admin_user)
        assert len(filtered) == 3

    def test_filter_menu_items_viewer(self, auth_manager: FileAuthManager, viewer_user: FileUser) -> None:
        """Viewer should not see admin-only menus."""
        class MockMenuItem:
            def __init__(self, name: str):
                self.name = name

        items = [MockMenuItem("DAGs"), MockMenuItem("Connections"), MockMenuItem("Variables")]
        filtered = auth_manager.filter_authorized_menu_items(items, user=viewer_user)
        # Viewer should only see DAGs (Connections and Variables are admin-only)
        assert len(filtered) == 1
        assert filtered[0].name == "DAGs"
