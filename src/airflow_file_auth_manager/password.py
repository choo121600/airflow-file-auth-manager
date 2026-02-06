"""Password hashing and validation utilities using bcrypt."""

from __future__ import annotations

import re

import bcrypt

# Password policy constants
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class PasswordPolicyError(ValueError):
    """Raised when password doesn't meet policy requirements."""

    pass


def validate_password(password: str) -> None:
    """Validate password against security policy.

    Policy requirements:
    - Minimum 8 characters
    - Maximum 128 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: Plain text password to validate.

    Raises:
        PasswordPolicyError: If password doesn't meet requirements.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
        )

    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters long"
        )

    if not re.search(r"[A-Z]", password):
        raise PasswordPolicyError("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        raise PasswordPolicyError("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        raise PasswordPolicyError("Password must contain at least one digit")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/`~]", password):
        raise PasswordPolicyError("Password must contain at least one special character")


def hash_password(password: str, validate: bool = True) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password to hash.
        validate: Whether to validate password against policy (default: True).

    Returns:
        Bcrypt hash string.

    Raises:
        PasswordPolicyError: If validate=True and password doesn't meet policy.
    """
    if validate:
        validate_password(password)

    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash.

    Args:
        password: Plain text password to verify.
        password_hash: Bcrypt hash to check against.

    Returns:
        True if password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False
