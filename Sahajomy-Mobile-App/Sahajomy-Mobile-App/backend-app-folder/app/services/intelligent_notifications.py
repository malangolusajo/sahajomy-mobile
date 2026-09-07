"""
Intelligent Notification Service for Logistics Intelligence Platform
Handles smart notifications for delays, early arrivals, payment risks, etc.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.database import get_db
from app.models.air_cargo import ExpressAirCargoBooking
from app.models.container import Container, SeaBooking
from app.models.finance import Notification, Payment
from app.models.tracking import TrackingEvent
from app.models.user import User
from sqlalchemy.orm import Session


class IntelligentNotificationService:
    def __init__(self, db: Session):
        self.db = db

    def check_for_delay_notifications(self):
        """
        Check for containers that are delayed and send notifications
        """
        # Find containers that are in transit or expected to arrive but haven't
        delayed_containers = (
            self.db.query(Container)
            .filter(
                Container.status.in_(["in_transit", "arrived"]),
                Container.estimated_arrival_date < datetime.utcnow(),
                Container.arrival_date.is_(None),  # Not yet marked as arrived
            )
            .all()
        )

        notifications_sent = 0
        for container in delayed_containers:
            # Get all users with sea_bookings in this container
            sea_bookings = (
                self.db.query(SeaBooking)
                .filter(SeaBooking.container_id == container.id)
                .all()
            )

            for sea_booking in sea_bookings:
                if sea_booking.user_id:
                    user = (
                        self.db.query(User)
                        .filter(User.id == sea_booking.user_id)
                        .first()
                    )
                    if user:
                        # Check if we've already sent a delay notification for this container today
                        existing_notification = (
                            self.db.query(Notification)
                            .filter(
                                Notification.user_id == user.id,
                                Notification.entity_id == str(container.id),
                                Notification.type == "delay_alert",
                                Notification.created_at >= datetime.utcnow().date(),
                            )
                            .first()
                        )

                        if not existing_notification:
                            message = f"Your container '{container.id}' is delayed by {(datetime.utcnow() - container.estimated_arrival_date).days} days. Expected on {container.estimated_arrival_date.strftime('%Y-%m-%d')}, currently in transit."

                            notification = Notification(
                                user_id=user.id,
                                type="delay_alert",
                                message=message,
                                is_read=False,
                                entity_id=str(container.id),
                            )
                            self.db.add(notification)
                            notifications_sent += 1

        self.db.commit()
        return notifications_sent

    def check_for_early_arrival_notifications(self):
        """
        Check for containers arriving earlier than expected
        """
        # Find containers that arrived earlier than estimated
        early_arrivals = (
            self.db.query(Container)
            .filter(
                Container.arrival_date.isnot(None),
                Container.estimated_arrival_date.isnot(None),
                Container.arrival_date < Container.estimated_arrival_date,
            )
            .all()
        )

        notifications_sent = 0
        for container in early_arrivals:
            # Get all users with sea_bookings in this container
            sea_bookings = (
                self.db.query(SeaBooking)
                .filter(SeaBooking.container_id == container.id)
                .all()
            )

            for sea_booking in sea_bookings:
                if sea_booking.user_id:
                    user = (
                        self.db.query(User)
                        .filter(User.id == sea_booking.user_id)
                        .first()
                    )
                    if user:
                        # Check if we've already sent an early arrival notification for this container
                        existing_notification = (
                            self.db.query(Notification)
                            .filter(
                                Notification.user_id == user.id,
                                Notification.entity_id == str(container.id),
                                Notification.type == "early_arrival",
                            )
                            .first()
                        )

                        if not existing_notification:
                            days_early = (
                                container.estimated_arrival_date
                                - container.arrival_date
                            ).days
                            message = f"Good news! Your container '{container.id}' arrived {days_early} days earlier than expected. Adjust your plans accordingly."

                            notification = Notification(
                                user_id=user.id,
                                type="early_arrival",
                                message=message,
                                is_read=False,
                                entity_id=str(container.id),
                            )
                            self.db.add(notification)
                            notifications_sent += 1

        self.db.commit()
        return notifications_sent

    def check_for_payment_risks(self):
        """
        Check for overdue payments and send notifications
        """
        # Find sea_bookings with overdue payments
        overdue_sea_bookings = (
            self.db.query(SeaBooking)
            .filter(
                SeaBooking.payment_status == "due",
                SeaBooking.payment_due_date < datetime.utcnow(),
            )
            .all()
        )

        notifications_sent = 0
        for sea_booking in overdue_sea_bookings:
            if sea_booking.user_id:
                user = (
                    self.db.query(User).filter(User.id == sea_booking.user_id).first()
                )
                if user:
                    # Check if we've already sent a payment reminder today
                    existing_notification = (
                        self.db.query(Notification)
                        .filter(
                            Notification.user_id == user.id,
                            Notification.entity_id == str(sea_booking.id),
                            Notification.type == "payment_reminder",
                            Notification.created_at >= datetime.utcnow().date(),
                        )
                        .first()
                    )

                    if not existing_notification:
                        days_overdue = (
                            datetime.utcnow() - sea_booking.payment_due_date
                        ).days
                        message_prefix = "Payment for your sea booking is "
                        message_suffix = " days overdue. Please settle the payment to avoid delays in goods collection."
                        message = f"{message_prefix}{days_overdue}{message_suffix}"

                        notification = Notification(
                            user_id=user.id,
                            type="payment_reminder",
                            message=message,
                            is_read=False,
                            entity_id=str(sea_booking.id),
                        )
                        self.db.add(notification)
                        notifications_sent += 1

        self.db.commit()
        return notifications_sent

    def check_for_stock_out_risks(self):
        """
        Check for potential stock-out situations based on arrival and sales patterns
        """
        # This would typically require more complex logic involving sales data
        # For now, we'll implement a basic version that alerts when containers
        # are taking longer than usual to arrive
        notifications_sent = 0

        # Get containers that have been in transit for more than 2 weeks beyond estimated arrival
        extended_transit = (
            self.db.query(Container)
            .filter(
                Container.status == "in_transit",
                Container.estimated_arrival_date
                < datetime.utcnow() - timedelta(days=14),
            )
            .all()
        )

        for container in extended_transit:
            sea_bookings = (
                self.db.query(SeaBooking)
                .filter(SeaBooking.container_id == container.id)
                .all()
            )

            for sea_booking in sea_bookings:
                if sea_booking.user_id:
                    user = (
                        self.db.query(User)
                        .filter(User.id == sea_booking.user_id)
                        .first()
                    )
                    if user:
                        # Check if we've already sent a stock-out risk notification
                        existing_notification = (
                            self.db.query(Notification)
                            .filter(
                                Notification.user_id == user.id,
                                Notification.entity_id == str(container.id),
                                Notification.type == "stock_out_risk",
                            )
                            .first()
                        )

                        if not existing_notification:
                            days_extended = (
                                datetime.utcnow() - container.estimated_arrival_date
                            ).days
                            prefix = "Your shipment is significantly delayed ("
                            suffix = " days past due). Consider ordering alternatives to prevent stock-outs."
                            message = f"{prefix}{days_extended}{suffix}"

                            notification = Notification(
                                user_id=user.id,
                                type="stock_out_risk",
                                message=message,
                                is_read=False,
                                entity_id=str(container.id),
                            )
                            self.db.add(notification)
                            notifications_sent += 1

        self.db.commit()
        return notifications_sent

    def check_for_high_demand_notifications(self):
        """
        Check for high-demand product notifications based on order patterns
        """
        # This would require analysis of order patterns and market demand
        # For now, we'll implement a simple version that alerts when
        # similar products are frequently ordered
        notifications_sent = 0

        # Example: notify if a user has ordered similar products multiple times
        # This would require more complex analysis in a real implementation
        return notifications_sent

    def generate_all_intelligent_notifications(self):
        """
        Generate all types of intelligent notifications
        """
        results = {
            "delay_notifications": self.check_for_delay_notifications(),
            "early_arrival_notifications": self.check_for_early_arrival_notifications(),
            "payment_risk_notifications": self.check_for_payment_risks(),
            "stock_out_notifications": self.check_for_stock_out_risks(),
            "high_demand_notifications": self.check_for_high_demand_notifications(),
        }

        total_notifications = sum(results.values())

        return {"total_notifications_sent": total_notifications, "breakdown": results}


# Helper function to run the intelligent notification service
def run_intelligent_notifications(db: Session):
    """
    Run the intelligent notification service to generate all notifications
    """
    service = IntelligentNotificationService(db)
    return service.generate_all_intelligent_notifications()
