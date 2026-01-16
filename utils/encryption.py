"""Token encryption utilities."""
from cryptography.fernet import Fernet
from config import settings
import base64
import hashlib


def get_encryption_key() -> bytes:
    """Get or derive encryption key from settings."""
    key_str = settings.token_encryption_key
    # Derive a 32-byte key using SHA256
    key_bytes = key_str.encode() if isinstance(key_str, str) else key_str
    key_bytes = hashlib.sha256(key_bytes).digest()
    # Convert to base64 for Fernet (Fernet requires 32-byte key, base64-encoded)
    return base64.urlsafe_b64encode(key_bytes)


# Initialize Fernet with the encryption key
try:
    _fernet = Fernet(get_encryption_key())
except Exception:
    # If key generation fails, generate a new one (for development)
    import os
    key = base64.urlsafe_b64encode(os.urandom(32))
    _fernet = Fernet(key)


def encrypt_token(token: str) -> str:
    """Encrypt a token for storage."""
    return _fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored token."""
    return _fernet.decrypt(encrypted_token.encode()).decode()
