"""Booking notification orchestration.

Connects the three booking flows to the EXISTING notification and email
infrastructure (no duplication):

- Notification rows + realtime push: app.services.realtime_notifications.create_notification
- Email delivery: app.core.email_service.send_email (shared Brevo client)

Recipient scoping (security):
- Sea container booking  -> ONLY the owning container's admin (container.admin_id)
- Air cargo booking      -> ONLY the cargo admin assigned to that booking
- Urgent sourcing request-> ONLY the sourcing agent that owns the batch

Every helper is best-effort: a notification/email failure must never break
the underlying booking transaction.
"""

from __future__ import annotations

import html
import logging

from app.core.email_service import send_email
from app.services.realtime_notifications import create_notification

logger = logging.getLogger(__name__)

# Canonical notification types (also used by the frontend for routing/icons)
CONTAINER_BOOKING_CREATED = "CONTAINER_BOOKING_CREATED"
AIR_CARGO_BOOKING_CREATED = "AIR_CARGO_BOOKING_CREATED"
URGENT_SOURCE_REQUEST = "URGENT_SOURCE_REQUEST"


def _recipient_email(user) -> str | None:
    """Resolve a user's email, preferring the secure (encrypted) field."""
    try:
        secure = getattr(user, "secure_email", None)
        if secure:
            return secure
    except Exception:
        pass
    return user.email


def _send_booking_email(user, subject: str, headline: str, body_html: str) -> None:
    """Best-effort branded email to a recipient user."""
    try:
        email = _recipient_email(user)
        if not email:
            logger.warning(
                "Booking notification email skipped: user %s has no email", user.id
            )
            return
        name = user.name or "there"
        html = f"""
        <div style="font-family:Arial,Helvetica,sans-serif;background:#F7F8FA;padding:24px;">
          <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #E2E8F0;">
            <div style="background:#0F3D5E;padding:20px 28px;">
              <span style="color:#ffffff;font-size:18px;font-weight:bold;letter-spacing:1px;">SAHAJOMY</span>
            </div>
            <div style="padding:28px;">
              <p style="margin:0 0 6px;color:#5B6472;font-size:11px;text-transform:uppercase;letter-spacing:2px;">{headline}</p>
              <p style="margin:0 0 16px;color:#0F172A;font-size:16px;font-weight:bold;">Hello {name},</p>
              {body_html}
              <p style="margin:20px 0 0;color:#5B6472;font-size:13px;">
                Sign in to your Sahajomy dashboard for details.<br>
                <a href="https://sahajomy.co.tz" style="color:#FF6B4A;text-decoration:none;">sahajomy.co.tz</a>
              </p>
            </div>
          </div>
        </div>
        """
        send_email(email, name, subject, html)
    except Exception as exc:
        logger.error(f"Booking notification email failed: {exc}")


def send_guest_batch_order_email(agent, batch, order, guest, items_count: int) -> None:
    """Email the sourcing agent after a guest successfully orders from a share link.

    This is intentionally post-commit and best-effort: an email delivery failure
    must not undo a valid guest order.
    """
    if not agent:
        logger.warning(
            "Guest batch order email skipped: batch %s has no sourcing agent",
            getattr(batch, "id", "unknown"),
        )
        return

    batch_title = html.escape(batch.title or "your sourcing batch")
    guest_name = html.escape(guest.name or "Guest customer")
    guest_phone = html.escape(guest.phone_number or "Not provided")
    currency = html.escape(batch.currency or "TZS")
    total = f"{float(order.total_product_amount or 0):,.2f}"
    batch_url = f"https://sahajomy.co.tz/agent/batches/{batch.id}"

    _send_booking_email(
        agent,
        subject="New guest order from your shared batch — Sahajomy",
        headline="Guest order received",
        body_html=(
            "<p style='margin:0;color:#0F172A;font-size:14px;line-height:1.6;'>"
            f"<strong>{guest_name}</strong> placed an order from "
            f"<strong>{batch_title}</strong>.</p>"
            "<ul style='margin:12px 0;padding-left:20px;color:#0F172A;font-size:14px;line-height:1.7;'>"
            f"<li><strong>Phone:</strong> {guest_phone}</li>"
            f"<li><strong>Items:</strong> {items_count}</li>"
            f"<li><strong>Order total:</strong> {currency} {total}</li>"
            "</ul>"
            f"<p style='margin:12px 0 0;font-size:14px;'>"
            f"<a href='{batch_url}' style='color:#FF6B4A;text-decoration:none;'>"
            "Open the batch to review the order</a>.</p>"
        ),
    )


def _container_label(container) -> str:
    size = container.container_size or "Container"
    return f"{size} container #{str(container.id)[:8]}"


def notify_container_booking_created(db, container, sea_booking, actor) -> None:
    """Notify the container's admin that space was just booked on it.

    Recipient: container.admin_id ONLY. Skips self-notification (e.g. an
    admin booking space on their own container).
    """
    try:
        admin_id = getattr(container, "admin_id", None)
        if not admin_id or admin_id == getattr(actor, "id", None):
            return

        actor_name = (actor.name if actor else None) or "A customer"
        cbm = float(sea_booking.cbm_booked)
        label = _container_label(container)
        message = f"{actor_name} booked {cbm:.2f} CBM on your {label}."

        create_notification(
            db,
            user_id=admin_id,
            notification_type=CONTAINER_BOOKING_CREATED,
            message=message,
            priority="info",
            target_type="sea_booking",
            target_id=sea_booking.id,
        )

        from app.models.user import User

        admin = db.query(User).filter(User.id == admin_id).first()
        if admin:
            _send_booking_email(
                admin,
                subject="New container booking — Sahajomy",
                headline="Container booking received",
                body_html=(
                    f"<p style='margin:0;color:#0F172A;font-size:14px;line-height:1.6;'>"
                    f"<strong>{actor_name}</strong> booked "
                    f"<strong>{cbm:.2f} CBM</strong> on your {label}.</p>"
                    f"<p style='margin:12px 0 0;color:#0F172A;font-size:14px;'>"
                    f"Payment status: <strong>{sea_booking.payment_status}</strong>. "
                    f"Review the sea_booking in your cargo dashboard.</p>"
                ),
            )
    except Exception as exc:
        logger.error(f"notify_container_booking_created failed: {exc}")


def notify_air_cargo_booking_created(db, booking, actor) -> None:
    """Notify the cargo admin assigned to an express air cargo booking.

    Recipient: booking.cargo_admin_id ONLY (assigned at creation time).
    """
    try:
        admin_id = getattr(booking, "cargo_admin_id", None)
        if not admin_id or admin_id == getattr(actor, "id", None):
            return

        actor_name = (actor.name if actor else None) or "A customer"
        weight = float(booking.weight_kg)
        reference = booking.tracking_number or f"#{str(booking.id)[:8]}"
        message = (
            f"New express air cargo booking {reference}: {weight:.2f} KG "
            f"from {actor_name}."
        )

        create_notification(
            db,
            user_id=admin_id,
            notification_type=AIR_CARGO_BOOKING_CREATED,
            message=message,
            priority="info",
            target_type="booking",
            target_id=booking.id,
        )

        from app.models.user import User

        admin = db.query(User).filter(User.id == admin_id).first()
        if admin:
            _send_booking_email(
                admin,
                subject="New air cargo booking — Sahajomy",
                headline="Air cargo booking assigned to you",
                body_html=(
                    f"<p style='margin:0;color:#0F172A;font-size:14px;line-height:1.6;'>"
                    f"<strong>{actor_name}</strong> created an express air cargo booking "
                    f"(<strong>{reference}</strong>) for <strong>{weight:.2f} KG</strong>.</p>"
                    f"<p style='margin:12px 0 0;color:#0F172A;font-size:14px;'>"
                    f"This booking is assigned to you. Process it from your cargo dashboard.</p>"
                ),
            )
    except Exception as exc:
        logger.error(f"notify_air_cargo_booking_created failed: {exc}")


def notify_urgent_sourcing_request(db, batch, order, actor) -> None:
    """Notify the sourcing agent that owns a batch about an urgent order.

    Recipient: batch.agent_id ONLY.
    """
    try:
        agent_id = getattr(batch, "agent_id", None)
        if not agent_id or agent_id == getattr(actor, "id", None):
            return

        actor_name = (actor.name if actor else None) or "A customer"
        batch_title = (getattr(batch, "title", None) or "").strip() or str(batch.id)[:8]
        order_ref = f"#{str(order.id)[:8]}"
        message = (
            f"URGENT: {actor_name} placed an urgent sourcing request "
            f"({order_ref}) in batch “{batch_title}”."
        )

        create_notification(
            db,
            user_id=agent_id,
            notification_type=URGENT_SOURCE_REQUEST,
            message=message,
            priority="warning",
            target_type="order",
            target_id=order.id,
        )

        from app.models.user import User

        agent = db.query(User).filter(User.id == agent_id).first()
        if agent:
            _send_booking_email(
                agent,
                subject="Urgent sourcing request — Sahajomy",
                headline="Urgent sourcing request",
                body_html=(
                    f"<p style='margin:0;color:#0F172A;font-size:14px;line-height:1.6;'>"
                    f"<strong>{actor_name}</strong> marked sourcing request "
                    f"<strong>{order_ref}</strong> in batch “{batch_title}” as "
                    f"<span style='color:#E85A3A;font-weight:bold;'>URGENT</span>.</p>"
                    f"<p style='margin:12px 0 0;color:#0F172A;font-size:14px;'>"
                    f"Please prioritise this request in your agent dashboard.</p>"
                ),
            )
    except Exception as exc:
        logger.error(f"notify_urgent_sourcing_request failed: {exc}")
