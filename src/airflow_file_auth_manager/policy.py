"""Role-based access control policy for file auth manager."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airflow.api_fastapi.auth.managers.models.resource_details import (
        AccessView,
        AssetDetails,
        ConfigurationDetails,
        ConnectionDetails,
        DagAccessEntity,
        DagDetails,
        PoolDetails,
        VariableDetails,
    )


class Role(str, Enum):
    """User roles with hierarchical permissions."""

    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Permission types."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    MENU = "MENU"


# Role hierarchy: admin > editor > viewer
ROLE_HIERARCHY = {
    Role.ADMIN: 3,
    Role.EDITOR: 2,
    Role.VIEWER: 1,
}


class FileAuthPolicy:
    """Policy class for role-based authorization decisions."""

    # Resources that only admins can modify
    ADMIN_ONLY_RESOURCES = frozenset({
        "Connection",
        "Variable",
        "Configuration",
        "Pool",
    })

    # Resources that editors can modify
    EDITOR_RESOURCES = frozenset({
        "Dag",
        "DagRun",
        "Task",
        "TaskInstance",
        "XCom",
        "Dataset",
    })

    # Read-only resources for viewers
    READ_ONLY_METHODS = frozenset({Permission.GET, Permission.MENU})

    @classmethod
    def get_role_level(cls, role: str) -> int:
        """Get the hierarchy level for a role."""
        try:
            return ROLE_HIERARCHY[Role(role)]
        except (ValueError, KeyError):
            return 0

    @classmethod
    def has_minimum_role(cls, user_role: str, required_role: Role) -> bool:
        """Check if user has at least the required role level."""
        return cls.get_role_level(user_role) >= ROLE_HIERARCHY[required_role]

    @classmethod
    def is_authorized_configuration(
        cls,
        *,
        method: str,
        user_role: str,
        details: ConfigurationDetails | None = None,
    ) -> bool:
        """Check if user can access configuration."""
        if method in cls.READ_ONLY_METHODS:
            return cls.has_minimum_role(user_role, Role.VIEWER)
        return cls.has_minimum_role(user_role, Role.ADMIN)

    @classmethod
    def is_authorized_connection(
        cls,
        *,
        method: str,
        user_role: str,
        details: ConnectionDetails | None = None,
    ) -> bool:
        """Check if user can access connections."""
        if method in cls.READ_ONLY_METHODS:
            return cls.has_minimum_role(user_role, Role.VIEWER)
        return cls.has_minimum_role(user_role, Role.ADMIN)

    @classmethod
    def is_authorized_dag(
        cls,
        *,
        method: str,
        user_role: str,
        access_entity: DagAccessEntity | None = None,
        details: DagDetails | None = None,
    ) -> bool:
        """Check if user can access Dags."""
        if method in cls.READ_ONLY_METHODS:
            return cls.has_minimum_role(user_role, Role.VIEWER)
        return cls.has_minimum_role(user_role, Role.EDITOR)

    @classmethod
    def is_authorized_dataset(
        cls,
        *,
        method: str,
        user_role: str,
        details: AssetDetails | None = None,
    ) -> bool:
        """Check if user can access datasets."""
        if method in cls.READ_ONLY_METHODS:
            return cls.has_minimum_role(user_role, Role.VIEWER)
        return cls.has_minimum_role(user_role, Role.EDITOR)

    @classmethod
    def is_authorized_pool(
        cls,
        *,
        method: str,
        user_role: str,
        details: PoolDetails | None = None,
    ) -> bool:
        """Check if user can access pools."""
        if method in cls.READ_ONLY_METHODS:
            return cls.has_minimum_role(user_role, Role.VIEWER)
        return cls.has_minimum_role(user_role, Role.ADMIN)

    @classmethod
    def is_authorized_variable(
        cls,
        *,
        method: str,
        user_role: str,
        details: VariableDetails | None = None,
    ) -> bool:
        """Check if user can access variables."""
        if method in cls.READ_ONLY_METHODS:
            return cls.has_minimum_role(user_role, Role.VIEWER)
        return cls.has_minimum_role(user_role, Role.ADMIN)

    @classmethod
    def is_authorized_view(
        cls,
        *,
        user_role: str,
        access_view: AccessView,
    ) -> bool:
        """Check if user can access a specific view."""
        # All authenticated users can access basic views
        return cls.has_minimum_role(user_role, Role.VIEWER)

    @classmethod
    def is_authorized_custom_view(
        cls,
        *,
        method: str,
        user_role: str,
        resource_name: str,
    ) -> bool:
        """Check if user can access custom views/resources."""
        if method in cls.READ_ONLY_METHODS:
            return cls.has_minimum_role(user_role, Role.VIEWER)
        if resource_name in cls.ADMIN_ONLY_RESOURCES:
            return cls.has_minimum_role(user_role, Role.ADMIN)
        return cls.has_minimum_role(user_role, Role.EDITOR)
