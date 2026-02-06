"""File-based Auth Manager for Apache Airflow 3.x."""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING, Any, Sequence
from urllib.parse import urlencode

from airflow.auth.managers.base_auth_manager import BaseAuthManager, ResourceMethod
from airflow.configuration import conf

from airflow_file_auth_manager.policy import FileAuthPolicy, Role
from airflow_file_auth_manager.user import FileUser
from airflow_file_auth_manager.user_store import UserStore

if TYPE_CHECKING:
    from fastapi import FastAPI

    from airflow.auth.managers.models.base_user import BaseUser
    from airflow.auth.managers.models.resource_details import (
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

    def get_url_login(self, *, next_url: str | None = None) -> str:
        """Get the login page URL."""
        url = "/auth/file/login"
        if next_url:
            url = f"{url}?{urlencode({'next': next_url})}"
        return url

    def get_url_logout(self) -> str:
        """Get the logout URL."""
        return "/auth/file/logout"

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

    def deserialize_user(self, data: dict[str, Any]) -> FileUser | None:
        """Deserialize user from JWT token payload.

        Security: Always validates against current user store to prevent
        privilege escalation via token manipulation.

        Returns:
            FileUser if valid and active, None otherwise.
        """
        username = data.get("username")
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

    def _get_user_role(self, user: BaseUser | None = None) -> str:
        """Get role for given user or current user."""
        if user is None:
            user = self.get_user()
        if user and isinstance(user, FileUser):
            return user.role
        return "viewer"  # Default to most restrictive

    def is_authorized_configuration(
        self,
        *,
        method: ResourceMethod,
        details: ConfigurationDetails | None = None,
        user: BaseUser | None = None,
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
        details: ConnectionDetails | None = None,
        user: BaseUser | None = None,
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
        access_entity: DagAccessEntity | None = None,
        details: DagDetails | None = None,
        user: BaseUser | None = None,
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
        details: AssetDetails | None = None,
        user: BaseUser | None = None,
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
        details: AssetAliasDetails | None = None,
        user: BaseUser | None = None,
    ) -> bool:
        """Check if user is authorized to access asset aliases."""
        # Same policy as assets
        return FileAuthPolicy.is_authorized_dataset(
            method=method,
            user_role=self._get_user_role(user),
        )

    def is_authorized_backfill(
        self,
        *,
        method: ResourceMethod,
        details: BackfillDetails | None = None,
        user: BaseUser | None = None,
    ) -> bool:
        """Check if user is authorized to access backfills."""
        # Backfills are like DAG runs - editor level
        return FileAuthPolicy.is_authorized_dag(
            method=method,
            user_role=self._get_user_role(user),
        )

    def is_authorized_pool(
        self,
        *,
        method: ResourceMethod,
        details: PoolDetails | None = None,
        user: BaseUser | None = None,
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
        details: VariableDetails | None = None,
        user: BaseUser | None = None,
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
        user: BaseUser | None = None,
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
        user: BaseUser | None = None,
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
                details=req.get("details"),
                user=req.get("user"),
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
                access_entity=req.get("access_entity"),
                details=req.get("details"),
                user=req.get("user"),
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
                details=req.get("details"),
                user=req.get("user"),
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
                details=req.get("details"),
                user=req.get("user"),
            )
            for req in requests
        )

    # =========================================================================
    # Menu Filtering
    # =========================================================================

    def filter_authorized_menu_items(
        self,
        menu_items: list[dict[str, Any]],
        user: BaseUser | None = None,
    ) -> list[dict[str, Any]]:
        """Filter menu items based on user authorization.

        Hides menu items that the user doesn't have permission to access,
        providing a cleaner UX.
        """
        user_role = self._get_user_role(user)

        # Menu items that require admin role
        admin_only_menus = frozenset({
            "Connections",
            "Variables",
            "Pools",
            "Configuration",
            "Admin",
        })

        # Menu items that require editor role
        editor_menus = frozenset({
            "DAGs",
            "Datasets",
        })

        filtered = []
        for item in menu_items:
            item_name = item.get("name", "")

            # Check admin-only menus
            if item_name in admin_only_menus:
                if FileAuthPolicy.has_minimum_role(user_role, Role.ADMIN):
                    filtered.append(item)
                continue

            # Check editor menus (for write operations visibility)
            if item_name in editor_menus:
                # All roles can see DAGs/Datasets (read access)
                filtered.append(item)
                continue

            # Default: allow all other menu items
            filtered.append(item)

        return filtered

    # =========================================================================
    # FastAPI Integration
    # =========================================================================

    def get_fastapi_app(self) -> FastAPI:
        """Get FastAPI app with authentication endpoints."""
        from airflow_file_auth_manager.endpoints import create_auth_app

        return create_auth_app(self)
