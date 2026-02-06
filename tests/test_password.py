"""Tests for password hashing utilities."""

from __future__ import annotations

import pytest

from airflow_file_auth_manager.password import (
    PasswordPolicyError,
    hash_password,
    validate_password,
    verify_password,
)

# Test password that meets all policy requirements
VALID_PASSWORD = "Test@123"


class TestPasswordPolicy:
    """Tests for password policy validation."""

    def test_valid_password(self) -> None:
        """Valid password should pass."""
        validate_password(VALID_PASSWORD)  # Should not raise

    def test_password_too_short(self) -> None:
        """Password less than 8 characters should fail."""
        with pytest.raises(PasswordPolicyError, match="at least 8 characters"):
            validate_password("Ab1@xyz")

    def test_password_too_long(self) -> None:
        """Password more than 128 characters should fail."""
        with pytest.raises(PasswordPolicyError, match="at most 128 characters"):
            validate_password("A" * 100 + "a1@" + "x" * 30)

    def test_password_missing_uppercase(self) -> None:
        """Password without uppercase should fail."""
        with pytest.raises(PasswordPolicyError, match="uppercase letter"):
            validate_password("test@123")

    def test_password_missing_lowercase(self) -> None:
        """Password without lowercase should fail."""
        with pytest.raises(PasswordPolicyError, match="lowercase letter"):
            validate_password("TEST@123")

    def test_password_missing_digit(self) -> None:
        """Password without digit should fail."""
        with pytest.raises(PasswordPolicyError, match="digit"):
            validate_password("Test@abc")

    def test_password_missing_special(self) -> None:
        """Password without special character should fail."""
        with pytest.raises(PasswordPolicyError, match="special character"):
            validate_password("Test1234")

    def test_various_special_characters(self) -> None:
        """Various special characters should be accepted."""
        special_chars = ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "-", "_", "=", "+"]
        for char in special_chars:
            password = f"Test123{char}"
            validate_password(password)  # Should not raise


class TestHashPassword:
    """Tests for hash_password function."""

    def test_hash_password_returns_bcrypt_hash(self) -> None:
        """Hash should start with bcrypt prefix."""
        hashed = hash_password(VALID_PASSWORD)
        assert hashed.startswith("$2b$")

    def test_hash_password_different_for_same_input(self) -> None:
        """Same password should produce different hashes (due to salt)."""
        hash1 = hash_password(VALID_PASSWORD)
        hash2 = hash_password(VALID_PASSWORD)
        assert hash1 != hash2

    def test_hash_password_handles_unicode(self) -> None:
        """Should handle unicode passwords that meet policy."""
        # Unicode password meeting policy requirements (ASCII letters required)
        hashed = hash_password("Пароль@1Aa")
        assert hashed.startswith("$2b$")

    def test_hash_password_validates_by_default(self) -> None:
        """hash_password should validate by default."""
        with pytest.raises(PasswordPolicyError):
            hash_password("weak")

    def test_hash_password_skip_validation(self) -> None:
        """hash_password with validate=False should skip validation."""
        # This should not raise even though password is weak
        hashed = hash_password("weak", validate=False)
        assert hashed.startswith("$2b$")


class TestVerifyPassword:
    """Tests for verify_password function."""

    def test_verify_correct_password(self) -> None:
        """Correct password should verify."""
        hashed = hash_password(VALID_PASSWORD)
        assert verify_password(VALID_PASSWORD, hashed) is True

    def test_verify_incorrect_password(self) -> None:
        """Incorrect password should not verify."""
        hashed = hash_password(VALID_PASSWORD)
        assert verify_password("Wrong@123", hashed) is False

    def test_verify_empty_password(self) -> None:
        """Empty password should be handled."""
        hashed = hash_password(VALID_PASSWORD)
        assert verify_password("", hashed) is False

    def test_verify_invalid_hash(self) -> None:
        """Invalid hash should return False, not raise."""
        assert verify_password(VALID_PASSWORD, "invalid_hash") is False

    def test_verify_empty_hash(self) -> None:
        """Empty hash should return False."""
        assert verify_password(VALID_PASSWORD, "") is False

    def test_verify_handles_unicode(self) -> None:
        """Should handle unicode passwords."""
        password = "Пароль@1Aa"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
