"""Tests for password hashing utilities."""

from __future__ import annotations

import pytest

from airflow_file_auth_manager.password import hash_password, verify_password


class TestHashPassword:
    """Tests for hash_password function."""

    def test_hash_password_returns_bcrypt_hash(self) -> None:
        """Hash should start with bcrypt prefix."""
        hashed = hash_password("test_password")
        assert hashed.startswith("$2b$")

    def test_hash_password_different_for_same_input(self) -> None:
        """Same password should produce different hashes (due to salt)."""
        hash1 = hash_password("same_password")
        hash2 = hash_password("same_password")
        assert hash1 != hash2

    def test_hash_password_handles_unicode(self) -> None:
        """Should handle unicode passwords."""
        hashed = hash_password("пароль한글密码")
        assert hashed.startswith("$2b$")


class TestVerifyPassword:
    """Tests for verify_password function."""

    def test_verify_correct_password(self) -> None:
        """Correct password should verify."""
        password = "correct_password"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self) -> None:
        """Incorrect password should not verify."""
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_empty_password(self) -> None:
        """Empty password should be handled."""
        hashed = hash_password("some_password")
        assert verify_password("", hashed) is False

    def test_verify_invalid_hash(self) -> None:
        """Invalid hash should return False, not raise."""
        assert verify_password("password", "invalid_hash") is False

    def test_verify_empty_hash(self) -> None:
        """Empty hash should return False."""
        assert verify_password("password", "") is False

    def test_verify_handles_unicode(self) -> None:
        """Should handle unicode passwords."""
        password = "пароль한글密码"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
