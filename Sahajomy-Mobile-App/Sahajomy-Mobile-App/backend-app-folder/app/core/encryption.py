"""
Phone number encryption service
"""

import base64
import hashlib
import hmac
import logging

from app.core.config import settings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC  # Fixed import

logger = logging.getLogger(__name__)


class DataEncryption:
    """
    Handles sensitive data encryption with multiple layers
    Supports both phone numbers and email addresses
    Uses:
    1. SHA-256 hash for lookups (one-way, can't decrypt)
    2. AES-256 encryption for display (reversible with key)
    """

    def __init__(self):
        # Master encryption key from environment
        self.master_key = settings.PHONE_ENCRYPTION_KEY.encode()
        self.salt = settings.ENCRYPTION_SALT.encode()
        self.phone_pepper = settings.PHONE_HASH_PEPPER
        # Use same pepper for email for consistency, or could add separate EMAIL_HASH_PEPPER later

        # Derive Fernet key using PBKDF2HMAC (correct class name)
        kdf = PBKDF2HMAC(  # Changed from PBKDF2 to PBKDF2HMAC
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        self.cipher = Fernet(key)

    def hash_phone(self, phone: str) -> str:
        """
        One-way hash for phone lookups
        Even with the hash, you cannot recover the original number
        """
        if not phone:
            return None
        # Add pepper to prevent rainbow table attacks
        peppered = phone + self.phone_pepper
        return hashlib.sha256(peppered.encode()).hexdigest()

    def hash_email(self, email: str) -> str:
        """
        One-way hash for email lookups
        Even with the hash, you cannot recover the original email
        """
        if not email:
            return None
        # Add pepper to prevent rainbow table attacks
        peppered = email + self.phone_pepper  # Reusing phone pepper for now
        return hashlib.sha256(peppered.encode()).hexdigest()

    def hash_otp(self, phone: str, otp_code: str) -> str:
        """Create a keyed, non-reversible OTP verifier bound to its recipient."""
        payload = f"{phone}:{otp_code}".encode()
        return hmac.new(self.phone_pepper.encode(), payload, hashlib.sha256).hexdigest()

    def encrypt_phone(self, phone: str) -> bytes:
        """
        Encrypt phone number for storage
        Can be decrypted later with the key
        """
        if not phone:
            return None
        return self.cipher.encrypt(phone.encode())

    def encrypt_email(self, email: str) -> bytes:
        """
        Encrypt email address for storage
        Can be decrypted later with the key
        """
        if not email:
            return None
        return self.cipher.encrypt(email.encode())

    def decrypt_phone(self, encrypted_data: bytes) -> str:
        """
        Decrypt phone number for display
        Requires the master encryption key
        """
        if not encrypted_data:
            return None
        return self.cipher.decrypt(encrypted_data).decode()

    def decrypt_email(self, encrypted_data: bytes) -> str:
        """
        Decrypt email address for display
        Requires the master encryption key
        """
        if not encrypted_data:
            return None
        return self.cipher.decrypt(encrypted_data).decode()

    def encrypt_text(self, value: str) -> bytes:
        """Encrypt another short sensitive value with the platform data key."""
        if not value:
            return None
        return self.cipher.encrypt(value.encode())

    def decrypt_text(self, encrypted_data: bytes) -> str:
        if not encrypted_data:
            return None
        return self.cipher.decrypt(encrypted_data).decode()

    def mask_phone(self, phone: str) -> str:
        """
        Create a masked version for logs (e.g., +255******678)
        """
        if not phone:
            return "***NO_PHONE***"
        if len(phone) >= 8:
            return phone[:4] + "*" * (len(phone) - 7) + phone[-3:]
        return "***MASKED***"

    def mask_email(self, email: str) -> str:
        """
        Create a masked version for logs (e.g., us***@example.com)
        """
        if not email:
            return "***NO_EMAIL***"
        parts = email.split("@")
        if len(parts) == 2 and len(parts[0]) > 2:
            masked_local = parts[0][0] + "***" + parts[0][-1]
            return f"{masked_local}@{parts[1]}"
        return "***MASKED***"


# Create global instance
data_encryption = DataEncryption()

# Maintain backward compatibility aliases
phone_encryption = data_encryption
