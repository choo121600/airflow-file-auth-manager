"""FileUser dataclass for file-based authentication."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FileUser:
    """Represents a user stored in the YAML file."""

    username: str
    password_hash: str
    role: str
    email: str = ""
    active: bool = True
    first_name: str = ""
    last_name: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate user data after initialization."""
        if not self.username:
            raise ValueError("username is required")
        if not self.password_hash:
            raise ValueError("password_hash is required")
        if self.role not in ("admin", "editor", "viewer"):
            raise ValueError(f"Invalid role: {self.role}. Must be admin, editor, or viewer")

    @property
    def is_active(self) -> bool:
        """Return whether the user is active."""
        return self.active

    @property
    def display_name(self) -> str:
        """Return display name for the user."""
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username

    def to_dict(self) -> dict:
        """Convert user to dictionary for YAML serialization."""
        data = {
            "username": self.username,
            "password_hash": self.password_hash,
            "role": self.role,
            "active": self.active,
        }
        if self.email:
            data["email"] = self.email
        if self.first_name:
            data["first_name"] = self.first_name
        if self.last_name:
            data["last_name"] = self.last_name
        if self.metadata:
            data["metadata"] = self.metadata
        return data

    @classmethod
    def from_dict(cls, data: dict) -> FileUser:
        """Create a FileUser from a dictionary."""
        return cls(
            username=data["username"],
            password_hash=data["password_hash"],
            role=data["role"],
            email=data.get("email", ""),
            active=data.get("active", True),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            metadata=data.get("metadata", {}),
        )
