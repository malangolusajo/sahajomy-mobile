"""
Customer Analytics API for Logistics Intelligence Platform
Provides business intelligence, performance metrics, and shipping recommendations
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from app.core.dependencies import get_customer
from app.database import get_db
from app.models.air_cargo import ExpressAirCargoBooking
from app.models.container import Container, SeaBooking
from app.models.finance import Payment
from app.models.sourcing import SourcingOrder, SourcingOrderItem, SourcingProduct
from app.models.tracking import TrackingEvent
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

router = APIRouter(prefix="/customer/analytics", tags=["Customer Analytics"])


# Response models
class OverviewStats(BaseModel):
    total_cbm_shipped: float
    total_air_shipments: int
    total_sales: float
    total_logistics_cost: float
    profit_estimate: float


class PerformanceMetric(BaseModel):
    avg_delay_per_operator: Dict[str, float]
    delay_frequency: Dict[str, int]
    operator_performance_score: Dict[str, float]


class DelayImpactData(BaseModel):
    sales_before_arrival: float
    sales_after_arrival: float
    stock_out_days: int
    estimated_lost_sales: float


class AirCargoAnalytics(BaseModel):
    total_air_cost: float
    total_air_revenue: float
    profit_from_air: float
    roi: float


class ShippingComparison(BaseModel):
    sea_cost: float
    air_cost: float
    sea_delivery_time: int  # in days
    air_delivery_time: int  # in days
    profit_comparison: Dict[str, float]
    recommendation: str


class SpeedToRevenue(BaseModel):
    days_from_shipment_to_first_sale: int
    air_vs_sea_comparison: Dict[str, int]


class InventorySummary(BaseModel):
    goods_in_transit: int
    goods_arrived: int
    goods_sold: int
    remaining_stock: int


class DemandInsight(BaseModel):
    fast_moving_products: List[Dict[str, str]]
    slow_moving_products: List[Dict[str, str]]
    goods_type_performance: List[Dict[str, str]]


class OperatorAnalytics(BaseModel):
    price_per_cbm: float
    avg_delivery_time: int  # in days
    delay_rate: float
    rating: float


class ProfitSimulatorInput(BaseModel):
    shipment_type: str  # SEA/AIR
    cbm_or_weight: float
    expected_sales: float


class ProfitSimulatorOutput(BaseModel):
    estimated_cost: float
    estimated_profit: float
    recommendation: str


class RiskAlert(BaseModel):
    alert_type: str
    description: str
    severity: str  # low, medium, high
    affected_entities: List[str]


class Recommendation(BaseModel):
    recommendation_type: str
    title: str
    description: str
    impact_score: int  # 1-10


# Analytics Endpoints


@router.get("/overview", response_model=OverviewStats)
def get_business_overview(
    current_user: User = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    GET /customer/dashboard/overview
    Metrics: total_cbm_shipped (sea cargo), total_air_shipments, total_sales (from sourcing_orders),
    total_logistics_cost (sea + air), profit_estimate = sales − logistics cost
    """

    def as_float(value) -> float:
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    # Calculate total CBM shipped (completed sea_bookings)
    total_cbm_shipped = as_float(
        db.query(func.sum(SeaBooking.cbm_booked))
        .join(Container, SeaBooking.container_id == Container.id)
        .filter(
            SeaBooking.user_id == current_user.id,
            Container.status == "completed",
        )
        .scalar()
    )

    # Total air shipments
    total_air_shipments = (
        db.query(ExpressAirCargoBooking)
        .filter(ExpressAirCargoBooking.customer_id == current_user.id)
        .count()
    )

    # Total sales from sourcing orders
    total_sales = as_float(
        db.query(func.sum(SourcingOrder.total_product_amount))
        .filter(SourcingOrder.customer_id == current_user.id)
        .scalar()
    )

    # Total logistics cost (from sea bookings and air cargo)
    total_logistics_cost = as_float(
        db.query(func.sum(SeaBooking.logistics_charge))
        .filter(SeaBooking.user_id == current_user.id)
        .scalar()
    )

    # Add air cargo costs (assuming weight * rate per kg)
    air_cargo_costs = as_float(
        db.query(func.sum(ExpressAirCargoBooking.weight_kg * 5.0))
        .filter(ExpressAirCargoBooking.customer_id == current_user.id)
        .scalar()
    )

    total_logistics_cost += air_cargo_costs

    # Profit estimate
    profit_estimate = total_sales - total_logistics_cost

    return OverviewStats(
        total_cbm_shipped=total_cbm_shipped,
        total_air_shipments=total_air_shipments,
        total_sales=total_sales,
        total_logistics_cost=total_logistics_cost,
        profit_estimate=profit_estimate,
    )


@router.get("/containers/performance", response_model=PerformanceMetric)
def get_container_performance(
    current_user: User = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    GET /containers/performance
    Metrics: avg_delay_per_operator, delay_frequency, operator performance score
    """
    # Get all completed containers for the user's sea_bookings
    sea_bookings_with_completed_containers = (
        db.query(SeaBooking)
        .join(Container)
        .filter(
            SeaBooking.user_id == current_user.id,
            Container.status == "completed",
            Container.arrival_date.isnot(None),
            Container.estimated_arrival_date.isnot(None),
        )
        .all()
    )

    # Calculate delay metrics
    operator_delays = {}
    delay_counts = {}

    for sea_booking in sea_bookings_with_completed_containers:
        container = sea_booking.container

        # Calculate delay in days
        actual_arrival = container.arrival_date
        estimated_arrival = container.estimated_arrival_date
        delay_days = (
            (actual_arrival - estimated_arrival).days
            if actual_arrival and estimated_arrival
            else 0
        )

        # Group by operator (admin who owns the container)
        operator_name = container.admin.name if container.admin else "Unknown"

        if operator_name not in operator_delays:
            operator_delays[operator_name] = []
            delay_counts[operator_name] = 0

        operator_delays[operator_name].append(delay_days)

        if delay_days > 0:
            delay_counts[operator_name] += 1

    # Calculate average delay per operator
    avg_delays = {}
    for op, delays in operator_delays.items():
        if delays:
            avg_delays[op] = sum(delays) / len(delays)
        else:
            avg_delays[op] = 0.0

    # Calculate operator performance score (lower delay = better score)
    performance_scores = {}
    for op in operator_delays.keys():
        avg_delay = avg_delays[op]
        # Score is based on inverse of delay, normalized to 0-10 scale
        score = max(0, 10 - avg_delay) if avg_delay < 10 else 0
        performance_scores[op] = min(10, score)

    return PerformanceMetric(
        avg_delay_per_operator=avg_delays,
        delay_frequency=delay_counts,
        operator_performance_score=performance_scores,
    )


@router.get("/delay-impact", response_model=DelayImpactData)
def get_delay_impact_analytics(
    current_user: User = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    GET /analytics/delay-impact
    Calculate: sales_before_arrival, sales_after_arrival, stock_out_days, estimated_lost_sales
    """
    # This is a simplified calculation - in a real system we'd need more complex logic
    # based on inventory levels, sales patterns, and actual arrival dates

    # For now, we'll return placeholder values based on the data we have
    sales_before_arrival = 0.0
    sales_after_arrival = 0.0
    stock_out_days = 0
    estimated_lost_sales = 0.0

    # More detailed implementation would require:
    # 1. Tracking when goods arrived vs when sales occurred
    # 2. Inventory management to know stock levels
    # 3. Historical sales patterns to estimate lost sales

    # For now, return zeros as placeholders
    return DelayImpactData(
        sales_before_arrival=sales_before_arrival,
        sales_after_arrival=sales_after_arrival,
        stock_out_days=stock_out_days,
        estimated_lost_sales=estimated_lost_sales,
    )


@router.get("/air/analytics", response_model=AirCargoAnalytics)
def get_air_cargo_analytics(
    current_user: User = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    GET /air/analytics
    Metrics: total_air_cost, total_air_revenue, profit_from_air, ROI
    """
    # Get all air cargo bookings for this customer
    air_bookings = (
        db.query(ExpressAirCargoBooking)
        .filter(ExpressAirCargoBooking.customer_id == current_user.id)
        .all()
    )

    # Simplified cost calculation (in a real system, this would come from actual pricing)
    total_air_cost = sum(
        float(booking.weight_kg or 0) * 5.0 for booking in air_bookings
    )  # $5 per kg

    # Revenue would come from associated sales orders
    # For now, we'll use a placeholder based on air cargo bookings
    total_air_revenue = 0.0

    # In a real system, revenue would be calculated from sales tied to air cargo
    # For now, we'll calculate based on sourcing orders that might be related to air cargo
    related_orders = (
        db.query(SourcingOrder)
        .filter(SourcingOrder.customer_id == current_user.id)
        .all()
    )

    for order in related_orders:
        if order.total_product_amount:
            total_air_revenue += float(order.total_product_amount)

    profit_from_air = total_air_revenue - total_air_cost
    roi = (profit_from_air / total_air_cost * 100) if total_air_cost > 0 else 0

    return AirCargoAnalytics(
        total_air_cost=total_air_cost,
        total_air_revenue=total_air_revenue,
        profit_from_air=profit_from_air,
        roi=roi,
    )


@router.get("/shipping-comparison", response_model=ShippingComparison)
def get_shipping_comparison(
    current_user: User = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    GET /analytics/shipping-comparison
    Output: sea_cost vs air_cost, sea_delivery_time vs air_delivery_time, profit comparison, recommendation
    """
    # Calculate sea shipping metrics
    sea_bookings = (
        db.query(SeaBooking)
        .filter(SeaBooking.user_id == current_user.id)
        .all()
    )

    sea_cost = sum(float(r.logistics_charge) for r in sea_bookings)

    # Simplified delivery time calculation (average of completed containers)
    completed_containers = (
        db.query(Container)
        .join(SeaBooking)
        .filter(
            SeaBooking.user_id == current_user.id,
            Container.status == "completed",
        )
        .all()
    )

    sea_delivery_times = []
    for container in completed_containers:
        if container.departure_date and container.arrival_date:
            duration = (container.arrival_date - container.departure_date).days
            sea_delivery_times.append(duration)

    avg_sea_delivery_time = (
        sum(sea_delivery_times) / len(sea_delivery_times) if sea_delivery_times else 30
    )  # 30 days default

    # Calculate air shipping metrics
    air_bookings = (
        db.query(ExpressAirCargoBooking)
        .filter(ExpressAirCargoBooking.customer_id == current_user.id)
        .all()
    )

    air_cost = sum(float(b.weight_kg or 0) * 5.0 for b in air_bookings)  # $5 per kg
    avg_air_delivery_time = 7  # 7 days default for air

    # Calculate profit comparison
    sea_profit = 0.0  # Placeholder - would need sales data
    air_profit = 0.0  # Placeholder - would need sales data

    # Simple recommendation based on cost and time
    if air_cost > sea_cost * 2 and avg_sea_delivery_time < 20:
        recommendation = "Sea shipping is more economical"
    elif avg_sea_delivery_time > 30 and air_cost < sea_cost * 3:
        recommendation = "Air shipping recommended for speed"
    else:
        recommendation = "Both options viable, consider other factors"

    return ShippingComparison(
        sea_cost=sea_cost,
        air_cost=air_cost,
        sea_delivery_time=avg_sea_delivery_time,
        air_delivery_time=avg_air_delivery_time,
        profit_comparison={"sea_profit": sea_profit, "air_profit": air_profit},
        recommendation=recommendation,
    )


@router.get("/speed-to-revenue", response_model=SpeedToRevenue)
def get_speed_to_revenue(
    current_user: User = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    GET /analytics/speed-to-revenue
    Calculate: days_from_shipment_to_first_sale, compare air vs sea
    """
    # This would require complex logic to match shipments with sales
    # For now, returning placeholder values

    # Simplified calculation based on container completion and order creation
    days_from_shipment_to_first_sale = 15  # Placeholder

    air_vs_sea_comparison = {
        "air_days": 10,  # Placeholder
        "sea_days": 25,  # Placeholder
    }

    return SpeedToRevenue(
        days_from_shipment_to_first_sale=days_from_shipment_to_first_sale,
        air_vs_sea_comparison=air_vs_sea_comparison,
    )


@router.get("/inventory/summary", response_model=InventorySummary)
def get_inventory_summary(
    current_user: User = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    GET /inventory/summary
    Output: goods_in_transit, goods_arrived, goods_sold, remaining_stock
    """
    # Count containers/sea-bookings in different states
    in_transit_count = (
        db.query(SeaBooking)
        .join(Container)
        .filter(
            SeaBooking.user_id == current_user.id,
            Container.status.in_(["in_transit", "nearly_full", "full"]),
        )
        .count()
    )

    arrived_count = (
        db.query(SeaBooking)
        .join(Container)
        .filter(
            SeaBooking.user_id == current_user.id,
            Container.status == "arrived",
        )
        .count()
    )

    # Sold goods would come from completed orders
    sold_count = (
        db.query(SourcingOrder)
        .filter(
            SourcingOrder.customer_id == current_user.id,
            SourcingOrder.delivery_status == "collected",
        )
        .count()
    )

    # Remaining stock would require more complex inventory tracking
    remaining_stock = 0  # Placeholder

    return InventorySummary(
        goods_in_transit=in_transit_count,
        goods_arrived=arrived_count,
        goods_sold=sold_count,
        remaining_stock=remaining_stock,
    )


@router.get("/demand-insights", response_model=DemandInsight)
def get_demand_insights(
    current_user: User = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    GET /analytics/demand-insights
    Output: fast moving products, slow moving products, goods type performance
    """
    # For this implementation, we'll analyze order patterns
    orders = (
        db.query(SourcingOrder)
        .filter(SourcingOrder.customer_id == current_user.id)
        .all()
    )

    # Extract products from orders to analyze performance
    product_quantities = {}
    for order in orders:
        for item in order.items:
            product_name = item.product.name if item.product else "Unknown Product"
            if product_name not in product_quantities:
                product_quantities[product_name] = 0
            product_quantities[product_name] += item.quantity

    # Sort products by quantity to identify fast/slow movers
    sorted_products = sorted(
        product_quantities.items(), key=lambda x: x[1], reverse=True
    )

    # Split into fast and slow movers (top 3 and bottom 3)
    fast_moving = [{"name": p[0], "quantity": str(p[1])} for p in sorted_products[:3]]
    slow_moving = [{"name": p[0], "quantity": str(p[1])} for p in sorted_products[-3:]]

    # Placeholder for goods type performance
    goods_type_performance = [
        {"type": "Electronics", "performance": "High"},
        {"type": "Clothing", "performance": "Medium"},
        {"type": "Food Items", "performance": "Low"},
    ]

    return DemandInsight(
        fast_moving_products=fast_moving,
        slow_moving_products=slow_moving,
        goods_type_performance=goods_type_performance,
    )


@router.get("/operators/analytics", response_model=OperatorAnalytics)
def get_operator_analytics(
    current_user: User = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    GET /operators/analytics
    Metrics: price_per_cbm, avg_delivery_time, delay_rate, rating
    """
    # Get containers handled by operators for this user
    containers = (
        db.query(Container)
        .join(SeaBooking)
        .filter(
            SeaBooking.user_id == current_user.id,
            Container.status == "completed",
        )
        .all()
    )

    if not containers:
        return OperatorAnalytics(
            price_per_cbm=0.0, avg_delivery_time=0, delay_rate=0.0, rating=0.0
        )

    # Calculate metrics
    total_price = sum(float(c.price_per_cbm) for c in containers)
    avg_price = total_price / len(containers) if containers else 0.0

    # Calculate delivery times
    delivery_times = []
    delays = 0

    for container in containers:
        if container.departure_date and container.arrival_date:
            time_taken = (container.arrival_date - container.departure_date).days
            delivery_times.append(time_taken)

            # Count delays (when actual arrival is after estimated)
            if container.estimated_arrival_date and container.arrival_date:
                if container.arrival_date > container.estimated_arrival_date:
                    delays += 1

    avg_delivery_time = (
        sum(delivery_times) / len(delivery_times) if delivery_times else 0
    )
    delay_rate = (delays / len(containers)) * 100 if containers else 0.0

    # Rating based on performance (inverse of delay rate, higher is better)
    rating = max(0, 10 - (delay_rate / 10))  # Scale 0-10

    return OperatorAnalytics(
        price_per_cbm=avg_price,
        avg_delivery_time=avg_delivery_time,
        delay_rate=delay_rate,
        rating=rating,
    )


@router.post("/profit-simulator", response_model=ProfitSimulatorOutput)
def get_profit_simulation(
    input_data: ProfitSimulatorInput,
    current_user: User = Depends(get_customer),
    db: Session = Depends(get_db),
):
    """
    POST /analytics/profit-simulator
    Input: shipment_type (SEA/AIR), cbm or weight, expected sales
    Output: estimated_cost, estimated_profit, recommendation
    """
    # Calculate cost based on shipment type
    if input_data.shipment_type.upper() == "SEA":
        # Sea shipping cost: price per CBM * volume
        estimated_cost = input_data.cbm_or_weight * 50  # $50 per CBM
    else:
        # Air shipping cost: weight * rate per kg
        estimated_cost = input_data.cbm_or_weight * 8  # $8 per kg

    # Estimated profit
    estimated_profit = input_data.expected_sales - estimated_cost

    # Recommendation based on profit margin
    profit_margin = (
        (estimated_profit / input_data.expected_sales) * 100
        if input_data.expected_sales > 0
        else 0
    )

    if profit_margin > 30:
        recommendation = "Recommended - High profit potential"
    elif profit_margin > 10:
        recommendation = "Consider - Moderate profit potential"
    else:
        recommendation = "Reconsider - Low profit potential"

    return ProfitSimulatorOutput(
        estimated_cost=estimated_cost,
        estimated_profit=estimated_profit,
        recommendation=recommendation,
    )


@router.get("/risk-alerts", response_model=List[RiskAlert])
def get_risk_alerts(
    current_user: User = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    GET /analytics/risk-alerts
    Detect: high delay operator, overpaying shipping cost, low demand product, risky goods type
    """
    alerts = []

    # Check for delayed containers
    delayed_containers = (
        db.query(Container)
        .join(SeaBooking)
        .filter(
            SeaBooking.user_id == current_user.id,
            Container.status.in_(["in_transit", "nearly_full", "full"]),
            Container.estimated_arrival_date < datetime.utcnow(),
        )
        .count()
    )

    if delayed_containers > 0:
        alerts.append(
            RiskAlert(
                alert_type="Delayed Shipment",
                description=f"You have {delayed_containers} shipment(s) that are past their estimated arrival date",
                severity="medium",
                affected_entities=[],
            )
        )

    # Check for high-cost sea_bookings
    expensive_sea_bookings = (
        db.query(SeaBooking)
        .filter(
            SeaBooking.user_id == current_user.id,
            SeaBooking.logistics_charge > 1000,  # Threshold for "expensive"
        )
        .count()
    )

    if expensive_sea_bookings > 2:  # More than 2 expensive sea_bookings
        alerts.append(
            RiskAlert(
                alert_type="High Shipping Costs",
                description="You have multiple high-cost shipping sea_bookings. Consider reviewing your shipping strategy",
                severity="medium",
                affected_entities=[],
            )
        )

    # Check for pending payments
    pending_payments = (
        db.query(SeaBooking)
        .filter(
            SeaBooking.user_id == current_user.id,
            SeaBooking.payment_status == "due",
        )
        .count()
    )

    if pending_payments > 0:
        alerts.append(
            RiskAlert(
                alert_type="Payment Due",
                description=f"You have {pending_payments} payment(s) due for received shipments",
                severity="high",
                affected_entities=[],
            )
        )

    return alerts


@router.get("/recommendations", response_model=List[Recommendation])
def get_recommendations(
    current_user: User = Depends(get_customer), db: Session = Depends(get_db)
):
    """
    GET /analytics/recommendations
    Suggestions: switch operator, use air cargo, increase stock, avoid certain goods
    """
    recommendations = []

    # Check container performance and suggest operator changes
    performance_result = get_container_performance(current_user, db)

    # Find operators with poor performance
    for operator, score in performance_result.operator_performance_score.items():
        if score < 5:  # Poor performing operator
            recommendations.append(
                Recommendation(
                    recommendation_type="Company Change",
                    title=f"Avoid company {operator}",
                    description=f"This company has a low performance score ({score}/10) due to frequent delays",
                    impact_score=7,
                )
            )

    # Check if user is only using sea shipping, recommend diversifying
    sea_bookings = (
        db.query(SeaBooking)
        .filter(SeaBooking.user_id == current_user.id)
        .count()
    )

    air_bookings = (
        db.query(ExpressAirCargoBooking)
        .filter(ExpressAirCargoBooking.customer_id == current_user.id)
        .count()
    )

    if sea_bookings > 0 and air_bookings == 0:
        recommendations.append(
            Recommendation(
                recommendation_type="Shipping Method",
                title="Consider air cargo for urgent shipments",
                description="You're only using sea shipping. Air cargo might be better for time-sensitive goods",
                impact_score=6,
            )
        )

    # Check for high delay rates
    if any(
        rate > 30 for rate in performance_result.delay_frequency.values()
    ):  # Over 30% delay rate
        recommendations.append(
            Recommendation(
                recommendation_type="Delay Reduction",
                title="Review shipping routes",
                description="High delay rates detected. Consider alternative shipping routes or companies",
                impact_score=8,
            )
        )

    # If no recommendations were found, add general ones
    if not recommendations:
        recommendations.append(
            Recommendation(
                recommendation_type="General",
                title="Optimize shipping strategy",
                description="Consider consolidating shipments to reduce costs and improve efficiency",
                impact_score=5,
            )
        )

    return recommendations
