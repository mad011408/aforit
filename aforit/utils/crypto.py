"""Cryptographic utilities - encryption, hashing, secure storage."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Any


class SecureVault:
    """Encrypted key-value storage for secrets."""

    def __init__(self, vault_path: Path, master_key: str | None = None):
        self.vault_path = vault_path
        self._master_key = master_key or os.getenv("AFORIT_VAULT_KEY", "")
        self._data: dict[str, str] = {}
        if vault_path.exists():
            self._load()

    def _derive_key(self) -> bytes:
        """Derive an encryption key from the master key."""
        return hashlib.pbkdf2_hmac(
            "sha256",
            self._master_key.encode(),
            b"aforit_vault_salt_v1",
            100000,
        )

    def _xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        """Simple XOR encryption (for demonstration; use Fernet in production)."""
        key_extended = key * (len(data) // len(key) + 1)
        return bytes(a ^ b for a, b in zip(data, key_extended))

    def store(self, key: str, value: str):
        """Store an encrypted value."""
        encryption_key = self._derive_key()
        encrypted = self._xor_encrypt(value.encode(), encryption_key)
        self._data[key] = base64.b64encode(encrypted).decode()
        self._save()

    def retrieve(self, key: str) -> str | None:
        """Retrieve and decrypt a value."""
        encoded = self._data.get(key)
        if not encoded:
            return None
        encryption_key = self._derive_key()
        encrypted = base64.b64decode(encoded)
        decrypted = self._xor_encrypt(encrypted, encryption_key)
        return decrypted.decode()

    def delete(self, key: str) -> bool:
        """Delete a stored value."""
        if key in self._data:
            del self._data[key]
            self._save()
            return True
        return False

    def list_keys(self) -> list[str]:
        """List all stored keys (not values)."""
        return list(self._data.keys())

    def _save(self):
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        self.vault_path.write_text(json.dumps(self._data))

    def _load(self):
        try:
            self._data = json.loads(self.vault_path.read_text())
        except (json.JSONDecodeError, IOError):
            self._data = {}


def generate_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def hash_text(text: str, algorithm: str = "sha256") -> str:
    """Hash text with the specified algorithm."""
    h = hashlib.new(algorithm)
    h.update(text.encode())
    return h.hexdigest()


def hmac_sign(message: str, key: str) -> str:
    """Create an HMAC signature."""
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()


def hmac_verify(message: str, key: str, signature: str) -> bool:
    """Verify an HMAC signature."""
    expected = hmac_sign(message, key)
    return hmac.compare_digest(expected, signature)


def secure_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())
