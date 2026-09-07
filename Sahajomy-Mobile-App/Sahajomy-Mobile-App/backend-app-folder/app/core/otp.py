"""
OTP Generation Module for Sahajomy Platform
Handles generation of One-Time Passwords for authentication
"""

import secrets
import string


def generate_otp(length: int = 6) -> str:
    """
    Generate a numeric OTP of specified length

    Args:
        length: Length of the OTP (default 6)

    Returns:
        str: Generated OTP code
    """
    otp = "".join(secrets.choice(string.digits) for _ in range(length))
    return otp
