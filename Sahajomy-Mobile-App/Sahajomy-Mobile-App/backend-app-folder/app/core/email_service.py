import logging
import re
from html import escape

from app.core.config import settings
from brevo import Brevo
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)

logger = logging.getLogger(__name__)


def send_email(recipient_email, recipient_name, subject, html_content):
    """Send a generic transactional email via the shared Brevo client.

    Used by OTP delivery and booking/notification emails alike.
    Returns True on success, False on failure (never raises).
    """
    if (
        settings.ENVIRONMENT == "development"
        and settings.EMAIL_DELIVERY_MODE.lower() == "console"
    ):
        logger.warning(
            "Local email mode: email for %s (%s) — subject: '%s'",
            recipient_name,
            recipient_email,
            subject,
        )
        return True

    if not settings.BREVO_API_KEY:
        logger.error("No BREVO_API_KEY")
        return False
    try:
        client = Brevo(api_key=settings.BREVO_API_KEY)
        resp = client.transactional_emails.send_transac_email(
            sender=SendTransacEmailRequestSender(
                email=settings.EMAIL_FROM_ADDRESS,
                name="Sahajomy",
            ),
            to=[
                SendTransacEmailRequestToItem(
                    email=recipient_email,
                    name=recipient_name,
                )
            ],
            subject=subject,
            html_content=html_content,
        )
        logger.info(f"Email sent, ID: {resp.message_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send: {e}")
        return False


def send_verification_email(recipient_email, recipient_name, otp_code):
    subject = "Your Sahajomy OTP"
    html_content = f"""
    <p>Hello {recipient_name},</p>
    <p>Welcome to Sahajomy 👋</p>
    <p>Use the verification code below to continue:</p>
    <h2 style="letter-spacing:2px;">{otp_code}</h2>
    <p>This OTP is valid for {settings.OTP_EXPIRE_MINUTES} minutes.</p>
    <p>For your security:</p>
    <ul>
        <li>Do not share this code with anyone</li>
        <li>Sahajomy will never ask for your OTP</li>
    </ul>
    <p>If you did not request this code, you can safely ignore this email.</p>
    <p>Best regards,<br>The Sahajomy Team</p>
    <p><a href="https://sahajomy.co.tz">https://sahajomy.co.tz</a></p>
    """
    return send_email(recipient_email, recipient_name, subject, html_content)


def send_staff_invitation_email(recipient_email, company_name, invitation_url):
    """Send a cargo-company staff invitation to the required email address."""
    safe_company_name = escape(company_name or "your cargo company")
    safe_invitation_url = escape(invitation_url, quote=True)
    subject = f"You're invited to join {company_name or 'a cargo company'} on Sahajomy"
    html_content = f"""
    <p>Hello,</p>
    <p>You have been invited to join <strong>{safe_company_name}</strong> on Sahajomy.</p>
    <p>Use the private link below to accept the invitation:</p>
    <p><a href="{safe_invitation_url}">Accept staff invitation</a></p>
    <p>This invitation expires in 7 days. Do not share this link with anyone else.</p>
    <p>After accepting, you will use your phone number to sign in and receive OTP codes by email.</p>
    <p>If you were not expecting this invitation, you can safely ignore this email.</p>
    <p>Best regards,<br>The Sahajomy Team</p>
    """
    return send_email(recipient_email, "Staff member", subject, html_content)


def validate_email(email):
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))
