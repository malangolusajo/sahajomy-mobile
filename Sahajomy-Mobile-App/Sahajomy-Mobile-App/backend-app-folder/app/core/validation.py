import re

try:
    import phonenumbers
    from phonenumbers import NumberParseException

    PHONENUMBERS_AVAILABLE = True
except ImportError:
    PHONENUMBERS_AVAILABLE = False


# Common disposable email domains (this is a small subset - in production you might want a more comprehensive list)
DISPOSABLE_EMAIL_DOMAINS = {
    "10minutemail.com",
    "tempmail.org",
    "guerrillamail.com",
    "mailinator.com",
    "yopmail.com",
    "throwaway.email",
    "temp-mail.org",
    "dispostable.com",
    "maildrop.cc",
    "getnada.com",
    "trashmail.com",
    "sharklasers.com",
    "tempinbox.com",
    "emailondeck.com",
    "fakeinbox.com",
    "tempmail.net",
}


def validate_email(email: str) -> bool:
    """
    Validate email format using regex and check against disposable email domains

    Args:
        email: Email address to validate

    Returns:
        bool: True if email format is valid and not from a disposable domain, False otherwise
    """
    # Basic format validation
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, email) is None:
        return False

    # Check for disposable email domains
    try:
        domain = email.split("@")[1].lower()
        if domain in DISPOSABLE_EMAIL_DOMAINS:
            return False
    except (IndexError, AttributeError):
        return False

    return True


def validate_and_format_phone(
    phone: str, default_region: str = "TZ"
) -> tuple[bool, str]:
    """
    Validate and format phone number to E.164 format (+countrycode number)
    Uses phonenumbers library if available, falls back to basic validation if not.

    Args:
        phone: Phone number string (can include +, spaces, dashes, parentheses)
        default_region: Default country code to assume if phone number doesn't start with +

    Returns:
        tuple: (is_valid, formatted_phone) - formatted_phone is in E.164 format if valid
    """
    if not phone:
        return False, ""

    if PHONENUMBERS_AVAILABLE:
        try:
            # Parse phone number
            if phone.startswith("+"):
                parsed_number = phonenumbers.parse(phone, None)
            else:
                # Assume default region if no country code provided
                parsed_number = phonenumbers.parse(phone, default_region)

            # Validate the number
            if phonenumbers.is_valid_number(parsed_number):
                # Format to E.164
                formatted = phonenumbers.format_number(
                    parsed_number, phonenumbers.PhoneNumberFormat.E164
                )
                return True, formatted
            else:
                return False, ""
        except NumberParseException:
            return False, ""
    else:
        # Fallback to basic validation
        # Remove all non-digit characters except the leading +
        cleaned = re.sub(r"[^\d+]", "", phone)

        # Handle cases with leading +
        if cleaned.startswith("+"):
            # Keep the + and ensure it has enough digits (minimum 7 digits after country code)
            digits_only = cleaned[1:]
            if len(digits_only) < 7 or len(digits_only) > 15:
                return False, ""
            return True, f"+{digits_only}"
        else:
            # No +, assume it's a local number - this is less reliable
            # For now, just ensure it has reasonable length
            if len(cleaned) < 7 or len(cleaned) > 15:
                return False, ""
            # Return as-is since we can't determine country code
            return True, cleaned
