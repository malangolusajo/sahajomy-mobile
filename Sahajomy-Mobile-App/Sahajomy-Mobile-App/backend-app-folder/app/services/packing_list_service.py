"""
Packing List Service for Sourcing Batches.
Handles creation, management, and calculation logic for packing lists.
"""

import base64
import uuid
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

import qrcode
from app.core.cloudinary import upload_to_cloudinary
from app.core.url_builder import build_public_url
from app.models.packing_list import PackingList, PackingListItem
from app.models.sourcing import (
    SourcingBatch,
    SourcingOrder,
    SourcingOrderItem,
    SourcingProduct,
)
from app.models.user import User
from app.services.document_generation_service import DocumentGenerationService
from app.services.document_branding import sourcing_agent_document_branding
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class PackingListService:
    """Service class for packing list operations."""

    @staticmethod
    def create_packing_list(
        db: Session,
        batch_id: str,
        agent_id: str,
        name: str,
        description: Optional[str] = None,
    ) -> PackingList:
        """
        Create a new packing list for a sourcing batch.

        Args:
            db: Database session
            batch_id: ID of the sourcing batch
            agent_id: ID of the sourcing agent creating the list
            name: Name of the packing list
            description: Optional description

        Returns:
            Created PackingList instance
        """
        try:
            # Verify batch exists and belongs to agent
            batch = (
                db.query(SourcingBatch)
                .filter(
                    SourcingBatch.id == batch_id, SourcingBatch.agent_id == agent_id
                )
                .first()
            )

            if not batch:
                raise ValueError("Batch not found or does not belong to this agent")

            # Create packing list
            packing_list = PackingList(
                batch_id=batch_id,
                created_by=agent_id,
                name=name,
                description=description,
            )

            db.add(packing_list)
            db.commit()
            db.refresh(packing_list)

            # Generate and store QR code
            qr_code_url = PackingListService._generate_qr_code(db, packing_list.id)
            if qr_code_url:
                packing_list.qr_code_url = qr_code_url
                db.commit()
                db.refresh(packing_list)

            return packing_list

        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error creating packing list: {str(e)}")
        except Exception as e:
            db.rollback()
            raise Exception(f"Error creating packing list: {str(e)}")

    @staticmethod
    def add_item_to_packing_list(
        db: Session, packing_list_id: str, item_data: Dict[str, Any]
    ) -> PackingListItem:
        """
        Add an item to a packing list with automatic calculations.

        Args:
            db: Database session
            packing_list_id: ID of the packing list
            item_data: Dictionary containing item fields

        Returns:
            Created PackingListItem instance with calculated fields
        """
        try:
            # Verify packing list exists
            packing_list = (
                db.query(PackingList).filter(PackingList.id == packing_list_id).first()
            )

            if not packing_list:
                raise ValueError("Packing list not found")

            # Create item with required fields
            item = PackingListItem(
                packing_list_id=packing_list_id,
                item_name=item_data.get("item_name"),
                item_picture=item_data.get("item_picture"),
                price_per_piece=item_data.get("price_per_piece"),
                item_code=item_data.get("item_code"),
                cartons=item_data.get("cartons"),
                items_per_carton=item_data.get("items_per_carton"),
                cbm_per_carton=item_data.get("cbm_per_carton"),
                kilogram_per_carton=item_data.get("kilogram_per_carton"),
            )

            # Perform calculations
            item.calculate_totals()

            db.add(item)
            db.commit()
            db.refresh(item)

            return item

        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error adding item: {str(e)}")
        except Exception as e:
            db.rollback()
            raise Exception(f"Error adding item: {str(e)}")

    @staticmethod
    def update_packing_list_item(
        db: Session, item_id: str, item_data: Dict[str, Any]
    ) -> PackingListItem:
        """
        Update a packing list item with recalculated totals.

        Args:
            db: Database session
            item_id: ID of the item to update
            item_data: Dictionary containing updated fields

        Returns:
            Updated PackingListItem instance
        """
        try:
            item = (
                db.query(PackingListItem).filter(PackingListItem.id == item_id).first()
            )

            if not item:
                raise ValueError("Item not found")

            # Update fields
            for field, value in item_data.items():
                if hasattr(item, field) and value is not None:
                    setattr(item, field, value)

            # Recalculate totals
            item.calculate_totals()

            db.commit()
            db.refresh(item)

            return item

        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error updating item: {str(e)}")
        except Exception as e:
            db.rollback()
            raise Exception(f"Error updating item: {str(e)}")

    @staticmethod
    def get_packing_list_by_id(
        db: Session, packing_list_id: str
    ) -> Optional[PackingList]:
        """Get a packing list by ID with all items."""
        return db.query(PackingList).filter(PackingList.id == packing_list_id).first()

    @staticmethod
    def get_packing_lists_by_batch(db: Session, batch_id: str) -> List[PackingList]:
        """Get all packing lists for a batch."""
        return db.query(PackingList).filter(PackingList.batch_id == batch_id).all()

    @staticmethod
    def get_agent_packing_lists(db: Session, agent_id: str) -> List[PackingList]:
        """Get all packing lists created by an agent."""
        return (
            db.query(PackingList)
            .join(SourcingBatch)
            .filter(SourcingBatch.agent_id == agent_id)
            .all()
        )

    @staticmethod
    def delete_packing_list(db: Session, packing_list_id: str, agent_id: str) -> bool:
        """Delete a packing list if it belongs to the agent."""
        try:
            packing_list = (
                db.query(PackingList)
                .join(SourcingBatch)
                .filter(
                    PackingList.id == packing_list_id,
                    SourcingBatch.agent_id == agent_id,
                )
                .first()
            )

            if not packing_list:
                return False

            db.delete(packing_list)
            db.commit()
            return True

        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error deleting packing list: {str(e)}")

    @staticmethod
    def _generate_qr_code(db: Session, packing_list_id: str) -> Optional[str]:
        """
        Generate QR code for packing list and upload to Cloudinary.

        Args:
            db: Database session (for potential future use)
            packing_list_id: ID of the packing list

        Returns:
            URL to uploaded QR code image, or None if failed
        """
        try:
            # Create QR code data (URL to packing list details)
            qr_data = build_public_url(f"/agent/packing-lists/{packing_list_id}")

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to bytes
            img_buffer = BytesIO()
            img.save(img_buffer, format="PNG")
            img_buffer.seek(0)

            # Upload to Cloudinary
            qr_code_url = upload_to_cloudinary(
                file=img_buffer,
                folder="packing_lists/qr_codes",
                public_id=f"qr_{packing_list_id}",
                resource_type="image",
            )

            return qr_code_url

        except Exception as e:
            # Log error but don't fail the entire operation
            print(
                f"Warning: Failed to generate QR code for packing list {packing_list_id}: {str(e)}"
            )
            return None

    @staticmethod
    def recalculate_all_items(
        db: Session, packing_list_id: str
    ) -> List[PackingListItem]:
        """
        Recalculate all items in a packing list (useful after bulk updates).

        Args:
            db: Database session
            packing_list_id: ID of the packing list

        Returns:
            List of recalculated items
        """
        try:
            items = (
                db.query(PackingListItem)
                .filter(PackingListItem.packing_list_id == packing_list_id)
                .all()
            )

            for item in items:
                item.calculate_totals()

            db.commit()
            return items

        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error recalculating items: {str(e)}")

    @staticmethod
    def generate_packing_list_from_closed_batch(
        db: Session, batch_id: str, agent_id: str
    ) -> Dict[str, Any]:
        """
        Generate a complete packing list from all orders in a closed batch.
        Creates both database records and downloadable documents (Excel/PDF).

        Args:
            db: Database session
            batch_id: ID of the closed sourcing batch
            agent_id: ID of the sourcing agent

        Returns:
            Dictionary containing packing list details and document URLs
        """
        try:
            # Verify batch exists, is closed, and belongs to agent
            batch = (
                db.query(SourcingBatch)
                .filter(
                    SourcingBatch.id == batch_id,
                    SourcingBatch.agent_id == agent_id,
                    SourcingBatch.status == "closed",
                )
                .first()
            )

            if not batch:
                raise ValueError(
                    "Closed batch not found or does not belong to this agent"
                )

            # Get all orders for this batch with related data
            orders = (
                db.query(SourcingOrder)
                .filter(SourcingOrder.batch_id == batch_id)
                .options(
                    # Load related items and products
                )
                .all()
            )

            if not orders:
                raise ValueError("No orders found in this batch")

            # Create packing list record
            packing_list_name = f"Packing List - {batch.title} - {datetime.utcnow().strftime('%Y-%m-%d')}"
            packing_list = PackingList(
                batch_id=batch_id,
                created_by=agent_id,
                name=packing_list_name,
                description=f"Auto-generated packing list from {len(orders)} orders in closed batch",
            )

            db.add(packing_list)
            db.flush()  # Get ID without committing

            # Aggregate items from all orders
            aggregated_items = {}

            for order in orders:
                for order_item in order.items:
                    product = order_item.product
                    if not product:
                        continue

                    # Create item key based on product characteristics
                    item_key = (
                        f"{product.name}_{product.price_per_unit}_{order_item.currency}"
                    )

                    if item_key not in aggregated_items:
                        aggregated_items[item_key] = {
                            "item_name": product.name,
                            "item_picture": product.image_url,
                            "price_per_piece": float(product.price_per_unit),
                            "currency": order_item.currency,
                            "total_quantity": 0,
                            "total_cbm": 0.0,
                            "total_amount": 0.0,
                            # Store product info for better defaults
                            "cbm_per_unit": (
                                float(product.cbm_per_unit)
                                if product.cbm_per_unit
                                else 0.0
                            ),
                        }

                    # Aggregate quantities and amounts
                    aggregated_items[item_key]["total_quantity"] += order_item.quantity
                    aggregated_items[item_key]["total_cbm"] += float(
                        order_item.total_cbm
                    )
                    aggregated_items[item_key]["total_amount"] += float(
                        order_item.total_price
                    )

            # Create packing list items with smart defaults
            packing_list_items = []
            for idx, (key, item_data) in enumerate(aggregated_items.items(), 1):
                total_quantity = item_data["total_quantity"]
                total_cbm = item_data["total_cbm"]
                cbm_per_unit = item_data["cbm_per_unit"]

                # Smart carton configuration defaults
                if total_quantity <= 10:
                    # Small quantities: 1 carton
                    cartons = 1
                    items_per_carton = total_quantity
                elif total_quantity <= 50:
                    # Medium quantities: aim for ~25 items per carton
                    cartons = max(1, (total_quantity + 24) // 25)  # Round up division
                    items_per_carton = total_quantity // cartons
                    # Distribute remaining items
                    if total_quantity % cartons > 0:
                        items_per_carton = (total_quantity + cartons - 1) // cartons
                else:
                    # Large quantities: aim for ~50 items per carton
                    cartons = max(1, (total_quantity + 49) // 50)  # Round up division
                    items_per_carton = total_quantity // cartons
                    # Distribute remaining items
                    if total_quantity % cartons > 0:
                        items_per_carton = (total_quantity + cartons - 1) // cartons

                # Calculate CBM per carton
                cbm_per_carton = total_cbm / cartons if cartons > 0 else total_cbm

                # Estimate weight per carton based on CBM and typical density
                # General cargo: 300-500 kg per CBM, using 400 kg/CBM as average
                # For very small items, use minimum weight of 1kg per carton
                estimated_weight_per_carton = max(1.0, cbm_per_carton * 400.0)

                # Cap weight at reasonable limits (max 1000kg per carton for safety)
                kilogram_per_carton = min(1000.0, round(estimated_weight_per_carton, 2))

                packing_list_item = PackingListItem(
                    packing_list_id=packing_list.id,
                    item_name=item_data["item_name"],
                    item_picture=item_data["item_picture"],
                    price_per_piece=item_data["price_per_piece"],
                    # Smart defaults for logistics parameters
                    cartons=cartons,
                    items_per_carton=items_per_carton,
                    cbm_per_carton=round(cbm_per_carton, 4),
                    kilogram_per_carton=kilogram_per_carton,
                    # Auto-calculated fields
                    total_quantity=total_quantity,
                    total_amount=item_data["total_amount"],
                    total_cbm=total_cbm,
                    total_kilogram=round(kilogram_per_carton * cartons, 2),
                )

                db.add(packing_list_item)
                packing_list_items.append(packing_list_item)

            db.flush()

            # Generate QR code
            qr_code_url = PackingListService._generate_qr_code(db, packing_list.id)
            if qr_code_url:
                packing_list.qr_code_url = qr_code_url

            db.commit()
            db.refresh(packing_list)

            # Prepare data for document generation
            batch_data = {
                "issuer": sourcing_agent_document_branding(db, batch.agent),
                "id": str(batch.id),
                "title": batch.title,
                "agent_name": batch.agent.name if batch.agent else "Unknown Agent",
                "status": batch.status,
                "created_at": (
                    batch.created_at.isoformat() if batch.created_at else None
                ),
            }

            items_data = []
            for item in packing_list_items:
                items_data.append(
                    {
                        "item_name": item.item_name,
                        "item_code": item.item_code,
                        "item_picture": item.item_picture,
                        "price_per_piece": float(item.price_per_piece),
                        "cartons": item.cartons,
                        "items_per_carton": item.items_per_carton,
                        "total_quantity": item.total_quantity,
                        "total_amount": float(item.total_amount),
                        "cbm_per_carton": float(item.cbm_per_carton),
                        "total_cbm": float(item.total_cbm),
                        "kilogram_per_carton": float(item.kilogram_per_carton),
                        "total_kilogram": float(item.total_kilogram),
                    }
                )

            # Generate documents
            excel_bytes = DocumentGenerationService.generate_packing_list_excel(
                batch_data, items_data
            )
            pdf_bytes = DocumentGenerationService.generate_packing_list_pdf(
                batch_data, items_data
            )

            # Upload documents to Cloudinary
            excel_url = DocumentGenerationService.upload_document_to_cloudinary(
                excel_bytes, "excel", str(batch.id), "xlsx"
            )
            pdf_url = DocumentGenerationService.upload_document_to_cloudinary(
                pdf_bytes, "pdf", str(batch.id), "pdf"
            )

            return {
                "success": True,
                "packing_list_id": str(packing_list.id),
                "packing_list_name": packing_list.name,
                "excel_url": excel_url,
                "pdf_url": pdf_url,
                "items_count": len(packing_list_items),
                "orders_count": len(orders),
            }

        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error generating packing list: {str(e)}")
        except Exception as e:
            db.rollback()
            raise Exception(f"Error generating packing list: {str(e)}")
