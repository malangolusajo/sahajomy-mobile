"""Tenant-scoped operational summary for the existing cargo dashboard."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from app.models.air_cargo import AirDepartureSchedule, ExpressAirCargoBooking
from app.models.cargo_customs import CargoCustomer, ManualCargoIntake
from app.models.cargo_workspace import CargoCompany
from app.models.container import Container, Route, SeaBooking
from app.models.finance import SeaBookingPackingList
from app.models.financial_analytics import FinancialReceivable, FinancialTransaction
from app.models.shipment_orders import ShipmentOrder, ShipmentOrderStatus
from app.models.tracking import TrackingEvent
from app.models.warehouse_automation import (
    CargoAdminFeatureEntitlement,
    WarehouseCollectionRequest,
)
from app.services.subscriptions import (
    entitlement_map,
    get_current_subscription,
    subscription_is_usable,
)
from sqlalchemy import and_, case, distinct, false, func, or_
from sqlalchemy.orm import Session

ACTIVE_CONTAINER_STATUSES = (
    "draft",
    "open",
    "nearly_full",
    "full",
    "in_transit",
    "arrived",
)
PRE_DEPARTURE_CONTAINER_STATUSES = ("draft", "open", "nearly_full", "full")
ACTIVE_AIR_STATUSES = ("pending", "confirmed", "label_created", "in_transit")
ACTIVE_MANUAL_STATUSES = ("draft", "received", "ready_for_packing_list")
DEFAULT_CARGO_DASHBOARD_PERMISSIONS = {
    "booking.view",
    "booking.manage",
    "shipment.view",
    "shipment.update",
    "parcel.view",
    "parcel.receive",
    "intake.view",
    "intake.manage",
    "warehouse.view",
    "warehouse.manage",
    "customs.view",
    "aircargo.view",
    "finance.dashboard.view",
    "finance.revenue.view",
    "finance.receivables.view",
    "cargo.release",
}


def _iso(value):
    return value.isoformat() if value else None


def _money(value) -> str:
    return str(Decimal(value or 0).quantize(Decimal("0.01")))


def _split_route(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    separator = "→" if "→" in value else "-" if "-" in value else None
    if not separator:
        return value.strip() or None, None
    parts = [part.strip() for part in value.split(separator, 1)]
    return parts[0] or None, parts[1] or None


def _count(query) -> int:
    return int(query.count())


def _scoped_queries(
    db: Session,
    owner_id: UUID,
    warehouse_id: UUID | None,
    *,
    deny_operational_scope: bool = False,
):
    containers = db.query(Container).filter(Container.admin_id == owner_id)
    air = db.query(ExpressAirCargoBooking).filter(
        ExpressAirCargoBooking.cargo_admin_id == owner_id
    )
    intakes = db.query(ManualCargoIntake).filter(
        ManualCargoIntake.cargo_admin_id == owner_id
    )
    if deny_operational_scope:
        containers = containers.filter(false())
        air = air.filter(false())
        intakes = intakes.filter(false())
    elif warehouse_id:
        containers = containers.filter(
            or_(
                Container.warehouse_origin_id == warehouse_id,
                Container.warehouse_destination_id == warehouse_id,
            )
        )
        air = air.filter(ExpressAirCargoBooking.warehouse_id == warehouse_id)
        intakes = intakes.filter(ManualCargoIntake.warehouse_id == warehouse_id)
    sea = db.query(SeaBooking).filter(
        SeaBooking.container_id.in_(containers.with_entities(Container.id))
    )
    orders = db.query(ShipmentOrder).filter(
        or_(
            ShipmentOrder.sea_booking_id.in_(sea.with_entities(SeaBooking.id)),
            ShipmentOrder.air_booking_id.in_(
                air.with_entities(ExpressAirCargoBooking.id)
            ),
        )
    )
    return containers, sea, air, intakes, orders


def _average_sea_transit_days(containers) -> float | None:
    rows = (
        containers.filter(
            Container.departure_date.is_not(None),
            Container.arrival_date.is_not(None),
            Container.arrival_date >= Container.departure_date,
        )
        .with_entities(Container.departure_date, Container.arrival_date)
        .all()
    )
    if not rows:
        return None
    return round(
        sum(
            (arrival - departure).total_seconds() / 86400 for departure, arrival in rows
        )
        / len(rows),
        1,
    )


def _average_air_transit_days(db: Session, air) -> float | None:
    booking_ids = [row[0] for row in air.with_entities(ExpressAirCargoBooking.id).all()]
    if not booking_ids:
        return None
    new_status = TrackingEvent.extra_data["new_status"].astext
    rows = (
        db.query(
            TrackingEvent.entity_id,
            func.min(case((new_status == "in_transit", TrackingEvent.timestamp))),
            func.min(case((new_status == "delivered", TrackingEvent.timestamp))),
        )
        .filter(
            TrackingEvent.entity_type == "booking",
            TrackingEvent.entity_id.in_(booking_ids),
            new_status.in_(("in_transit", "delivered")),
        )
        .group_by(TrackingEvent.entity_id)
        .all()
    )
    durations = [
        (delivered - departed).total_seconds() / 86400
        for _, departed, delivered in rows
        if departed and delivered and delivered >= departed
    ]
    return round(sum(durations) / len(durations), 1) if durations else None


def build_cargo_dashboard(
    db: Session,
    *,
    owner_id: UUID,
    permissions: set[str],
    role_name: str,
    role_scope: str,
    company_id: UUID | None = None,
    branch_id: UUID | None = None,
    warehouse_id: UUID | None = None,
) -> dict:
    """Build one compact summary without leaking data outside the active workspace."""
    now = datetime.utcnow()
    today_start = datetime.combine(now.date(), time.min)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    horizon = now + timedelta(days=14)

    can_bookings = "booking.view" in permissions
    can_air = "aircargo.view" in permissions
    can_shipments = "shipment.view" in permissions
    can_intakes = bool({"intake.view", "parcel.view"} & permissions)
    can_documents = bool({"customs.view", "intake.view"} & permissions)
    can_customers = (
        "customs.view" in permissions and role_scope == "company" and branch_id is None
    )
    can_finance_dashboard = (
        "finance.dashboard.view" in permissions and company_id is not None
    )
    can_revenue = "finance.revenue.view" in permissions and company_id is not None
    can_receivables = (
        "finance.receivables.view" in permissions and company_id is not None
    )
    can_finance = can_finance_dashboard and (can_revenue or can_receivables)
    can_automation = "parcel.view" in permissions
    can_operations = can_bookings or can_air or can_shipments or can_intakes
    deny_branch_data = (role_scope != "company" and branch_id is None) or (
        branch_id is not None and warehouse_id is None
    )

    base_containers, base_sea, base_air, base_intakes, base_orders = _scoped_queries(
        db,
        owner_id,
        warehouse_id,
        deny_operational_scope=deny_branch_data,
    )
    containers = base_containers if can_bookings else base_containers.filter(false())
    sea = base_sea if can_bookings else base_sea.filter(false())
    air = base_air if can_air else base_air.filter(false())
    intakes = base_intakes if can_intakes else base_intakes.filter(false())
    orders = base_orders if can_shipments else base_orders.filter(false())

    active_sea = sea.join(Container).filter(
        SeaBooking.goods_status != "collected",
        Container.status.in_(ACTIVE_CONTAINER_STATUSES),
    )
    active_air = air.filter(ExpressAirCargoBooking.status.in_(ACTIVE_AIR_STATUSES))
    standalone_intakes = intakes.filter(
        ManualCargoIntake.sea_booking_id.is_(None),
        ManualCargoIntake.air_booking_id.is_(None),
    )
    active_intakes = standalone_intakes.filter(
        ManualCargoIntake.status.in_(ACTIVE_MANUAL_STATUSES),
        ManualCargoIntake.collection_status != "collected",
    )
    sea_in_transit = active_sea.filter(Container.status == "in_transit")
    air_in_transit = active_air.filter(ExpressAirCargoBooking.status == "in_transit")
    active_orders = orders.filter(
        ShipmentOrder.status != ShipmentOrderStatus.received_at_warehouse
    )
    order_only_predicates = [
        and_(
            ShipmentOrder.sea_booking_id.is_(None),
            ShipmentOrder.air_booking_id.is_(None),
        )
    ]
    if not can_bookings:
        order_only_predicates.append(ShipmentOrder.sea_booking_id.is_not(None))
    if not can_air:
        order_only_predicates.append(ShipmentOrder.air_booking_id.is_not(None))
    standalone_orders = active_orders.filter(or_(*order_only_predicates))
    held = sea.filter(SeaBooking.goods_status == "held")
    delayed_arrivals = containers.filter(
        Container.estimated_arrival_date < now,
        Container.status.in_(("in_transit", "arrived")),
        Container.arrival_date.is_(None),
    )
    delayed_departures = containers.filter(
        Container.departure_date < now,
        Container.status.in_(PRE_DEPARTURE_CONTAINER_STATUSES),
    )
    pending_sea_count = _count(
        sea.join(Container).filter(
            SeaBooking.goods_status != "collected",
            Container.status.in_(PRE_DEPARTURE_CONTAINER_STATUSES),
        )
    )
    pending_air_count = _count(
        air.filter(ExpressAirCargoBooking.status.in_(("pending", "confirmed")))
    )
    pending_order_count = _count(
        standalone_orders.filter(ShipmentOrder.status == ShipmentOrderStatus.pending)
    )
    pending_bookings = pending_sea_count + pending_air_count + pending_order_count

    active_sea_count = _count(active_sea)
    active_air_count = _count(active_air)
    active_intake_count = _count(active_intakes)
    active_order_count = _count(standalone_orders)
    sea_in_transit_count = _count(sea_in_transit)
    air_in_transit_count = _count(air_in_transit)
    held_count = _count(held)
    delayed_arrival_count = _count(delayed_arrivals)
    delayed_departure_count = _count(delayed_departures)
    released_count = _count(sea.filter(SeaBooking.goods_status == "released"))
    air_delivered_count = _count(
        air.filter(ExpressAirCargoBooking.status == "delivered")
    )
    ready_for_collection_count = _count(
        intakes.filter(ManualCargoIntake.collection_status == "ready")
    )

    delivered_week = _count(sea.filter(SeaBooking.collected_at >= week_start)) + _count(
        standalone_intakes.filter(ManualCargoIntake.collected_at >= week_start)
    )
    delivered_month = _count(
        sea.filter(SeaBooking.collected_at >= month_start)
    ) + _count(standalone_intakes.filter(ManualCargoIntake.collected_at >= month_start))
    if can_air:
        air_ids = air.with_entities(ExpressAirCargoBooking.id)
        delivered_week += (
            db.query(func.count(distinct(TrackingEvent.entity_id)))
            .filter(
                TrackingEvent.entity_type == "booking",
                TrackingEvent.entity_id.in_(air_ids),
                TrackingEvent.timestamp >= week_start,
                TrackingEvent.extra_data["new_status"].astext == "delivered",
            )
            .scalar()
            or 0
        )
        delivered_month += (
            db.query(func.count(distinct(TrackingEvent.entity_id)))
            .filter(
                TrackingEvent.entity_type == "booking",
                TrackingEvent.entity_id.in_(air_ids),
                TrackingEvent.timestamp >= month_start,
                TrackingEvent.extra_data["new_status"].astext == "delivered",
            )
            .scalar()
            or 0
        )

    total_cbm = active_sea.with_entities(func.sum(SeaBooking.cbm_booked)).scalar() or 0
    total_kg = (
        active_air.with_entities(func.sum(ExpressAirCargoBooking.weight_kg)).scalar()
        or 0
    )
    exception_count = held_count + delayed_arrival_count + delayed_departure_count

    summary = {
        "total_active": active_sea_count
        + active_air_count
        + active_intake_count
        + active_order_count,
        "sea_in_transit": sea_in_transit_count,
        "air_in_transit": air_in_transit_count,
        "exceptions": exception_count,
        "pending_bookings": pending_bookings,
        "delivered_this_week": int(delivered_week),
        "delivered_this_month": int(delivered_month),
    }

    status_board = []
    if can_bookings:
        status_board.extend(
            [
                {
                    "key": "booked",
                    "label": "Booked",
                    "count": _count(
                        active_sea.filter(
                            Container.status.in_(PRE_DEPARTURE_CONTAINER_STATUSES)
                        )
                    ),
                },
                {
                    "key": "in_transit",
                    "label": "Sea In Transit",
                    "count": sea_in_transit_count,
                },
                {
                    "key": "arrived",
                    "label": "Sea Arrived",
                    "count": _count(active_sea.filter(Container.status == "arrived")),
                },
                {
                    "key": "ready",
                    "label": "Ready / Released",
                    "count": released_count,
                },
                {
                    "key": "exception",
                    "label": "Held / Delayed",
                    "count": exception_count,
                },
            ]
        )
    if can_air:
        status_board.extend(
            [
                {
                    "key": "air_pending",
                    "label": "Air Pending",
                    "count": _count(
                        air.filter(
                            ExpressAirCargoBooking.status.in_(
                                ("pending", "confirmed", "label_created")
                            )
                        )
                    ),
                },
                {
                    "key": "air_transit",
                    "label": "Air In Transit",
                    "count": air_in_transit_count,
                },
                {
                    "key": "air_delivered",
                    "label": "Air Delivered",
                    "count": air_delivered_count,
                },
            ]
        )
    if can_intakes:
        status_board.extend(
            [
                {
                    "key": "warehouse",
                    "label": "At Warehouse",
                    "count": active_intake_count,
                },
                {
                    "key": "pickup",
                    "label": "Ready for Collection",
                    "count": ready_for_collection_count,
                },
            ]
        )
    if can_shipments:
        status_board.append(
            {
                "key": "shipment_orders",
                "label": "Shipment Orders",
                "count": active_order_count,
            }
        )

    departures = []
    if can_bookings:
        for row in (
            containers.filter(
                Container.departure_date >= now,
                Container.departure_date <= horizon,
                Container.status.in_(PRE_DEPARTURE_CONTAINER_STATUSES),
            )
            .order_by(Container.departure_date)
            .limit(5)
            .all()
        ):
            origin = (
                row.route.origin
                if row.route
                else row.origin_warehouse.city if row.origin_warehouse else None
            )
            destination = (
                row.route.destination
                if row.route
                else (
                    row.destination_warehouse.city
                    if row.destination_warehouse
                    else None
                )
            )
            departures.append(
                {
                    "id": str(row.id),
                    "mode": "sea",
                    "reference": f"{row.container_size or 'Sea'} container",
                    "origin": origin,
                    "destination": destination,
                    "date": _iso(row.departure_date),
                    "capacity": round(
                        max(float(row.max_cbm or 0) - float(row.booked_cbm or 0), 0), 2
                    ),
                    "unit": "CBM available",
                    "route": f"/cargo/containers?focus={row.id}",
                }
            )
    if can_air:
        schedules = db.query(AirDepartureSchedule).filter(
            AirDepartureSchedule.cargo_admin_id == owner_id,
            AirDepartureSchedule.departure_at >= now,
            AirDepartureSchedule.departure_at <= horizon,
            AirDepartureSchedule.status.in_(("open", "filling_fast")),
        )
        if warehouse_id:
            # Schedules do not carry a branch/warehouse key; branch staff must not
            # receive company-wide schedules that cannot be scoped reliably.
            schedules = schedules.filter(false())
        for row in schedules.order_by(AirDepartureSchedule.departure_at).limit(5).all():
            origin, destination = _split_route(row.route_label)
            departures.append(
                {
                    "id": str(row.id),
                    "mode": "air",
                    "reference": row.service_label,
                    "origin": origin,
                    "destination": destination,
                    "date": _iso(row.departure_at),
                    "capacity": (
                        float(row.available_capacity_kg)
                        if row.available_capacity_kg is not None
                        else None
                    ),
                    "unit": "KG available",
                    "route": "/cargo/express-air-cargo",
                }
            )
    departures.sort(key=lambda item: item["date"] or "")
    departures = departures[:6]

    arrivals = []
    if can_bookings:
        for row in (
            containers.filter(
                Container.estimated_arrival_date >= now,
                Container.estimated_arrival_date <= horizon,
                Container.status.in_(("full", "in_transit", "arrived")),
            )
            .order_by(Container.estimated_arrival_date)
            .limit(6)
            .all()
        ):
            destination = (
                row.route.destination
                if row.route
                else (
                    row.destination_warehouse.city
                    if row.destination_warehouse
                    else None
                )
            )
            arrivals.append(
                {
                    "id": str(row.id),
                    "reference": f"{row.container_size or 'Sea'} container",
                    "destination": destination,
                    "date": _iso(row.estimated_arrival_date),
                    "status": row.status,
                    "route": f"/cargo/containers?focus={row.id}",
                }
            )

    documents = None
    missing_document_count = 0
    if can_documents:
        document_sea = base_sea.join(Container).filter(
            SeaBooking.goods_status != "collected",
            Container.status.in_(ACTIVE_CONTAINER_STATUSES),
        )
        sea_ids = document_sea.with_entities(SeaBooking.id)
        packing_missing = _count(
            document_sea.filter(
                ~SeaBooking.id.in_(
                    db.query(SeaBookingPackingList.sea_booking_id).filter(
                        SeaBookingPackingList.sea_booking_id.in_(sea_ids)
                    )
                )
            )
        )
        packing_pending = (
            db.query(SeaBookingPackingList)
            .filter(
                SeaBookingPackingList.sea_booking_id.in_(sea_ids),
                SeaBookingPackingList.status.in_(("draft", "in_progress")),
            )
            .count()
        )
        shipment_files = (
            _count(
                base_orders.filter(
                    ShipmentOrder.has_attachments.is_not(True),
                    ShipmentOrder.status != ShipmentOrderStatus.received_at_warehouse,
                )
            )
            if can_shipments
            else 0
        )
        missing_document_count = packing_missing + packing_pending + shipment_files
        documents = {
            "total_pending": missing_document_count,
            "items": [
                {"label": "Packing list not started", "count": packing_missing},
                {"label": "Packing list in progress", "count": packing_pending},
                {"label": "Shipment files missing", "count": shipment_files},
            ],
            "route": "/cargo/documentationworkspace",
        }

    finance = None
    overdue_receivables = 0
    if can_finance:
        selected_branch = branch_id if branch_id else None
        transaction_scope = db.query(FinancialTransaction).filter(
            FinancialTransaction.company_id == company_id,
            FinancialTransaction.status == "posted",
            FinancialTransaction.transaction_date >= month_start.date(),
        )
        receivable_scope = db.query(FinancialReceivable).filter(
            FinancialReceivable.company_id == company_id
        )
        if selected_branch:
            transaction_scope = transaction_scope.filter(
                FinancialTransaction.branch_id == selected_branch
            )
            receivable_scope = receivable_scope.filter(
                FinancialReceivable.branch_id == selected_branch
            )
        company = db.query(CargoCompany).filter(CargoCompany.id == company_id).one()
        finance = {
            "base_currency": company.base_currency,
            "revenue_this_month": None,
            "outstanding_receivables": None,
            "paid_invoices": None,
            "unpaid_invoices": None,
            "overdue_invoices": None,
            "route": "/cargo/finance",
        }
        if can_revenue:
            revenue = (
                transaction_scope.filter(
                    FinancialTransaction.transaction_type == "revenue"
                )
                .with_entities(func.sum(FinancialTransaction.base_amount))
                .scalar()
                or 0
            )
            finance["revenue_this_month"] = _money(revenue)
        if can_receivables:
            outstanding = (
                receivable_scope.filter(
                    FinancialReceivable.status.in_(("unpaid", "partial", "overdue"))
                )
                .with_entities(
                    func.sum(
                        FinancialReceivable.base_invoiced_amount
                        - FinancialReceivable.base_paid_amount
                    )
                )
                .scalar()
                or 0
            )
            overdue_receivables = _count(
                receivable_scope.filter(FinancialReceivable.status == "overdue")
            )
            finance.update(
                {
                    "outstanding_receivables": _money(outstanding),
                    "paid_invoices": _count(
                        receivable_scope.filter(FinancialReceivable.status == "paid")
                    ),
                    "unpaid_invoices": _count(
                        receivable_scope.filter(
                            FinancialReceivable.status.in_(
                                ("unpaid", "partial", "overdue")
                            )
                        )
                    ),
                    "overdue_invoices": overdue_receivables,
                }
            )

    customers = None
    if can_customers:
        customer_scope = db.query(CargoCustomer).filter(
            CargoCustomer.cargo_admin_id == owner_id
        )
        active_customer_ids = base_intakes.filter(
            ManualCargoIntake.status.in_(ACTIVE_MANUAL_STATUSES)
        ).with_entities(ManualCargoIntake.customer_id)
        customers = {
            "active": _count(customer_scope.filter(CargoCustomer.status == "active")),
            "new_this_month": _count(
                customer_scope.filter(CargoCustomer.created_at >= month_start)
            ),
            "with_active_cargo": int(
                customer_scope.filter(CargoCustomer.id.in_(active_customer_ids)).count()
            ),
            "with_overdue_balances": 0,
            "route": "/cargo/documentationworkspace/customers",
        }
        if can_receivables:
            overdue_customer_ids = db.query(FinancialReceivable.customer_id).filter(
                FinancialReceivable.company_id == company_id,
                FinancialReceivable.status == "overdue",
            )
            if branch_id:
                overdue_customer_ids = overdue_customer_ids.filter(
                    FinancialReceivable.branch_id == branch_id
                )
            customers["with_overdue_balances"] = int(
                customer_scope.filter(
                    CargoCustomer.id.in_(overdue_customer_ids)
                ).count()
            )

    automation = None
    automation_enabled = False
    if can_automation:
        if company_id:
            subscription = get_current_subscription(db, company_id)
            feature = entitlement_map(subscription).get("warehouse_automation")
            automation_enabled = bool(
                feature and feature.enabled and subscription_is_usable(subscription)
            )
        else:
            legacy_entitlement = (
                db.query(CargoAdminFeatureEntitlement)
                .filter(CargoAdminFeatureEntitlement.cargo_admin_id == owner_id)
                .first()
            )
            automation_enabled = bool(
                legacy_entitlement and legacy_entitlement.warehouse_automation_enabled
            )
        if automation_enabled:
            automated_today = intakes.filter(
                ManualCargoIntake.intake_method != "manual",
                ManualCargoIntake.received_at >= today_start,
            )
            auto_matched = automated_today.filter(
                or_(
                    ManualCargoIntake.external_tracking_number.is_not(None),
                    ManualCargoIntake.shipping_mark.is_not(None),
                )
            )
            needs_review = automated_today.filter(
                ManualCargoIntake.external_tracking_number.is_(None),
                ManualCargoIntake.shipping_mark.is_(None),
            )
            collections = db.query(WarehouseCollectionRequest).filter(
                WarehouseCollectionRequest.cargo_admin_id == owner_id,
                WarehouseCollectionRequest.created_at >= today_start,
            )
            if warehouse_id:
                collections = collections.filter(
                    WarehouseCollectionRequest.warehouse_id == warehouse_id
                )
            automation = {
                "enabled": True,
                "scanned_today": _count(automated_today),
                "auto_matched": _count(auto_matched),
                "needs_review": _count(needs_review),
                "ready_for_collection": _count(
                    intakes.filter(ManualCargoIntake.collection_status == "ready")
                ),
                "collection_requests": _count(collections),
                "collected_today": _count(
                    intakes.filter(ManualCargoIntake.collected_at >= today_start)
                ),
            }
        else:
            automation = {"enabled": False}

    alerts = []
    if can_bookings:
        for row in (
            delayed_arrivals.order_by(Container.estimated_arrival_date).limit(3).all()
        ):
            alerts.append(
                {
                    "key": f"arrival-{row.id}",
                    "severity": "critical",
                    "label": "ARRIVAL DELAYED",
                    "title": f"{row.container_size or 'Sea'} container",
                    "detail": f"ETA was {row.estimated_arrival_date:%d %b}",
                    "route": f"/cargo/containers?focus={row.id}",
                }
            )
        for row in delayed_departures.order_by(Container.departure_date).limit(3).all():
            alerts.append(
                {
                    "key": f"departure-{row.id}",
                    "severity": "critical",
                    "label": "DEPARTURE DELAYED",
                    "title": f"{row.container_size or 'Sea'} container",
                    "detail": f"Planned {row.departure_date:%d %b}",
                    "route": f"/cargo/containers?focus={row.id}",
                }
            )
        for row in held.order_by(SeaBooking.hold_marked_at.desc()).limit(3).all():
            alerts.append(
                {
                    "key": f"hold-{row.id}",
                    "severity": "critical",
                    "label": "GOODS ON HOLD",
                    "title": str(row.id)[:8].upper(),
                    "detail": row.hold_reason or "Review hold details",
                    "route": f"/cargo/sea-bookings?focus={row.id}",
                }
            )
        near_capacity = containers.filter(
            Container.max_cbm > 0,
            Container.booked_cbm >= Container.max_cbm * Decimal("0.85"),
            Container.status.in_(("open", "nearly_full")),
        ).count()
        if near_capacity:
            alerts.append(
                {
                    "key": "capacity",
                    "severity": "warning",
                    "label": "CAPACITY",
                    "title": f"{near_capacity} container(s) at 85%+",
                    "detail": "Review remaining space",
                    "route": "/cargo/containers",
                }
            )
    if documents and missing_document_count:
        alerts.append(
            {
                "key": "documents",
                "severity": "warning",
                "label": "MISSING DOCUMENTS",
                "title": f"{missing_document_count} documentation action(s)",
                "detail": "Open the documentation workspace",
                "route": documents["route"],
            }
        )
    if can_receivables and overdue_receivables:
        alerts.append(
            {
                "key": "receivables",
                "severity": "critical",
                "label": "PAYMENT OVERDUE",
                "title": f"{overdue_receivables} overdue invoice(s)",
                "detail": "Review receivables",
                "route": "/cargo/finance",
            }
        )
    if automation and automation.get("needs_review"):
        alerts.append(
            {
                "key": "unmatched",
                "severity": "warning",
                "label": "UNMATCHED INTAKE",
                "title": f"{automation['needs_review']} parcel(s) need review",
                "detail": "Resolve warehouse intake matches",
                "route": "/cargo/documentationworkspace/warehouse-automation",
            }
        )
    alerts = alerts[:8]

    route_summary = []
    if can_bookings:
        route_rows = (
            containers.join(Route, Container.route_id == Route.id)
            .filter(Container.status.in_(ACTIVE_CONTAINER_STATUSES))
            .with_entities(Route.origin, Route.destination, func.count(Container.id))
            .group_by(Route.origin, Route.destination)
            .order_by(func.count(Container.id).desc())
            .limit(5)
            .all()
        )
        route_summary = [
            {"origin": origin, "destination": destination, "count": int(count)}
            for origin, destination, count in route_rows
        ]

    quick_actions = []
    action_definitions = [
        ("booking.manage", "Create Container", "/cargo/containers/new"),
        (
            "intake.manage",
            "Register Cargo Intake",
            "/cargo/documentationworkspace/manual-cargo-intake",
        ),
        ("warehouse.manage", "Manage Warehouses", "/cargo/warehouses"),
        ("shipment.view", "View Shipment Orders", "/cargo/shipment-orders"),
        ("customs.view", "Documentation Workspace", "/cargo/documentationworkspace"),
        ("aircargo.view", "Manage Air Cargo", "/cargo/express-air-cargo"),
    ]
    if automation_enabled:
        action_definitions = [
            (
                "parcel.receive",
                "Scan Incoming Parcel",
                "/cargo/documentationworkspace/warehouse-automation",
            ),
            (
                "cargo.release",
                "Scan Collection Code",
                "/cargo/documentationworkspace/warehouse-automation",
            ),
            *action_definitions,
        ]
    for permission, label, route in action_definitions:
        if permission in permissions and len(quick_actions) < 6:
            quick_actions.append({"label": label, "route": route})

    return {
        "generated_at": _iso(now),
        "role_context": {
            "role": role_name,
            "scope": role_scope,
            "company_id": str(company_id) if company_id else None,
            "branch_id": str(branch_id) if branch_id else None,
            "permissions": sorted(permissions),
        },
        "visibility": {
            "operations": can_operations,
            "finance": can_finance,
            "documents": can_documents,
            "customers": can_customers,
            "automation": can_automation,
        },
        "summary": summary,
        "alerts": alerts,
        "status_board": status_board,
        "modes": {
            "sea": {
                "visible": can_bookings,
                "active": active_sea_count,
                "quantity": round(float(total_cbm), 2),
                "unit": "CBM",
                "average_transit_days": (
                    _average_sea_transit_days(containers) if can_bookings else None
                ),
                "upcoming_departures": sum(
                    1 for item in departures if item["mode"] == "sea"
                ),
            },
            "air": {
                "visible": can_air,
                "active": active_air_count,
                "quantity": round(float(total_kg), 2),
                "unit": "KG",
                "average_transit_days": (
                    _average_air_transit_days(db, air) if can_air else None
                ),
                "upcoming_departures": sum(
                    1 for item in departures if item["mode"] == "air"
                ),
            },
        },
        "departures": departures,
        "arrivals": arrivals,
        "documents": documents,
        "finance": finance,
        "customers": customers,
        "automation": automation,
        "routes": route_summary,
        "quick_actions": quick_actions,
    }
