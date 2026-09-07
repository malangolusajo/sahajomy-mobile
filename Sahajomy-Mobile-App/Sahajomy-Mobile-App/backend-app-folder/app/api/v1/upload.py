# app/api/v1/upload.py
import os
import tempfile

from app.core.cloudinary import upload_to_cloudinary
from app.core.config import settings
from app.core.dependencies import get_current_user, get_sourcing_agent
from app.core.upload_validation import validated_image_format
from app.database import get_db
from app.models.cargo_workspace import CargoCompany, CargoCompanyMembership
from app.models.sourcing import SourcingBatch
from app.models.user import User
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

router = APIRouter(prefix="/upload", tags=["Upload"])


async def _read_with_size_limit(file: UploadFile, max_bytes: int) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum file size is {settings.MAX_IMAGE_SIZE_MB}MB.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/product-image")
async def upload_product_image(
    file: UploadFile = File(...),
    batch_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_sourcing_agent),
):
    """Upload an image only into a batch owned by the active sourcing agent."""

    # Validate file type
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed.",
        )

    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    content = await _read_with_size_limit(file, max_bytes)
    _, file_extension = validated_image_format(content, file.content_type)

    if not batch_id:
        raise HTTPException(
            status_code=400, detail="A batch ID is required for product images."
        )
    batch = (
        db.query(SourcingBatch)
        .filter(SourcingBatch.id == batch_id, SourcingBatch.agent_id == current_user.id)
        .first()
    )
    if not batch:
        raise HTTPException(
            status_code=404, detail="Batch not found or not owned by this agent."
        )
    if batch.status == "closed":
        raise HTTPException(
            status_code=400, detail="Cannot upload images to a closed batch."
        )

    # Save temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Upload to Cloudinary
        image_url = upload_to_cloudinary(
            file=tmp_path,
            folder=f"products/{batch.id}",
            resource_type="image",
        )
        return {"url": image_url, "image_url": image_url}
    finally:
        # Clean up temp file
        os.unlink(tmp_path)


@router.post("/profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload profile image for current user"""

    # Validate file type - only allow common image formats
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, GIF, and WebP images are allowed.",
        )

    # Validate file size (max 5MB)
    content = await _read_with_size_limit(file, 5 * 1024 * 1024)
    _, file_extension = validated_image_format(
        content, file.content_type, allow_gif=True
    )

    # Save temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Upload to Cloudinary, then persist the URL immediately so it survives logout/login.
        result = upload_to_cloudinary(
            file=tmp_path,
            folder=f"user_content/{current_user.id}/profile",
            public_id="profile_image",
            resource_type="image",
            overwrite=True,
            invalidate=True,
            tags=["profile_image"],
            context={"uploaded_by": str(current_user.id)},
        )
        image_url = result
        current_user.profile_image_url = image_url
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        return {
            "url": image_url,
            "profile_image_url": image_url,
            "message": "Profile image uploaded successfully",
        }
    finally:
        # Clean up temp file
        os.unlink(tmp_path)


@router.post("/company-logo")
async def upload_company_logo(
    file: UploadFile = File(...),
    company_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a company logo (super admin or a member of that company).

    - Super admin may upload for any company, or without a company_id when
      registering a brand-new company (logo stored under company_branding).
    - Cargo admin may only upload for a company they belong to.
    """
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, GIF, and WebP images are allowed.",
        )

    content = await _read_with_size_limit(file, 2 * 1024 * 1024)
    _, file_extension = validated_image_format(
        content, file.content_type, allow_gif=True
    )

    company = None
    if company_id:
        company = db.query(CargoCompany).filter(CargoCompany.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found.")
        is_super_admin = current_user.role == "super_admin"
        if not is_super_admin:
            membership = (
                db.query(CargoCompanyMembership)
                .filter(
                    CargoCompanyMembership.company_id == company.id,
                    CargoCompanyMembership.user_id == current_user.id,
                    CargoCompanyMembership.status == "active",
                )
                .first()
            )
            if not membership:
                raise HTTPException(
                    status_code=403,
                    detail="Only super admins or company members can upload this company's logo.",
                )
    else:
        if current_user.role != "super_admin":
            raise HTTPException(
                status_code=403,
                detail="Only super admins can upload a company logo without a company.",
            )

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if company:
            image_url = upload_to_cloudinary(
                file=tmp_path,
                folder=f"companies/{company.id}/branding",
                public_id="company_logo",
                resource_type="image",
                overwrite=True,
                invalidate=True,
                company_id=str(company.id),
                db_session=db,
                uploaded_by_id=str(current_user.id),
                asset_kind="company_logo",
            )
            company.logo_url = image_url
            db.add(company)
            db.commit()
        else:
            image_url = upload_to_cloudinary(
                file=tmp_path,
                folder="company_branding/pending",
                resource_type="image",
            )
        return {"url": image_url, "logo_url": image_url}
    finally:
        os.unlink(tmp_path)
