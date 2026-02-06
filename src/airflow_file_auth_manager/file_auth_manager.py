"""File-based Auth Manager for Apache Airflow 3.x."""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING, Any, Sequence

from airflow.api_fastapi.auth.managers.base_auth_manager import BaseAuthManager, ResourceMethod, MenuItem
from airflow.configuration import conf

from airflow_file_auth_manager.policy import FileAuthPolicy, Role
from airflow_file_auth_manager.user import FileUser
from airflow_file_auth_manager.user_store import UserStore

if TYPE_CHECKING:
    from fastapi import FastAPI

    from airflow.api_fastapi.auth.managers.models.base_user import BaseUser
    from airflow.api_fastapi.auth.managers.models.resource_details import (
        AccessView,
        AssetAliasDetails,
        AssetDetails,
        BackfillDetails,
        ConfigurationDetails,
        ConnectionDetails,
        DagAccessEntity,
        DagDetails,
        PoolDetails,
        VariableDetails,
    )

logger = logging.getLogger(__name__)

# Configuration section name
CONFIG_SECTION = "file_auth_manager"


class FileAuthManager(BaseAuthManager[FileUser]):
    """YAML file-based authentication manager for Apache Airflow.

    This auth manager stores users in a YAML file and supports:
    - bcrypt password hashing
    - Three-tier role system (admin, editor, viewer)
    - JWT token-based session management
    """

    def __init__(self) -> None:
        """Initialize FileAuthManager."""
        super().__init__()
        self._user_store: UserStore | None = None

    @cached_property
    def user_store(self) -> UserStore:
        """Get the user store instance."""
        users_file = conf.get(CONFIG_SECTION, "users_file", fallback=None)
        return UserStore(users_file)

    def init(self) -> None:
        """Initialize the auth manager."""
        logger.info("Initializing FileAuthManager")
        # Pre-load users
        self.user_store.load()
        user_count = len(self.user_store.get_all_users())
        logger.info("FileAuthManager initialized with %d users", user_count)

    def is_logged_in(self) -> bool:
        """Check if user is logged in."""
        return self.get_user() is not None

    def get_user_display_name(self) -> str:
        """Get the display name of current user."""
        user = self.get_user()
        if user:
            return user.display_name
        return ""

    def get_user_id(self) -> str | None:
        """Get the ID of current user."""
        user = self.get_user()
        if user:
            return user.username
        return None

    # =========================================================================
    # URL Methods
    # =========================================================================

    def get_url_login(self, **kwargs) -> str:
        """Get the login page URL."""
        from urllib.parse import urlencode
        url = "/auth/login"
        next_url = kwargs.get("next_url")
        if next_url:
            url = f"{url}?{urlencode({'next': next_url})}"
        return url

    def get_url_logout(self) -> str:
        """Get the logout URL."""
        return "/auth/logout"

    # =========================================================================
    # Serialization Methods (for JWT)
    # =========================================================================

    def serialize_user(self, user: FileUser) -> dict[str, Any]:
        """Serialize user for JWT token payload."""
        return {
            "username": user.username,
            "role": user.role,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

    def deserialize_user(self, token: dict[str, Any]) -> FileUser | None:
        """Deserialize user from JWT token payload.

        Security: Always validates against current user store to prevent
        privilege escalation via token manipulation.

        Returns:
            FileUser if valid and active, None otherwise.
        """
        username = token.get("username")
        if not username:
            logger.warning("JWT token missing username claim")
            return None

        user = self.user_store.get_user(username)
        if not user:
            logger.warning("User from JWT not found in store: %s", username)
            return None

        if not user.is_active:
            logger.warning("User from JWT is inactive: %s", username)
            return None

        return user

    # =========================================================================
    # Authorization Methods
    # =========================================================================

    def _get_user_role(self, user: FileUser | None) -> str:
        """Get role for given user."""
        if user and isinstance(user, FileUser):
            return user.role
        return "viewer"  # Default to most restrictive

    def is_authorized_configuration(
        self,
        *,
        method: ResourceMethod,
        user: FileUser,
        details: ConfigurationDetails | None = None,
    ) -> bool:
        """Check if user is authorized to access configuration."""
        return FileAuthPolicy.is_authorized_configuration(
            method=method,
            user_role=self._get_user_role(user),
            details=details,
        )

    def is_authorized_connection(
        self,
        *,
        method: ResourceMethod,
        user: FileUser,
        details: ConnectionDetails | None = None,
    ) -> bool:
        """Check if user is authorized to access connections."""
        return FileAuthPolicy.is_authorized_connection(
            method=method,
            user_role=self._get_user_role(user),
            details=details,
        )

    def is_authorized_dag(
        self,
        *,
        method: ResourceMethod,
        user: FileUser,
        access_entity: DagAccessEntity | None = None,
        details: DagDetails | None = None,
    ) -> bool:
        """Check if user is authorized to access DAGs."""
        return FileAuthPolicy.is_authorized_dag(
            method=method,
            user_role=self._get_user_role(user),
            access_entity=access_entity,
            details=details,
        )

    def is_authorized_asset(
        self,
        *,
        method: ResourceMethod,
        user: FileUser,
        details: AssetDetails | None = None,
    ) -> bool:
        """Check if user is authorized to access assets (datasets)."""
        return FileAuthPolicy.is_authorized_dataset(
            method=method,
            user_role=self._get_user_role(user),
            details=details,
        )

    def is_authorized_asset_alias(
        self,
        *,
        method: ResourceMethod,
        user: FileUser,
        details: AssetAliasDetails | None = None,
    ) -> bool:
        """Check if user is authorized to access asset aliases."""
        return FileAuthPolicy.is_authorized_dataset(
            method=method,
            user_role=self._get_user_role(user),
            details=details,
        )

    def is_authorized_backfill(
        self,
        *,
        method: ResourceMethod,
        user: FileUser,
        details: BackfillDetails | None = None,
    ) -> bool:
        """Check if user is authorized to access backfills."""
        return FileAuthPolicy.is_authorized_dag(
            method=method,
            user_role=self._get_user_role(user),
            details=details,
        )

    def is_authorized_pool(
        self,
        *,
        method: ResourceMethod,
        user: FileUser,
        details: PoolDetails | None = None,
    ) -> bool:
        """Check if user is authorized to access pools."""
        return FileAuthPolicy.is_authorized_pool(
            method=method,
            user_role=self._get_user_role(user),
            details=details,
        )

    def is_authorized_variable(
        self,
        *,
        method: ResourceMethod,
        user: FileUser,
        details: VariableDetails | None = None,
    ) -> bool:
        """Check if user is authorized to access variables."""
        return FileAuthPolicy.is_authorized_variable(
            method=method,
            user_role=self._get_user_role(user),
            details=details,
        )

    def is_authorized_view(
        self,
        *,
        access_view: AccessView,
        user: FileUser,
    ) -> bool:
        """Check if user is authorized to access a specific view."""
        return FileAuthPolicy.is_authorized_view(
            user_role=self._get_user_role(user),
            access_view=access_view,
        )

    def is_authorized_custom_view(
        self,
        *,
        method: ResourceMethod | str,
        resource_name: str,
        user: FileUser,
    ) -> bool:
        """Check if user is authorized to access custom views."""
        return FileAuthPolicy.is_authorized_custom_view(
            method=str(method),
            user_role=self._get_user_role(user),
            resource_name=resource_name,
        )

    # =========================================================================
    # Batch Authorization Methods
    # =========================================================================

    def batch_is_authorized_connection(
        self,
        requests: Sequence[dict[str, Any]],
    ) -> bool:
        """Batch check connection authorization."""
        return all(
            self.is_authorized_connection(
                method=req["method"],
                user=req["user"],
                details=req.get("details"),
            )
            for req in requests
        )

    def batch_is_authorized_dag(
        self,
        requests: Sequence[dict[str, Any]],
    ) -> bool:
        """Batch check DAG authorization."""
        return all(
            self.is_authorized_dag(
                method=req["method"],
                user=req["user"],
                access_entity=req.get("access_entity"),
                details=req.get("details"),
            )
            for req in requests
        )

    def batch_is_authorized_pool(
        self,
        requests: Sequence[dict[str, Any]],
    ) -> bool:
        """Batch check pool authorization."""
        return all(
            self.is_authorized_pool(
                method=req["method"],
                user=req["user"],
                details=req.get("details"),
            )
            for req in requests
        )

    def batch_is_authorized_variable(
        self,
        requests: Sequence[dict[str, Any]],
    ) -> bool:
        """Batch check variable authorization."""
        return all(
            self.is_authorized_variable(
                method=req["method"],
                user=req["user"],
                details=req.get("details"),
            )
            for req in requests
        )

    # =========================================================================
    # Menu Filtering
    # =========================================================================

    def filter_authorized_menu_items(
        self,
        menu_items: list[MenuItem],
        *,
        user: FileUser,
    ) -> list[MenuItem]:
        """Filter menu items based on user authorization.

        Hides menu items that the user doesn't have permission to access,
        providing a cleaner UX.
        """
        user_role = self._get_user_role(user)

        # Menu items that require admin role (case-insensitive)
        admin_only_menus = frozenset({
            "connections",
            "variables",
            "pools",
            "config",
            "admin",
        })

        filtered = []
        for item in menu_items:
            # MenuItem is an enum, get its name
            item_name = item.name.lower() if hasattr(item, 'name') else str(item).lower()

            # Check admin-only menus
            if item_name in admin_only_menus:
                if FileAuthPolicy.has_minimum_role(user_role, Role.ADMIN):
                    filtered.append(item)
                continue

            # Default: allow all other menu items for all roles
            filtered.append(item)

        return filtered

    # =========================================================================
    # FastAPI Integration
    # =========================================================================

    def get_fastapi_app(self) -> FastAPI:
        """Get FastAPI app with authentication endpoints."""
        from airflow_file_auth_manager.endpoints import create_auth_app

        return create_auth_app(self)
