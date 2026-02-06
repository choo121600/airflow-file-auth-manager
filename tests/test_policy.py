"""Tests for FileAuthPolicy."""

from __future__ import annotations

import pytest

from airflow_file_auth_manager.policy import FileAuthPolicy, Role


class TestRoleHierarchy:
    """Tests for role hierarchy."""

    def test_admin_level(self) -> None:
        """Admin should have highest level."""
        assert FileAuthPolicy.get_role_level("admin") == 3

    def test_editor_level(self) -> None:
        """Editor should have middle level."""
        assert FileAuthPolicy.get_role_level("editor") == 2

    def test_viewer_level(self) -> None:
        """Viewer should have lowest level."""
        assert FileAuthPolicy.get_role_level("viewer") == 1

    def test_unknown_role_level(self) -> None:
        """Unknown role should have zero level."""
        assert FileAuthPolicy.get_role_level("unknown") == 0

    def test_has_minimum_role_admin(self) -> None:
        """Admin should have all roles."""
        assert FileAuthPolicy.has_minimum_role("admin", Role.ADMIN)
        assert FileAuthPolicy.has_minimum_role("admin", Role.EDITOR)
        assert FileAuthPolicy.has_minimum_role("admin", Role.VIEWER)

    def test_has_minimum_role_editor(self) -> None:
        """Editor should have editor and viewer roles."""
        assert not FileAuthPolicy.has_minimum_role("editor", Role.ADMIN)
        assert FileAuthPolicy.has_minimum_role("editor", Role.EDITOR)
        assert FileAuthPolicy.has_minimum_role("editor", Role.VIEWER)

    def test_has_minimum_role_viewer(self) -> None:
        """Viewer should only have viewer role."""
        assert not FileAuthPolicy.has_minimum_role("viewer", Role.ADMIN)
        assert not FileAuthPolicy.has_minimum_role("viewer", Role.EDITOR)
        assert FileAuthPolicy.has_minimum_role("viewer", Role.VIEWER)


class TestConfigurationAuthorization:
    """Tests for configuration authorization."""

    def test_admin_can_read_config(self) -> None:
        """Admin can read configuration."""
        assert FileAuthPolicy.is_authorized_configuration(method="GET", user_role="admin")

    def test_admin_can_modify_config(self) -> None:
        """Admin can modify configuration."""
        assert FileAuthPolicy.is_authorized_configuration(method="PUT", user_role="admin")

    def test_viewer_can_read_config(self) -> None:
        """Viewer can read configuration."""
        assert FileAuthPolicy.is_authorized_configuration(method="GET", user_role="viewer")

    def test_viewer_cannot_modify_config(self) -> None:
        """Viewer cannot modify configuration."""
        assert not FileAuthPolicy.is_authorized_configuration(method="PUT", user_role="viewer")

    def test_editor_cannot_modify_config(self) -> None:
        """Editor cannot modify configuration."""
        assert not FileAuthPolicy.is_authorized_configuration(method="PUT", user_role="editor")


class TestConnectionAuthorization:
    """Tests for connection authorization."""

    def test_admin_can_modify_connections(self) -> None:
        """Admin can modify connections."""
        assert FileAuthPolicy.is_authorized_connection(method="POST", user_role="admin")
        assert FileAuthPolicy.is_authorized_connection(method="PUT", user_role="admin")
        assert FileAuthPolicy.is_authorized_connection(method="DELETE", user_role="admin")

    def test_editor_can_read_connections(self) -> None:
        """Editor can read connections."""
        assert FileAuthPolicy.is_authorized_connection(method="GET", user_role="editor")

    def test_editor_cannot_modify_connections(self) -> None:
        """Editor cannot modify connections."""
        assert not FileAuthPolicy.is_authorized_connection(method="POST", user_role="editor")


class TestDagAuthorization:
    """Tests for DAG authorization."""

    def test_admin_can_manage_dags(self) -> None:
        """Admin can fully manage DAGs."""
        assert FileAuthPolicy.is_authorized_dag(method="GET", user_role="admin")
        assert FileAuthPolicy.is_authorized_dag(method="POST", user_role="admin")
        assert FileAuthPolicy.is_authorized_dag(method="DELETE", user_role="admin")

    def test_editor_can_manage_dags(self) -> None:
        """Editor can manage DAGs."""
        assert FileAuthPolicy.is_authorized_dag(method="GET", user_role="editor")
        assert FileAuthPolicy.is_authorized_dag(method="POST", user_role="editor")

    def test_viewer_can_only_read_dags(self) -> None:
        """Viewer can only read DAGs."""
        assert FileAuthPolicy.is_authorized_dag(method="GET", user_role="viewer")
        assert not FileAuthPolicy.is_authorized_dag(method="POST", user_role="viewer")


class TestVariableAuthorization:
    """Tests for variable authorization."""

    def test_admin_can_modify_variables(self) -> None:
        """Admin can modify variables."""
        assert FileAuthPolicy.is_authorized_variable(method="POST", user_role="admin")

    def test_editor_cannot_modify_variables(self) -> None:
        """Editor cannot modify variables."""
        assert not FileAuthPolicy.is_authorized_variable(method="POST", user_role="editor")

    def test_viewer_can_read_variables(self) -> None:
        """Viewer can read variables."""
        assert FileAuthPolicy.is_authorized_variable(method="GET", user_role="viewer")


class TestPoolAuthorization:
    """Tests for pool authorization."""

    def test_admin_can_modify_pools(self) -> None:
        """Admin can modify pools."""
        assert FileAuthPolicy.is_authorized_pool(method="POST", user_role="admin")

    def test_editor_cannot_modify_pools(self) -> None:
        """Editor cannot modify pools."""
        assert not FileAuthPolicy.is_authorized_pool(method="POST", user_role="editor")


class TestViewAuthorization:
    """Tests for view authorization."""

    def test_any_authenticated_user_can_access_views(self) -> None:
        """Any authenticated user can access views."""
        # Using a mock access_view since we don't have the actual enum
        assert FileAuthPolicy.is_authorized_view(user_role="viewer", access_view=None)  # type: ignore
        assert FileAuthPolicy.is_authorized_view(user_role="editor", access_view=None)  # type: ignore
        assert FileAuthPolicy.is_authorized_view(user_role="admin", access_view=None)  # type: ignore


class TestCustomViewAuthorization:
    """Tests for custom view authorization."""

    def test_admin_resource_requires_admin(self) -> None:
        """Admin-only resources require admin role."""
        assert FileAuthPolicy.is_authorized_custom_view(
            method="POST",
            user_role="admin",
            resource_name="Connection",
        )
        assert not FileAuthPolicy.is_authorized_custom_view(
            method="POST",
            user_role="editor",
            resource_name="Connection",
        )

    def test_editor_can_modify_other_resources(self) -> None:
        """Editor can modify non-admin resources."""
        assert FileAuthPolicy.is_authorized_custom_view(
            method="POST",
            user_role="editor",
            resource_name="Dag",
        )
