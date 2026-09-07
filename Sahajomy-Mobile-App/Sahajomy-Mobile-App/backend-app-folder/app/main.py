"""
Sahajomy Platform API v3.0
FastAPI backend aligned with Sahajomy Platform technical specification.
"""

import logging
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import app.models as _models  # noqa: F401 - registers all models
from app.api.v1.agizisha import agent_router as agizisha_agent_router
from app.api.v1.agizisha import public_router as agizisha_public_router
from app.api.v1.air_cargo_pricing import (
    cargo_admin_router as air_cargo_pricing_cargo_admin_router,
)
from app.api.v1.air_cargo_pricing import (
    super_admin_router as air_cargo_pricing_super_admin_router,
)
from app.api.v1.auth import router as auth_router
from app.api.v1.cargo_admin.routes import router as cargo_admin_router
from app.api.v1.cargo_company_registrations import (
    router as cargo_company_registration_router,
)
from app.api.v1.customer.routes import router as customer_router
from app.api.v1.fcl_quote_requests import router as fcl_quote_requests_router
from app.api.v1.financial_analytics import (
    cargo_router as financial_analytics_cargo_router,
)
from app.api.v1.financial_analytics import (
    platform_router as financial_analytics_platform_router,
)
from app.api.v1.forwarding import router as forwarding_router
from app.api.v1.interactions import router as interactions_router
from app.api.v1.notifications import (
    router as notifications_router,  # Added notifications router
)
from app.api.v1.public import router as public_router
from app.api.v1.smartphone_warehouse import (
    cargo_router as smartphone_warehouse_cargo_router,
)
from app.api.v1.smartphone_warehouse import (
    customer_router as smartphone_warehouse_customer_router,
)
from app.api.v1.sourcing_agent.routes import router as sourcing_agent_router
from app.api.v1.sourcing_agents import router as sourcing_agent_registration_router
from app.api.v1.subscriptions import company_router as company_subscriptions_router
from app.api.v1.subscriptions import (
    super_admin_router as super_admin_subscriptions_router,
)
from app.api.v1.super_admin.companies import router as super_admin_companies_router
from app.api.v1.super_admin.routes import router as super_admin_router
from app.api.v1.tracking import router as tracking_router
from app.api.v1.upload import router as upload_router
from app.api.v1.warehouse_automation import (
    cargo_router as warehouse_automation_cargo_router,
)
from app.api.v1.warehouse_automation import (
    customer_router as warehouse_automation_customer_router,
)
from app.api.v1.warehouse_automation import (
    super_admin_router as warehouse_automation_super_admin_router,
)
from app.api.v1.workspaces import router as workspaces_router
from app.core.config import settings
from app.core.logging_config import log_error, setup_logging
from app.core.middleware import (
    CSRFMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.redis import close_redis, init_redis
from app.database import SessionLocal, engine
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Configure logging using centralized configuration
setup_logging(settings.LOG_LEVEL if hasattr(settings, "LOG_LEVEL") else "WARNING")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sahajomy Platform API",
    description="China-to-Africa cargo booking, sourcing, and shipment tracking platform",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ========== GLOBAL EXCEPTION HANDLERS ==========


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions (404, 403, 400, etc.)"""
    # Generate reference ID for tracking
    reference_id = str(uuid.uuid4())[:8]

    # Log internal error details with structured logging
    log_error(
        message=str(exc.detail),
        error_code=f"http_{exc.status_code}",
        reference_id=reference_id,
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        security_event=("authorization_denied" if exc.status_code == 403 else None),
        user_agent=request.headers.get("user-agent", ""),
        client_ip=request.client.host if request.client else "",
    )

    # Return user-friendly message based on status code
    if exc.status_code == 404:
        user_message = "The requested resource was not found."
    elif exc.status_code == 403:
        user_message = "You don't have permission to access this resource."
    elif exc.status_code == 401:
        user_message = "Please log in to continue."
    elif exc.status_code == 400:
        user_message = (
            str(exc.detail) if len(str(exc.detail)) < 100 else "Invalid request."
        )
    else:
        user_message = str(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            # Keep both keys for backward compatibility with older API clients/tests.
            "message": user_message,
            "detail": user_message,
            "error_code": f"http_{exc.status_code}",
            "reference_id": reference_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors (invalid input data)"""
    reference_id = str(uuid.uuid4())[:8]

    # Log internal validation details with structured logging
    log_error(
        message="Validation error",
        error_code="validation_error",
        reference_id=reference_id,
        path=request.url.path,
        method=request.method,
        details=exc.errors(),
        user_agent=request.headers.get("user-agent", ""),
        client_ip=request.client.host if request.client else "",
    )

    # Do not include Pydantic's raw `input` value here: a validation error can
    # occur on credentials or other sensitive request fields.  The location
    # and message are sufficient for clients to tell a user exactly what to
    # correct.
    validation_details = [
        {
            "loc": error.get("loc", []),
            "msg": error.get("msg", "Invalid value"),
            "type": error.get("type"),
        }
        for error in exc.errors()
    ]

    # Return user-friendly, field-level feedback rather than an opaque 422.
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "success": False,
            "message": "Invalid data provided. Please check your input.",
            "detail": validation_details,
            "error_code": "validation_error",
            "reference_id": reference_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    reference_id = str(uuid.uuid4())[:8]

    # Log full error details internally with structured logging
    log_error(
        message=str(exc),
        error_code="internal_error",
        reference_id=reference_id,
        path=request.url.path,
        method=request.method,
        exception=traceback.format_exc(),
        user_agent=request.headers.get("user-agent", ""),
        client_ip=request.client.host if request.client else "",
    )

    # Return generic user-friendly message
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected error occurred. Our team has been notified.",
            "error_code": "internal_error",
            "reference_id": reference_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ================================================

# CORS middleware
cors_allow_origins = [
    "https://sahajomy.co.tz",
    "https://www.sahajomy.co.tz",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
cors_allow_origin_regex = None
if settings.ENVIRONMENT == "development":
    cors_allow_origin_regex = r"http://localhost(:\\d+)?|http://127\\.0\\.0\\.1(:\\d+)?"

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_origin_regex=cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "X-Sahajomy-Workspace",
        "X-Sahajomy-Company",
        "X-Sahajomy-Branch",
    ],
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)

# Rate limiting for sensitive endpoints
rate_limits = {
    "/api/v1/auth/send-otp": (5, 60),
    "/api/v1/auth/verify-otp": (10, 60),
    "/api/v1/auth/mfa": (10, 60),
    "/api/v1/auth/refresh": (20, 60),
    "/api/v1/auth/logout": (20, 60),
    "/api/v1/public/cargo-operators/register": (5, 3600),
    "/api/v1/public/cargo-operators/logo-upload": (5, 3600),
    "/api/v1/customer/sea-bookings": (30, 60),
    "/api/v1/customer/express-air-cargo/book": (20, 60),
    "/api/v1/customer/batches": (30, 60),
    "/api/v1/customer/shared-batch": (30, 60),
    "/api/v1/customer/warehouse-access": (20, 60),
    "/api/v1/cargo_admin/warehouse-automation/collection": (30, 60),
    "/api/v1/cargo_admin/warehouse-automation/warehouses": (10, 60),
    # Public conversion endpoint: keep a tighter limit than browsing so a
    # browser can browse normally but cannot flood agents with requests.
    "/api/v1/public/agizisha/orders": (
        settings.AGIZISHA_ORDER_MAX_PER_IP_PER_HOUR,
        3600,
    ),
}
app.add_middleware(RateLimitMiddleware, limits=rate_limits)

# API routes
PREFIX = "/api/v1"
app.include_router(auth_router, prefix=PREFIX)
app.include_router(workspaces_router, prefix=PREFIX)
app.include_router(company_subscriptions_router, prefix=PREFIX)
app.include_router(super_admin_subscriptions_router, prefix=PREFIX)
app.include_router(super_admin_router, prefix=PREFIX)
app.include_router(super_admin_companies_router, prefix=PREFIX)
app.include_router(cargo_admin_router, prefix=PREFIX)
app.include_router(cargo_company_registration_router, prefix=PREFIX)
app.include_router(air_cargo_pricing_cargo_admin_router, prefix=PREFIX)
app.include_router(air_cargo_pricing_super_admin_router, prefix=PREFIX)
app.include_router(sourcing_agent_router, prefix=PREFIX)
app.include_router(sourcing_agent_registration_router, prefix=PREFIX)
app.include_router(customer_router, prefix=PREFIX)
app.include_router(forwarding_router, prefix=PREFIX)
app.include_router(warehouse_automation_cargo_router, prefix=PREFIX)
app.include_router(warehouse_automation_customer_router, prefix=PREFIX)
app.include_router(warehouse_automation_super_admin_router, prefix=PREFIX)
app.include_router(smartphone_warehouse_cargo_router, prefix=PREFIX)
app.include_router(smartphone_warehouse_customer_router, prefix=PREFIX)
app.include_router(financial_analytics_cargo_router, prefix=PREFIX)
app.include_router(financial_analytics_platform_router, prefix=PREFIX)
app.include_router(fcl_quote_requests_router, prefix=PREFIX)
app.include_router(upload_router, prefix=PREFIX)
app.include_router(public_router, prefix=PREFIX)
app.include_router(agizisha_public_router, prefix=PREFIX)
app.include_router(agizisha_agent_router, prefix=PREFIX)
app.include_router(tracking_router, prefix=PREFIX)
app.include_router(notifications_router, prefix=PREFIX)  # Include notifications router
app.include_router(interactions_router, prefix=PREFIX)


# Startup and Shutdown Events
def _ensure_default_goods_type_templates() -> None:
    """Seed useful starter fields while leaving every template admin-editable."""
    from app.models.container import GoodsType, GoodsTypeAttributeTemplate

    by_category = {
        "textiles and apparel": [
            ("material", "Material", "text", [], True, False),
            (
                "gender",
                "Gender",
                "select",
                ["Women", "Men", "Unisex", "Children"],
                False,
                False,
            ),
            (
                "season",
                "Season",
                "select",
                ["All season", "Summer", "Winter", "Spring", "Autumn"],
                False,
                False,
            ),
            (
                "size",
                "Size",
                "multiselect",
                ["XS", "S", "M", "L", "XL", "XXL"],
                True,
                True,
            ),
            (
                "color",
                "Color",
                "multiselect",
                ["Black", "White", "Red", "Blue"],
                True,
                True,
            ),
        ],
        "footwear and travel goods": [
            (
                "eu_size",
                "EU Size",
                "multiselect",
                [str(size) for size in range(36, 46)],
                True,
                True,
            ),
            ("color", "Color", "multiselect", ["Black", "White", "Brown"], True, True),
            ("material", "Material", "text", [], False, False),
        ],
        "electronics and ict": [
            ("voltage", "Voltage", "text", [], False, False),
            ("power", "Power", "text", [], False, False),
            ("model", "Model", "text", [], False, False),
            (
                "plug_type",
                "Plug Type",
                "select",
                ["EU", "UK", "US", "Universal"],
                False,
                False,
            ),
        ],
        "home, furniture and decor": [
            ("length", "Length", "number", [], False, False),
            ("width", "Width", "number", [], False, False),
            ("height", "Height", "number", [], False, False),
            ("material", "Material", "text", [], False, False),
        ],
        "cosmetics and personal care": [
            ("volume", "Volume", "text", [], False, False),
            ("ingredients", "Ingredients", "text", [], False, False),
            (
                "skin_type",
                "Skin Type",
                "select",
                ["All skin types", "Dry", "Oily", "Sensitive", "Combination"],
                False,
                False,
            ),
        ],
    }
    packaging = [
        ("length", "Length", "number", [], True, False),
        ("width", "Width", "number", [], True, False),
        ("height", "Height", "number", [], True, False),
        ("unit", "Unit", "select", ["cm", "mm"], True, False),
        ("thickness", "Thickness", "text", [], False, False),
        ("material", "Material", "text", [], False, False),
        (
            "customization",
            "Customization",
            "select",
            ["Logo Printing", "Custom Design", "No Printing"],
            False,
            False,
        ),
    ]
    db = SessionLocal()
    try:
        for goods_type in db.query(GoodsType).all():
            category_name = (
                (goods_type.category.name if goods_type.category else "")
                .strip()
                .lower()
            )
            specs = (
                packaging
                if "packaging" in goods_type.name.lower()
                else by_category.get(category_name, [])
            )
            if not specs:
                continue
            existing = {
                key
                for (key,) in db.query(GoodsTypeAttributeTemplate.key).filter(
                    GoodsTypeAttributeTemplate.goods_type_id == goods_type.id
                )
            }
            for sort_order, (
                key,
                label,
                field_type,
                allowed_values,
                required,
                variant,
            ) in enumerate(specs):
                if key not in existing:
                    db.add(
                        GoodsTypeAttributeTemplate(
                            goods_type_id=goods_type.id,
                            key=key,
                            label=label,
                            field_type=field_type,
                            allowed_values=allowed_values,
                            is_required=required,
                            customer_visible=True,
                            is_variant_option=variant,
                            sort_order=sort_order,
                        )
                    )
        db.commit()
    except Exception as exc:  # noqa: BLE001 - seed must never block API startup
        db.rollback()
        logger.warning(f"Default Goods Type template seed skipped: {exc}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize services on startup"""
    logger.info("Starting up Sahajomy API...")

    # Retry database connection with exponential backoff
    max_retries = 5
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            # Test database connection first
            from sqlalchemy import text

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            _ensure_default_goods_type_templates()

            # Register the running loop so sync endpoints can push realtime
            # notification events over websockets (send_to_user_sync no-ops
            # without this).
            import asyncio

            from app.services.realtime_notifications import (
                notification_realtime_manager,
            )

            notification_realtime_manager.set_loop(asyncio.get_running_loop())

            await init_redis()
            logger.info("Database connection successful; Alembic schema is ready")
            break

        except Exception as e:
            logger.warning(
                f"Database connection attempt {attempt + 1} failed: {str(e)}"
            )
            if attempt < max_retries - 1:
                import time

                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(
                    "Startup initialization failed after "
                    f"{max_retries} attempts: {str(e)}"
                )

    try:
        yield
    finally:
        logger.info("Shutting down Sahajomy API...")
        try:
            await close_redis()
        except Exception as e:
            logger.error(f"Error closing Redis: {str(e)}")


app.router.lifespan_context = lifespan


@app.get("/")
def root():
    return {
        "service": "Sahajomy API",
        "version": "3.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health")
def health():
    """Health check endpoint for monitoring"""
    from app.core.redis import redis_client

    redis_status = "connected" if redis_client else "disconnected"

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.0.0",
        "environment": settings.ENVIRONMENT,
        "services": {
            "database": "connected",
            "redis": redis_status,
            "cloudinary": "configured" if settings.CLOUDINARY_CLOUD_NAME else "missing",
        },
    }
