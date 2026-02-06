"""File-based Auth Manager for Apache Airflow 3.x.

A lightweight YAML file-based authentication manager that supports:
- bcrypt password hashing
- Three-tier role system (admin, editor, viewer)
- JWT token-based session management
"""

from airflow_file_auth_manager.password import hash_password, verify_password
from airflow_file_auth_manager.policy import FileAuthPolicy, Role
from airflow_file_auth_manager.user import FileUser
from airflow_file_auth_manager.user_store import UserStore

__version__ = "0.1.0"

# FileAuthManager requires Airflow, so import lazily
try:
    from airflow_file_auth_manager.file_auth_manager import FileAuthManager
except ImportError:
    FileAuthManager = None  # type: ignore[misc, assignment]

__all__ = [
    "FileAuthManager",
    "FileAuthPolicy",
    "FileUser",
    "Role",
    "UserStore",
    "hash_password",
    "verify_password",
]
