"""
Sahajomy Platform v3.0 - All Models Registration
Register all models here for proper SQLAlchemy initialization.
"""

from .air_cargo import (
    AirCargoGoodsTypeRequest,
    AirCargoRate,
    AirDepartureSchedule,
    ExpressAirCargoBooking,
)
from .cargo_customs import (
    CargoCustomer,
    CargoCustomerAddress,
    CargoCustomerContact,
    CustomsPackingList,
    CustomsPackingListItem,
    ManualCargoIntake,
    ManualCargoIntakeItem,
)
from .cargo_company import CargoOperatorProfile, OperatorGovernanceCase
from .cargo_workspace import (
    CargoBranch,
    CargoCompany,
    CargoCompanyMembership,
    CargoPermission,
    CargoRole,
    CargoStaffInvitation,
)
from .container import (
    Container,
    SeaBooking,
    SeaBookingGoods,
    GoodsCategory,
    GoodsType,
    GoodsTypeAlias,
    GoodsTypeAttributeTemplate,
    Route,
    Warehouse,
)
from .customer_china_address import CustomerChinaAddress
from .finance import (
    AuditLog,
    CommissionSettings,
    ContainerConsolidatedPackingList,
    Notification,
    Payment,
    Receipt,
    ReceiptScan,
    SeaBookingInvoice,
    SeaBookingPackingList,
    SeaBookingPackingListItem,
)
from .financial_analytics import (
    CargoProfitabilitySnapshot,
    FinanceCategory,
    FinancialReceivable,
    FinancialTransaction,
)
from .interaction import Interaction, InteractionReaction
from .packing_list import PackingList  # NEW: Add packing list models
from .packing_list import PackingListItem
from .quote_request import QuoteRequest
from .shipment_orders import ShipmentOrder  # NEW: Add shipment orders model
from .shipping_mark import ShippingMark
from .subscription import (
    CompanyStorageAsset,
    CompanySubscription,
    CompanyUsageCounter,
    PlanEntitlement,
    ProviderCostSnapshot,
    SubscriptionPlan,
    SubscriptionUsageEvent,
)
from .smartphone_warehouse import (
    LoadingScan,
    LoadingSession,
    ParcelBookingLink,
    ParcelScanEvent,
    ShipmentMilestone,
    WarehouseParcel,
)
from .sourcing import (
    AgizishaOrder,
    BatchGoodsType,
    BatchShareToken,
    SourcingBatch,
    SourcingOrder,
    SourcingOrderItem,
    SourcingProduct,
    SourcingProductVariant,
)
from .sourcing_agent import SourcingAgent
from .tracking import NotificationTemplate  # NEW: Add tracking models
from .tracking import TrackingEvent
from .user import Guest, OTPVerification, RefreshToken, User
from .warehouse_automation import (
    CargoAdminFeatureEntitlement,
    WarehouseCollectionRequest,
    WarehouseCollectionRequestItem,
)

# ─── EXPORTS ─────────────────────────────────────────────

__all__ = [
    # User
    "User",
    "Guest",
    "OTPVerification",
    "RefreshToken",
    # Container
    "Route",
    "Warehouse",
    "GoodsCategory",
    "GoodsType",
    "GoodsTypeAlias",
    "GoodsTypeAttributeTemplate",
    "Container",
    "SeaBooking",
    "SeaBookingGoods",
    "CargoOperatorProfile",
    "OperatorGovernanceCase",
    "CargoCompany",
    "CargoBranch",
    "CargoCompanyMembership",
    "CargoRole",
    "CargoPermission",
    "CargoStaffInvitation",
    "SubscriptionPlan",
    "PlanEntitlement",
    "CompanySubscription",
    "CompanyUsageCounter",
    "CompanyStorageAsset",
    "ProviderCostSnapshot",
    "SubscriptionUsageEvent",
    # Cargo customer CRM and customs documents
    "CargoCustomer",
    "CargoCustomerContact",
    "CargoCustomerAddress",
    "CustomsPackingList",
    "CustomsPackingListItem",
    "ManualCargoIntake",
    "ManualCargoIntakeItem",
    "CargoOperatorProfile",
    "CargoAdminFeatureEntitlement",
    "WarehouseCollectionRequest",
    "WarehouseCollectionRequestItem",
    "WarehouseParcel",
    "ParcelScanEvent",
    "ParcelBookingLink",
    "LoadingSession",
    "LoadingScan",
    "ShipmentMilestone",
    # Sourcing
    "SourcingBatch",
    "AgizishaOrder",
    "BatchGoodsType",
    "BatchShareToken",
    "SourcingProduct",
    "SourcingProductVariant",
    "SourcingOrder",
    "SourcingOrderItem",
    "SourcingAgent",
    # Air Cargo
    "ExpressAirCargoBooking",
    "AirCargoRate",
    "AirCargoGoodsTypeRequest",
    "AirDepartureSchedule",
    "CustomerChinaAddress",
    # Shipping Mark
    "ShippingMark",
    # Finance
    "FinancialTransaction",
    "FinancialReceivable",
    "FinanceCategory",
    "CargoProfitabilitySnapshot",
    "Payment",
    "CommissionSettings",
    "SeaBookingInvoice",
    "SeaBookingPackingList",
    "SeaBookingPackingListItem",
    "ContainerConsolidatedPackingList",
    "Receipt",
    "ReceiptScan",
    "Notification",
    "AuditLog",
    # NEW: Tracking
    "TrackingEvent",
    "NotificationTemplate",
    # NEW: Shipment Orders
    "ShipmentOrder",
    "Interaction",
    "InteractionReaction",
    # NEW: Packing List
    "PackingList",
    "PackingListItem",
    "QuoteRequest",
]
