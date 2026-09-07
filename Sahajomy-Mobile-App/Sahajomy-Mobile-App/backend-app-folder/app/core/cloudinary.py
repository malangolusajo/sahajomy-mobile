# app/core/cloudinary.py
import os
from datetime import datetime
from typing import Any, Optional, Union

import cloudinary
import cloudinary.uploader
from app.core.config import settings


def configure_cloudinary():
    """Initialize Cloudinary with credentials from settings"""
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_to_cloudinary(
    file_path: Union[str, Any] = None,
    user_id: Optional[str] = None,
    instagram_username: Optional[str] = None,
    **kwargs,
):
    """
    Upload content to Cloudinary.

    Supports two call patterns:
    1) Legacy product upload:
       upload_to_cloudinary(file_path, user_id, instagram_username=None) -> dict
    2) Generic upload used by document/QR services:
       upload_to_cloudinary(
           file=..., folder=..., public_id=..., resource_type=...
       ) -> str
    """
    try:
        # Generic mode (document/QR uploads)
        if kwargs:
            company_id = kwargs.pop("company_id", None)
            db_session = kwargs.pop("db_session", None)
            uploaded_by_id = kwargs.pop("uploaded_by_id", None)
            asset_kind = kwargs.pop("asset_kind", "company_upload")
            upload_source = kwargs.pop("file", file_path)
            if upload_source is None:
                raise ValueError("Missing upload source for Cloudinary upload")
            held_bytes = 0
            if isinstance(upload_source, (str, os.PathLike)) and os.path.exists(
                upload_source
            ):
                held_bytes = os.path.getsize(upload_source)
            elif isinstance(upload_source, (bytes, bytearray)):
                held_bytes = len(upload_source)
            elif hasattr(upload_source, "getbuffer"):
                held_bytes = len(upload_source.getbuffer())
            tracking_enabled = bool(company_id and db_session)
            if tracking_enabled:
                from app.services.subscriptions import hold_storage

                hold_storage(db_session, company_id, held_bytes)
                raw_folder = str(kwargs.get("folder") or "uploads").strip("/")
                kwargs["folder"] = f"companies/{company_id}/{raw_folder}"
            try:
                result = cloudinary.uploader.upload(upload_source, **kwargs)
                url = result.get("secure_url") or result.get("url")
                if tracking_enabled:
                    from app.services.subscriptions import finalize_storage_asset

                    finalize_storage_asset(
                        db_session,
                        company_id,
                        public_id=result["public_id"],
                        secure_url=url,
                        byte_count=int(result.get("bytes") or held_bytes),
                        held_bytes=held_bytes,
                        resource_type=result.get("resource_type") or kwargs.get("resource_type") or "image",
                        asset_kind=asset_kind,
                        uploaded_by_id=uploaded_by_id,
                    )
                return url
            except Exception:
                if tracking_enabled:
                    from app.services.subscriptions import release_storage_hold

                    release_storage_hold(db_session, company_id, held_bytes)
                raise

        # Legacy mode (product uploads)
        if file_path is None or user_id is None:
            raise ValueError(
                "file_path and user_id are required for legacy upload mode"
            )

        upload_purpose = instagram_username or "instagram_import"
        if upload_purpose in {"direct_upload", "express_air_cargo"}:
            folder = f"user_content/{user_id}/{upload_purpose}"
            tags = ["product_image", upload_purpose]
            context_source = upload_purpose
        else:
            folder = f"user_content/{user_id}/products"
            tags = ["product_image", "instagram_import"]
            context_source = instagram_username or "unknown"

        result = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            tags=tags,
            context={
                "uploaded_by": str(user_id),
                "instagram_username": context_source,
                "upload_timestamp": str(datetime.utcnow()),
            },
        )
        return {
            "secure_url": result["secure_url"],
            "public_id": result["public_id"],
            "format": result["format"],
        }
    except Exception as e:
        raise Exception(f"Cloudinary upload failed: {str(e)}")


def build_optimized_cloudinary_image_url(
    image_url: Optional[str],
    *,
    width: int = 720,
    height: int = 720,
) -> Optional[str]:
    """
    Build a non-cropping optimized Cloudinary delivery URL.

    Keeps the full image visible (no crop) using
    `c_pad` + `object-contain`-like behavior.
    Returns original URL for non-Cloudinary sources.
    """
    if not image_url:
        return image_url

    raw_url = str(image_url).strip()
    if not raw_url or "res.cloudinary.com" not in raw_url or "/upload/" not in raw_url:
        return raw_url

    optimized_prefix = "/upload/f_auto,q_auto,dpr_auto,c_pad,b_auto,"
    if optimized_prefix in raw_url:
        return raw_url

    safe_width = max(int(width or 720), 1)
    safe_height = max(int(height or 720), 1)
    transform = f"f_auto,q_auto,dpr_auto,c_pad,b_auto,w_{safe_width},h_{safe_height}"
    base, remainder = raw_url.split("/upload/", 1)

    # If the URL already contains a transformation segment, replace it.
    parts = remainder.split("/", 1)
    if len(parts) == 2 and not parts[0].startswith("v"):
        remainder = parts[1]

    return f"{base}/upload/{transform}/{remainder}"
