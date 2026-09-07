"""
STABLE AUTHENTICATION MODULE - DO NOT MODIFY UNDER ANY CIRCUMSTANCES
===================================================================

This module contains the core authentication logic for the entire application.
It has been isolated and stabilized to prevent the authentication issues that
were previously occurring due to inconsistent implementations.

RULES:
1. NEVER modify any code in this directory once deployed
2. NEVER change token subjects (must remain user ID)
3. NEVER alter the get_current_user dependency signature
4. All authentication-related changes must go through proper RFC process

Any modification will break authentication system-wide and cause 401 errors.
"""

from .auth_dependencies import get_current_user
from .auth_utils import (
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
)

__all__ = [
    "get_current_user",
    "create_access_token",
    "create_refresh_token",
    "verify_access_token",
    "verify_refresh_token",
]
