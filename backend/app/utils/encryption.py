"""Encryption utilities for sensitive data storage."""

import base64
import hashlib

from cryptography.fernet import Fernet


def _get_key(settings=None) -> bytes:
    """Get or generate encryption key from settings."""
    if settings is None:
        from app.config import get_settings
        settings = get_settings()

    secret = getattr(settings, 'ENCRYPTION_KEY', None)
    if not secret:
        secret = getattr(settings, 'SECRET_KEY', 'default-secret-key-change-in-production')

    # Derive a 32-byte key from the secret
    key = base64.urlsafe_b64encode(
        hashlib.sha256(secret.encode()).digest()
    )
    return key


def encrypt_value(plaintext: str, settings=None) -> str:
    """Encrypt a string value and return base64-encoded ciphertext."""
    key = _get_key(settings)
    f = Fernet(key)
    encrypted = f.encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_value(ciphertext: str, settings=None) -> str:
    """Decrypt a base64-encoded ciphertext string."""
    key = _get_key(settings)
    f = Fernet(key)
    encrypted = base64.urlsafe_b64decode(ciphertext.encode())
    return f.decrypt(encrypted).decode()


def mask_key(key: str, visible_chars: int = 4) -> str:
    """Mask an API key showing only the last N characters."""
    if len(key) <= visible_chars:
        return key
    return "*" * (len(key) - visible_chars) + key[-visible_chars:]
