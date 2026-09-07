"""
Utility functions for the application.
"""

import secrets
import string
from datetime import datetime


def generate_receipt_number():
    """Generate a unique receipt number in format RCT-YYYYMMDD-XXXX"""
    timestamp = datetime.now().strftime("%Y%m%d")
    random_suffix = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)
    )
    return f"RCT-{timestamp}-{random_suffix}"


def generate_invoice_number():
    """Generate a unique invoice number in format INV-YYYYMMDD-XXXX"""
    timestamp = datetime.now().strftime("%Y%m%d")
    random_suffix = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)
    )
    return f"INV-{timestamp}-{random_suffix}"
