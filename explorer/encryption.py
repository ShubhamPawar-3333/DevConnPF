"""
Token encryption service using Fernet symmetric encryption.

Provides encrypt/decrypt operations for storing GitHub access tokens at rest.
"""

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class TokenEncryptionService:
    """Encrypts and decrypts tokens using Fernet symmetric encryption."""

    def __init__(self):
        key = settings.FERNET_KEY
        if not key:
            raise ValueError(
                "FERNET_KEY is not configured. Set the FERNET_KEY environment variable. "
                "Generate one with: from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
            )
        if isinstance(key, str):
            key = key.encode()
        self._fernet = Fernet(key)

    def encrypt(self, token: str) -> bytes:
        """Encrypt a plaintext token string.

        Args:
            token: The plaintext GitHub access token.

        Returns:
            The encrypted token as bytes.

        Raises:
            ValueError: If the token is empty or None.
        """
        if not token:
            raise ValueError("Token cannot be empty or None.")
        return self._fernet.encrypt(token.encode())

    def decrypt(self, encrypted: bytes) -> str:
        """Decrypt an encrypted token back to plaintext.

        Args:
            encrypted: The encrypted token bytes.

        Returns:
            The decrypted plaintext token string.

        Raises:
            ValueError: If the encrypted data is empty or None.
            cryptography.fernet.InvalidToken: If decryption fails (wrong key or corrupted data).
        """
        if not encrypted:
            raise ValueError("Encrypted data cannot be empty or None.")
        return self._fernet.decrypt(encrypted).decode()
