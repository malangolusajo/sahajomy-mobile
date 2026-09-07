#!/usr/bin/env python3
"""
Document Generation Service for Packing Lists
Handles generation of packing lists in Excel and PDF formats from batch orders.
"""

import os
import re
import tempfile
from datetime import datetime
from html import escape
from io import BytesIO
from typing import Any, Dict, List, Optional

from app.core.cloudinary import upload_to_cloudinary
from app.core.safe_remote import MAX_REMOTE_IMAGE_BYTES, fetch_public_bytes
from fastapi import HTTPException
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image as ReportLabImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _financial_amount_format(currency: str | None) -> str:
    """Match the platform convention: whole TZS, two decimals otherwise."""
    return "#,##0" if str(currency or "").upper() == "TZS" else "#,##0.00"


def _format_financial_amount(amount: float, currency: str | None) -> str:
    return format(amount, ",.0f" if str(currency or "").upper() == "TZS" else ",.2f")


def _issuer(data: Dict[str, Any]) -> Dict[str, Any]:
    return data.get("issuer") or data.get("company") or {}


def _issuer_name(data: Dict[str, Any]) -> str:
    issuer = _issuer(data)
    return str(issuer.get("name") or data.get("agent_name") or "Document issuer")


def _issuer_contact_lines(data: Dict[str, Any]) -> list[str]:
    issuer = _issuer(data)
    location = ", ".join(
        str(value) for value in (issuer.get("city"), issuer.get("country")) if value
    )
    return [
        str(value)
        for value in (
            issuer.get("registration_number"),
            issuer.get("address"),
            location,
            issuer.get("phone"),
            issuer.get("email"),
            issuer.get("website"),
        )
        if value
    ]


class DocumentGenerationService:
    """Service for generating packing list documents in various formats."""

    @staticmethod
    def _fetch_image_bytes(image_url: str, timeout: float = 8.0) -> Optional[bytes]:
        if not image_url:
            return None
        try:
            image_bytes, _ = fetch_public_bytes(
                str(image_url),
                max_bytes=MAX_REMOTE_IMAGE_BYTES,
                allowed_content_prefixes=("image/",),
                timeout_seconds=timeout,
                user_agent="Sahajomy-Document-Exporter/1.0",
            )
            return image_bytes
        except Exception:
            return None

    @staticmethod
    def generate_packing_list_excel(
        batch_data: Dict[str, Any], items_data: List[Dict[str, Any]]
    ) -> bytes:
        """
        Generate packing list as Excel file.

        Args:
            batch_data: Dictionary containing batch information
            items_data: List of dictionaries containing item information

        Returns:
            Bytes of the Excel file
        """
        # Create workbook and worksheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Packing List"

        # Set column widths
        column_widths = [5, 25, 15, 15, 10, 10, 15, 15, 15, 15, 15]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[chr(64 + i)].width = width

        # Header styling
        header_font = Font(bold=True, size=12)
        header_fill = PatternFill(
            start_color="D3D3D3", end_color="D3D3D3", fill_type="solid"
        )
        header_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        header_alignment = Alignment(horizontal="center", vertical="center")

        issuer_name = _issuer_name(batch_data)
        # Add title
        title_cell = ws.cell(
            row=1,
            column=1,
            value=f"{issuer_name} - PACKING LIST",
        )
        title_cell.font = Font(bold=True, size=16)
        title_cell.alignment = Alignment(horizontal="center")
        ws.merge_cells(
            start_row=1, start_column=1, end_row=1, end_column=len(column_widths)
        )

        # Add batch info
        ws.cell(row=2, column=1, value="Batch:")
        ws.cell(row=2, column=2, value=batch_data.get("title", "Unknown Batch"))
        ws.cell(row=2, column=4, value="Created:")
        ws.cell(
            row=2,
            column=5,
            value=(
                batch_data.get("created_at", "").split("T")[0]
                if batch_data.get("created_at")
                else ""
            ),
        )

        ws.cell(row=3, column=1, value="Issued by:")
        ws.cell(row=3, column=2, value=issuer_name)
        ws.cell(row=3, column=4, value="Status:")
        ws.cell(row=3, column=5, value=batch_data.get("status", "").upper())

        ws.cell(row=4, column=1, value="Business details:")
        ws.cell(
            row=4,
            column=2,
            value=" | ".join(_issuer_contact_lines(batch_data)),
        )
        ws.merge_cells(
            start_row=4, start_column=2, end_row=4, end_column=len(column_widths)
        )

        # Headers
        headers = [
            "No.",
            "Item Name",
            "Item Code",
            "Picture",
            "Price/Unit",
            "Cartons",
            "Items/Carton",
            "Total Qty",
            "Total Amount",
            "CBM/Carton",
            "Total CBM",
        ]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=5, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = header_border
            cell.alignment = header_alignment

        # Data rows
        data_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        data_alignment = Alignment(vertical="center")

        for row_idx, item in enumerate(items_data, 6):
            ws.cell(row=row_idx, column=1, value=row_idx - 5).alignment = data_alignment
            ws.cell(
                row=row_idx, column=2, value=item.get("item_name", "")
            ).alignment = data_alignment
            ws.cell(
                row=row_idx, column=3, value=item.get("item_code", "")
            ).alignment = data_alignment
            ws.cell(
                row=row_idx, column=4, value=item.get("item_picture", "")
            ).alignment = data_alignment
            ws.cell(
                row=row_idx, column=5, value=item.get("price_per_piece", 0)
            ).alignment = data_alignment
            ws.cell(row=row_idx, column=6, value=item.get("cartons", 0)).alignment = (
                data_alignment
            )
            ws.cell(
                row=row_idx, column=7, value=item.get("items_per_carton", 0)
            ).alignment = data_alignment
            ws.cell(
                row=row_idx, column=8, value=item.get("total_quantity", 0)
            ).alignment = data_alignment
            ws.cell(
                row=row_idx, column=9, value=item.get("total_amount", 0)
            ).alignment = data_alignment
            ws.cell(
                row=row_idx, column=10, value=item.get("cbm_per_carton", 0)
            ).alignment = data_alignment
            ws.cell(
                row=row_idx, column=11, value=item.get("total_cbm", 0)
            ).alignment = data_alignment

            # Apply borders to all data cells
            for col in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=col).border = data_border

        # Auto-adjust row heights
        for row in ws.iter_rows(min_row=5, max_row=ws.max_row):
            ws.row_dimensions[row[0].row].height = 20

        # Save to bytes
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        return excel_buffer.getvalue()

    @staticmethod
    def generate_packing_list_pdf(
        batch_data: Dict[str, Any], items_data: List[Dict[str, Any]]
    ) -> bytes:
        """
        Generate packing list as PDF file.

        Args:
            batch_data: Dictionary containing batch information
            items_data: List of dictionaries containing item information

        Returns:
            Bytes of the PDF file
        """
        # Create PDF buffer
        pdf_buffer = BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30,
        )

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=12,
            alignment=1,  # Center
        )
        normal_style = styles["Normal"]

        # Content
        story = []

        # Title
        story.append(Paragraph(escape(_issuer_name(batch_data)), styles["Heading3"]))
        issuer_details = " | ".join(_issuer_contact_lines(batch_data))
        if issuer_details:
            story.append(Paragraph(escape(issuer_details), normal_style))
        story.append(Paragraph("PACKING LIST", title_style))
        story.append(
            Paragraph(
                f"Batch: {batch_data.get('title', 'Unknown Batch')}", styles["Normal"]
            )
        )
        story.append(Spacer(1, 12))

        # Batch info
        created_date = (
            batch_data.get("created_at", "").split("T")[0]
            if batch_data.get("created_at")
            else ""
        )
        batch_info = f"""
        <b>Batch ID:</b> {batch_data.get('id', '')}<br/>
        <b>Issued by:</b> {escape(_issuer_name(batch_data))}<br/>
        <b>Status:</b> {batch_data.get('status', '').upper()}<br/>
        <b>Created:</b> {created_date}
        """
        story.append(Paragraph(batch_info, normal_style))
        story.append(Spacer(1, 12))

        # Items table
        if items_data:
            # Table headers
            table_data = [
                [
                    "No.",
                    "Item Name",
                    "Code",
                    "Price/Unit",
                    "Cartons",
                    "Items/Ctn",
                    "Total Qty",
                    "Total Amt",
                    "CBM/Ctn",
                    "Total CBM",
                ]
            ]

            # Table data
            for idx, item in enumerate(items_data, 1):
                row = [
                    str(idx),
                    str(item.get("item_name", "")),
                    str(item.get("item_code", "")),
                    f"{item.get('price_per_piece', 0):.2f}",
                    str(item.get("cartons", 0)),
                    str(item.get("items_per_carton", 0)),
                    str(item.get("total_quantity", 0)),
                    f"{item.get('total_amount', 0):.2f}",
                    f"{item.get('cbm_per_carton', 0):.4f}",
                    f"{item.get('total_cbm', 0):.4f}",
                ]
                table_data.append(row)

            # Create table
            table = Table(table_data, repeatRows=1)

            # Table style
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                        ("WORDWRAP", (1, 1), (1, -1), True),  # Wrap item names
                    ]
                )
            )

            story.append(table)

        # Build PDF
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()

    @staticmethod
    def generate_packing_list_excel_detailed(
        metadata: Dict[str, Any], items_data: List[Dict[str, Any]]
    ) -> bytes:
        wb = Workbook()
        ws = wb.active
        ws.title = "Packing List"

        column_widths = [8, 16, 26, 16, 18, 12, 12, 10, 12, 12, 14, 12, 12, 26, 22]
        for idx, width in enumerate(column_widths, 1):
            ws.column_dimensions[chr(64 + idx)].width = width

        ws.merge_cells(
            start_row=1, start_column=1, end_row=1, end_column=len(column_widths)
        )
        title = ws.cell(
            row=1, column=1, value=f"{_issuer_name(metadata)} - Packing List"
        )
        title.font = Font(bold=True, size=16)
        title.alignment = Alignment(horizontal="center")

        ws.cell(row=2, column=1, value="Reference:")
        ws.cell(row=2, column=2, value=metadata.get("reference", ""))
        ws.cell(row=2, column=6, value="Generated:")
        ws.cell(row=2, column=7, value=metadata.get("generated_at", ""))

        ws.cell(row=3, column=1, value="Batch:")
        ws.cell(row=3, column=2, value=metadata.get("batch_title", ""))
        ws.cell(row=3, column=6, value="Status:")
        ws.cell(row=3, column=7, value=str(metadata.get("status", "")).upper())

        ws.cell(row=4, column=1, value="Agent:")
        ws.cell(row=4, column=2, value=metadata.get("agent_name", ""))
        ws.cell(row=4, column=6, value="Phone/WhatsApp:")
        ws.cell(row=4, column=7, value=metadata.get("agent_phone_or_whatsapp", ""))

        ws.cell(row=5, column=1, value="Instagram:")
        ws.cell(row=5, column=2, value=metadata.get("instagram", ""))
        ws.cell(row=5, column=6, value="TikTok:")
        ws.cell(row=5, column=7, value=metadata.get("tiktok", ""))

        headers = [
            "No.",
            "Reference",
            "Item Name",
            "Item Code/SKU",
            "Order References",
            "Quantity",
            "Cartons",
            "PCS/CTN",
            "Total CBM",
            "Weight (kg)",
            "Unit Price",
            "Total Amount",
            "Image",
            "Notes",
            "Image URL",
        ]
        header_row = 7
        header_font = Font(bold=True, size=10)
        header_fill = PatternFill(
            start_color="1F2937", end_color="1F2937", fill_type="solid"
        )
        header_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = header_border
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.font = Font(bold=True, color="FFFFFF")

        data_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        totals = {"quantity": 0, "cartons": 0, "cbm": 0.0, "weight": 0.0, "amount": 0.0}
        currency = metadata.get("currency", "TZS")
        image_cache: Dict[str, Optional[bytes]] = {}
        start_row = header_row + 1
        for row_idx, item in enumerate(items_data, start_row):
            quantity = float(item.get("total_quantity") or 0)
            cartons = float(item.get("cartons") or 0)
            total_cbm = float(item.get("total_cbm") or 0)
            total_weight = float(item.get("total_kilogram") or 0)
            total_amount = float(item.get("total_amount") or 0)

            totals["quantity"] += quantity
            totals["cartons"] += cartons
            totals["cbm"] += total_cbm
            totals["weight"] += total_weight
            totals["amount"] += total_amount

            image_url = str(item.get("item_picture") or "").strip()
            values = [
                row_idx - start_row + 1,
                metadata.get("reference", ""),
                item.get("item_name", ""),
                item.get("item_code", ""),
                ", ".join(item.get("order_references", [])),
                int(quantity) if quantity.is_integer() else quantity,
                int(cartons) if cartons.is_integer() else cartons,
                item.get("items_per_carton", ""),
                round(total_cbm, 4),
                round(total_weight, 2),
                f"{currency} {float(item.get('price_per_piece') or 0):,.2f}",
                f"{currency} {total_amount:,.2f}",
                "No image" if not image_url else "",
                item.get("notes", ""),
                image_url,
            ]
            for col, value in enumerate(values, 1):
                cell = ws.cell(row=row_idx, column=col, value=value)
                cell.border = data_border
                cell.alignment = Alignment(vertical="top", wrap_text=True)

            if image_url:
                if image_url not in image_cache:
                    image_cache[image_url] = (
                        DocumentGenerationService._fetch_image_bytes(image_url)
                    )
                image_bytes = image_cache[image_url]
                if image_bytes:
                    try:
                        image_stream = BytesIO(image_bytes)
                        excel_image = XLImage(image_stream)
                        excel_image.width = 52
                        excel_image.height = 52
                        ws.add_image(excel_image, f"M{row_idx}")
                        ws.row_dimensions[row_idx].height = 42
                    except Exception:
                        ws.cell(row=row_idx, column=13, value="Image unavailable")

        summary_row = start_row + len(items_data)
        ws.merge_cells(
            start_row=summary_row, start_column=1, end_row=summary_row, end_column=5
        )
        total_label = ws.cell(row=summary_row, column=1, value="TOTALS")
        total_label.font = Font(bold=True)
        total_label.fill = PatternFill(
            start_color="E5E7EB", end_color="E5E7EB", fill_type="solid"
        )
        total_label.alignment = Alignment(horizontal="right")
        total_label.border = data_border

        ws.cell(
            row=summary_row, column=6, value=round(totals["quantity"], 2)
        ).border = data_border
        ws.cell(row=summary_row, column=7, value=round(totals["cartons"], 2)).border = (
            data_border
        )
        ws.cell(row=summary_row, column=9, value=round(totals["cbm"], 4)).border = (
            data_border
        )
        ws.cell(row=summary_row, column=10, value=round(totals["weight"], 2)).border = (
            data_border
        )
        amount_cell = ws.cell(
            row=summary_row, column=12, value=f"{currency} {totals['amount']:,.2f}"
        )
        amount_cell.border = data_border
        amount_cell.font = Font(bold=True)
        ws.cell(row=summary_row, column=13).border = data_border
        ws.cell(row=summary_row, column=14).border = data_border
        ws.cell(row=summary_row, column=15).border = data_border

        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        return excel_buffer.getvalue()

    @staticmethod
    def generate_packing_list_pdf_detailed(
        metadata: Dict[str, Any], items_data: List[Dict[str, Any]]
    ) -> bytes:
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=landscape(A4),
            rightMargin=24,
            leftMargin=24,
            topMargin=24,
            bottomMargin=24,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "PackingListTitle",
            parent=styles["Heading1"],
            fontSize=20,
            alignment=1,
            spaceAfter=8,
        )
        meta_style = ParagraphStyle(
            "PackingListMeta",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
        )

        story = []
        story.append(Paragraph(escape(_issuer_name(metadata)), styles["Heading3"]))
        issuer_details = " | ".join(_issuer_contact_lines(metadata))
        if issuer_details:
            story.append(Paragraph(escape(issuer_details), meta_style))
        story.append(Paragraph("Packing List", title_style))
        story.append(
            Paragraph(
                (
                    f"<b>Reference:</b> {metadata.get('reference', '')} &nbsp;&nbsp; "
                    f"<b>Date:</b> {metadata.get('generated_at', '')} &nbsp;&nbsp; "
                    f"<b>Status:</b> {str(metadata.get('status', '')).upper()}"
                ),
                meta_style,
            )
        )
        story.append(
            Paragraph(
                (
                    f"<b>Batch:</b> {metadata.get('batch_title', '')}<br/>"
                    f"<b>Issued by:</b> {escape(_issuer_name(metadata))}<br/>"
                    f"<b>Phone/WhatsApp:</b> "
                    f"{metadata.get('agent_phone_or_whatsapp', '')}<br/>"
                    f"<b>Instagram:</b> {metadata.get('instagram', '')} &nbsp;&nbsp; "
                    f"<b>TikTok:</b> {metadata.get('tiktok', '')}"
                ),
                meta_style,
            )
        )
        story.append(Spacer(1, 8))

        headers = [
            "No.",
            "Image",
            "Item",
            "Code",
            "Qty",
            "Cartons",
            "PCS/CTN",
            "CBM",
            "Weight",
            "Unit Price",
            "Total",
        ]
        table_data = [headers]

        currency = metadata.get("currency", "TZS")
        total_qty = 0.0
        total_cartons = 0.0
        total_cbm = 0.0
        total_weight = 0.0
        total_amount = 0.0
        image_cache: Dict[str, Optional[bytes]] = {}

        for idx, item in enumerate(items_data, 1):
            qty = float(item.get("total_quantity") or 0)
            cartons = float(item.get("cartons") or 0)
            cbm = float(item.get("total_cbm") or 0)
            weight = float(item.get("total_kilogram") or 0)
            amount = float(item.get("total_amount") or 0)
            total_qty += qty
            total_cartons += cartons
            total_cbm += cbm
            total_weight += weight
            total_amount += amount
            image_url = str(item.get("item_picture") or "").strip()
            pdf_image: Any = "No image"
            if image_url:
                if image_url not in image_cache:
                    image_cache[image_url] = (
                        DocumentGenerationService._fetch_image_bytes(image_url)
                    )
                image_bytes = image_cache[image_url]
                if image_bytes:
                    try:
                        pdf_image = ReportLabImage(
                            BytesIO(image_bytes),
                            width=34,
                            height=34,
                            kind="proportional",
                        )
                    except Exception:
                        pdf_image = "Image unavailable"
                else:
                    pdf_image = "Image unavailable"

            table_data.append(
                [
                    str(idx),
                    pdf_image,
                    str(item.get("item_name", "")),
                    str(item.get("item_code", "")),
                    f"{qty:.0f}" if qty.is_integer() else f"{qty:.2f}",
                    f"{cartons:.0f}" if cartons.is_integer() else f"{cartons:.2f}",
                    str(item.get("items_per_carton", "")),
                    f"{cbm:.4f}",
                    f"{weight:.2f}",
                    f"{currency} {float(item.get('price_per_piece') or 0):,.2f}",
                    f"{currency} {amount:,.2f}",
                ]
            )

        table_data.append(
            [
                "",
                "",
                "TOTALS",
                "",
                f"{total_qty:.2f}",
                f"{total_cartons:.2f}",
                "",
                f"{total_cbm:.4f}",
                f"{total_weight:.2f}",
                "",
                f"{currency} {total_amount:,.2f}",
            ]
        )

        table = Table(
            table_data,
            repeatRows=1,
            colWidths=[28, 46, 140, 72, 52, 52, 54, 58, 58, 86, 94],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("ALIGN", (2, 1), (3, -2), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -2),
                        [colors.whitesmoke, colors.lightgrey],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E5E7EB")),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 10))
        story.append(
            Paragraph(
                (
                    f"Generated on {metadata.get('generated_at', '')} "
                    f"for {escape(_issuer_name(metadata))}."
                ),
                styles["Italic"],
            )
        )

        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()

    @staticmethod
    def generate_consolidated_container_packing_list_pdf(
        payload: Dict[str, Any]
    ) -> bytes:
        """Generate a printable container packing list from sea_booking data."""
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=landscape(A4),
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ConsolidatedPackingListTitle",
            parent=styles["Heading1"],
            fontSize=18,
            alignment=1,
            spaceAfter=8,
        )
        meta_style = ParagraphStyle(
            "ConsolidatedPackingListMeta",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
        )
        cell_style = ParagraphStyle(
            "ConsolidatedPackingListCell",
            parent=styles["Normal"],
            fontSize=7,
            leading=9,
        )

        container = payload.get("container") or {}
        summary = payload.get("summary") or {}
        story = [
            Paragraph(escape(_issuer_name(payload)), styles["Heading3"]),
            Paragraph(
                escape(" | ".join(_issuer_contact_lines(payload)))
                or "Business details not provided",
                meta_style,
            ),
            Paragraph("Consolidated Container Packing List", title_style),
            Paragraph(
                (
                    f"<b>Container:</b> {escape(str(container.get('reference') or container.get('id') or ''))} "
                    f"&nbsp;&nbsp; <b>Size:</b> {escape(str(container.get('container_size') or ''))} "
                    f"&nbsp;&nbsp; <b>Status:</b> {escape(str(container.get('status') or ''))}<br/>"
                    f"<b>Generated:</b> {escape(str(payload.get('generated_at') or ''))}<br/>"
                    f"<b>Sea bookings:</b> {int(summary.get('sea_booking_count') or 0)} "
                    f"&nbsp;&nbsp; <b>Customers:</b> {int(summary.get('customer_count') or 0)} "
                    f"&nbsp;&nbsp; <b>Cartons:</b> {int(summary.get('total_cartons') or 0)} "
                    f"&nbsp;&nbsp; <b>CBM:</b> {float(summary.get('total_cbm') or 0):.3f} "
                    f"&nbsp;&nbsp; <b>Known weight:</b> {float(summary.get('total_weight_kg') or 0):.2f} kg"
                ),
                meta_style,
            ),
            Spacer(1, 8),
        ]

        headers = [
            "Customer",
            "Sea Booking",
            "Tracking",
            "Shipping Mark",
            "Description",
            "Supplier / Notes",
            "Cartons",
            "CBM",
            "Weight (kg)",
            "Status",
        ]
        table_data = [headers]
        for item in payload.get("items") or []:

            def cell(value: Any) -> Paragraph:
                return Paragraph(
                    escape(str(value if value not in (None, "") else "-")), cell_style
                )

            weight = item.get("weight_kg")
            table_data.append(
                [
                    cell(item.get("customer_name")),
                    cell(
                        item.get("sea_booking_reference") or item.get("sea_booking_id")
                    ),
                    cell(item.get("tracking_number")),
                    cell(item.get("shipping_mark")),
                    cell(item.get("item_name")),
                    cell(item.get("supplier_details") or item.get("notes")),
                    cell(int(item.get("cartons") or 0)),
                    cell(f"{float(item.get('cbm') or 0):.3f}"),
                    cell(f"{float(weight):.2f}" if weight is not None else "-"),
                    cell(item.get("status")),
                ]
            )

        table_data.append(
            [
                "",
                "",
                "",
                "",
                "TOTALS",
                "",
                str(int(summary.get("total_cartons") or 0)),
                f"{float(summary.get('total_cbm') or 0):.3f}",
                f"{float(summary.get('total_weight_kg') or 0):.2f}",
                "",
            ]
        )
        table = Table(
            table_data,
            repeatRows=1,
            colWidths=[64, 70, 74, 72, 120, 94, 40, 42, 52, 48],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("ALIGN", (6, 1), (8, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -2),
                        [colors.whitesmoke, colors.HexColor("#F3F4F6")],
                    ),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E5E7EB")),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )
        story.append(table)
        if summary.get("missing_weight_item_count"):
            story.extend(
                [
                    Spacer(1, 6),
                    Paragraph(
                        (
                            f"Weight is not recorded for {int(summary['missing_weight_item_count'])} "
                            "baseline item(s); the total weight includes recorded values only."
                        ),
                        meta_style,
                    ),
                ]
            )

        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()

    @staticmethod
    def generate_financial_document_excel(
        document_title: str, metadata: Dict[str, Any], items_data: List[Dict[str, Any]]
    ) -> bytes:
        """Generate invoice/receipt as an Excel file."""
        wb = Workbook()
        ws = wb.active
        ws.title = document_title[:31]

        column_widths = [6, 40, 12, 14, 16, 12]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[chr(64 + i)].width = width

        title_cell = ws.cell(row=1, column=1, value=document_title.upper())
        title_cell.font = Font(bold=True, size=16)
        title_cell.alignment = Alignment(horizontal="center")
        ws.merge_cells(
            start_row=1, start_column=1, end_row=1, end_column=len(column_widths)
        )

        ws.cell(row=2, column=1, value="Document No:")
        ws.cell(row=2, column=2, value=metadata.get("document_number", ""))
        ws.cell(row=2, column=4, value="Date:")
        ws.cell(row=2, column=5, value=metadata.get("generated_at", ""))

        ws.cell(row=3, column=1, value="Order ID:")
        ws.cell(row=3, column=2, value=metadata.get("order_id", ""))
        ws.cell(row=3, column=4, value="Customer:")
        ws.cell(row=3, column=5, value=metadata.get("customer_name", ""))

        ws.cell(row=4, column=1, value="Currency:")
        ws.cell(row=4, column=2, value=metadata.get("currency", "TZS"))
        ws.cell(row=4, column=4, value="Status:")
        ws.cell(row=4, column=5, value=metadata.get("status", "").upper())

        ws.cell(row=5, column=1, value="Issued By:")
        issuer_summary = " | ".join(
            [_issuer_name(metadata), *_issuer_contact_lines(metadata)]
        )
        ws.cell(row=5, column=2, value=issuer_summary)
        ws.merge_cells(start_row=5, start_column=2, end_row=5, end_column=6)

        headers = [
            "No.",
            "Description",
            "Quantity",
            "Unit Price",
            "Line Total",
            "Currency",
        ]
        header_row = 6
        header_font = Font(bold=True, size=11)
        header_fill = PatternFill(
            start_color="D3D3D3", end_color="D3D3D3", fill_type="solid"
        )
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center")

        total_amount = 0.0
        for idx, item in enumerate(items_data, 1):
            row = header_row + idx
            line_total = float(item.get("total_price") or 0)
            total_amount += line_total

            ws.cell(row=row, column=1, value=idx).border = border
            ws.cell(row=row, column=2, value=item.get("description", "")).border = (
                border
            )
            ws.cell(row=row, column=3, value=item.get("quantity", 0)).border = border
            item_currency = item.get("currency", metadata.get("currency", "TZS"))
            unit_price_cell = ws.cell(
                row=row, column=4, value=float(item.get("unit_price") or 0)
            )
            unit_price_cell.border = border
            unit_price_cell.number_format = _financial_amount_format(item_currency)
            line_total_cell = ws.cell(row=row, column=5, value=line_total)
            line_total_cell.border = border
            line_total_cell.number_format = _financial_amount_format(item_currency)
            ws.cell(
                row=row,
                column=6,
                value=item_currency,
            ).border = border

        summary_row = header_row + len(items_data) + 2
        ws.cell(row=summary_row, column=4, value="Grand Total:").font = Font(bold=True)
        total_cell = ws.cell(row=summary_row, column=5, value=total_amount)
        total_cell.font = Font(bold=True)
        total_cell.number_format = _financial_amount_format(metadata.get("currency"))
        ws.cell(
            row=summary_row, column=6, value=metadata.get("currency", "TZS")
        ).font = Font(bold=True)

        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        return excel_buffer.getvalue()

    @staticmethod
    def generate_financial_document_pdf(
        document_title: str, metadata: Dict[str, Any], items_data: List[Dict[str, Any]]
    ) -> bytes:
        """Generate invoice/receipt as a PDF file."""
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "FinancialDocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=12,
            alignment=1,
        )

        story = [
            Paragraph(escape(_issuer_name(metadata)), styles["Heading2"]),
            Paragraph(document_title.upper(), title_style),
            Paragraph(
                "<br/>".join(escape(line) for line in _issuer_contact_lines(metadata))
                or "Business details not provided",
                styles["Normal"],
            ),
            Spacer(1, 8),
            Paragraph(
                (
                    f"<b>Document No:</b> {metadata.get('document_number', '')}<br/>"
                    f"<b>Order ID:</b> {metadata.get('order_id', '')}<br/>"
                    f"<b>Customer:</b> {metadata.get('customer_name', '')}<br/>"
                    f"<b>Currency:</b> {metadata.get('currency', 'TZS')}<br/>"
                    f"<b>Status:</b> {str(metadata.get('status', '')).upper()}<br/>"
                    f"<b>Generated:</b> {metadata.get('generated_at', '')}"
                ),
                styles["Normal"],
            ),
            Spacer(1, 12),
        ]

        table_data = [
            ["No.", "Description", "Qty", "Unit Price", "Line Total", "Currency"]
        ]
        total_amount = 0.0
        for idx, item in enumerate(items_data, 1):
            line_total = float(item.get("total_price") or 0)
            total_amount += line_total
            item_currency = item.get("currency", metadata.get("currency", "TZS"))
            table_data.append(
                [
                    str(idx),
                    str(item.get("description", "")),
                    str(item.get("quantity", 0)),
                    _format_financial_amount(
                        float(item.get("unit_price") or 0), item_currency
                    ),
                    _format_financial_amount(line_total, item_currency),
                    str(item_currency),
                ]
            )

        table_data.append(
            [
                "",
                "",
                "",
                "Grand Total",
                _format_financial_amount(total_amount, metadata.get("currency", "TZS")),
                str(metadata.get("currency", "TZS")),
            ]
        )

        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 1), (-1, -2), colors.beige),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )
        story.append(table)
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()

    @staticmethod
    def generate_customs_packing_list_pdf(document: Dict[str, Any]) -> bytes:
        """Generate a clean, multi-page customs PACKING LIST from its snapshot."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=24,
            leftMargin=24,
            topMargin=28,
            bottomMargin=30,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomsPackingTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=1,
            spaceAfter=8,
        )
        heading_style = ParagraphStyle(
            "CustomsPackingHeading",
            parent=styles["Heading4"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1d4ed8"),
            spaceAfter=2,
        )
        body_style = ParagraphStyle(
            "CustomsPackingBody",
            parent=styles["BodyText"],
            fontSize=7.2,
            leading=9,
        )
        cell_style = ParagraphStyle(
            "CustomsPackingCell",
            parent=styles["BodyText"],
            fontSize=6.5,
            leading=7.6,
        )

        def safe(value: Any) -> str:
            return escape(str(value or "")).replace("\n", "<br/>")

        def fmt(value: Any, places: int = 3) -> str:
            if value is None:
                return ""
            try:
                return f"{float(value):,.{places}f}"
            except (ValueError, TypeError):
                return str(value)

        def address_block(title: str, data: Dict[str, Any]) -> Paragraph:
            data = data or {}
            address = (
                data.get("address") if isinstance(data.get("address"), dict) else data
            )
            lines = [
                data.get("name"),
                data.get("contact_person"),
                data.get("phone"),
                data.get("email"),
                address.get("full_address"),
                address.get("city"),
                address.get("region"),
                address.get("country"),
            ]
            text = "<br/>".join(safe(line) for line in lines if line)
            return Paragraph(f"<b>{safe(title)}</b><br/>{text or '—'}", body_style)

        photo_size = 1.2 * 72  # ReportLab points: 1 inch = 72 points.

        def fallback_photo() -> Drawing:
            """A printable placeholder is still a real visual thumbnail in the PDF."""
            drawing = Drawing(photo_size, photo_size)
            drawing.add(
                Rect(
                    0,
                    0,
                    photo_size,
                    photo_size,
                    fillColor=colors.HexColor("#e2e8f0"),
                    strokeColor=colors.HexColor("#94a3b8"),
                )
            )
            drawing.add(
                String(
                    photo_size / 2,
                    photo_size / 2 + 5,
                    "ITEM",
                    textAnchor="middle",
                    fontName="Helvetica-Bold",
                    fontSize=8,
                    fillColor=colors.HexColor("#475569"),
                )
            )
            drawing.add(
                String(
                    photo_size / 2,
                    photo_size / 2 - 7,
                    "PHOTO",
                    textAnchor="middle",
                    fontName="Helvetica",
                    fontSize=7,
                    fillColor=colors.HexColor("#475569"),
                )
            )
            return drawing

        shipment_details = " | ".join(
            f"{str(key).replace('_', ' ').title()}: {value}"
            for key, value in (document.get("shipment_references") or {}).items()
            if value
        )

        shipper = document.get("shipper_snapshot") or {}
        story = [
            Paragraph(
                safe(shipper.get("name") or "Cargo Company"),
                ParagraphStyle(
                    "ShipperName",
                    parent=styles["Heading2"],
                    alignment=1,
                    fontSize=12,
                    leading=14,
                ),
            ),
            Paragraph("PACKING LIST", title_style),
            Paragraph(
                f"<b>Packing List No.:</b> {safe(document.get('packing_list_number'))} &nbsp;&nbsp;&nbsp; <b>Issue Date:</b> {safe(document.get('issue_date'))} &nbsp;&nbsp;&nbsp; <b>Cargo Type:</b> {safe(str(document.get('cargo_type') or '').upper())}",
                body_style,
            ),
            Spacer(1, 8),
        ]
        header = Table(
            [
                [
                    address_block("SHIPPER / EXPORTER", shipper),
                    address_block(
                        "CONSIGNEE", document.get("consignee_snapshot") or {}
                    ),
                    address_block("NOTIFY PARTY", document.get("notify_party") or {}),
                ],
                [
                    address_block(
                        "ORIGIN / SHIP FROM", document.get("origin_address") or {}
                    ),
                    Paragraph(
                        f"<b>SHIPMENT DETAILS</b><br/>{safe(shipment_details) or '—'}",
                        body_style,
                    ),
                    Paragraph(
                        f"<b>Remarks</b><br/>{safe(document.get('notes')) or '—'}",
                        body_style,
                    ),
                ],
            ],
            colWidths=[255, 255, 255],
        )
        header.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.extend(
            [header, Spacer(1, 10), Paragraph("PACKING DETAILS", heading_style)]
        )
        headers = [
            "#",
            "Item Photo",
            "Item Name / Description",
            "No. of Cartons",
            "Qty per Carton",
            "Total Quantity",
            "Dimensions (L × W × H cm)",
            "CBM per Carton",
            "Total CBM",
            "Gross Weight per Carton (kg)",
            "Total Gross Weight (kg)",
            "Remarks",
        ]
        rows = [headers]
        for index, item in enumerate(document.get("items") or [], start=1):
            dimensions = " × ".join(
                fmt(item.get(key), 2) for key in ("length_cm", "width_cm", "height_cm")
            )
            photo = fallback_photo()
            photo_url = item.get("item_photo_url")
            photo_bytes = (
                None
                if str(photo_url or "").startswith("fallback://")
                else DocumentGenerationService._fetch_image_bytes(photo_url)
            )
            if photo_bytes:
                try:
                    photo = ReportLabImage(
                        BytesIO(photo_bytes), width=photo_size, height=photo_size
                    )
                except Exception:
                    pass
            name_and_description = f"<b>{safe(item.get('item_name'))}</b><br/>{safe(item.get('item_description'))}"
            rows.append(
                [
                    str(index),
                    photo,
                    Paragraph(name_and_description, cell_style),
                    str(item.get("carton_count") or 0),
                    fmt(item.get("qty_per_carton")),
                    fmt(item.get("total_quantity")),
                    dimensions,
                    fmt(item.get("cbm_per_carton"), 6),
                    fmt(item.get("total_cbm"), 6),
                    fmt(item.get("gross_weight_per_carton_kg")),
                    fmt(item.get("total_gross_weight_kg")),
                    Paragraph(safe(item.get("remarks")), cell_style),
                ]
            )
        item_table = Table(
            rows,
            repeatRows=1,
            colWidths=[16, 92, 90, 36, 42, 44, 72, 48, 44, 58, 58, 49],
        )
        item_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f8fafc")],
                    ),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.extend([item_table, Spacer(1, 10)])
        total_rows = [
            [
                "Total Item Lines",
                len(document.get("items") or []),
                "Total Cartons",
                document.get("total_cartons", 0),
                "Total Quantity",
                fmt(document.get("total_quantity")),
                "Total CBM",
                f"{fmt(document.get('total_cbm'), 6)} CBM",
                "Total Gross Weight",
                f"{fmt(document.get('total_gross_weight_kg'))} kg",
            ]
        ]
        if document.get("cargo_type") == "air":
            total_rows.append(
                [
                    "Air Volumetric Weight",
                    f"{fmt(document.get('total_volumetric_weight_kg'))} kg",
                    "Chargeable Weight",
                    f"{fmt(document.get('chargeable_weight_kg'))} kg",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
        totals = Table(total_rows, colWidths=[75, 60, 65, 55, 70, 70, 55, 85, 78, 80])
        totals.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#93c5fd")),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(totals)
        footer_values = [
            f"{label.title()}: {shipper.get(key)}"
            for key, label in {
                "website": "Website",
                "whatsapp": "WhatsApp",
                "email": "Email",
                "instagram_url": "Instagram",
                "facebook_url": "Facebook",
                "wechat": "WeChat",
            }.items()
            if shipper.get(key)
        ]
        if footer_values:
            story.extend(
                [
                    Spacer(1, 9),
                    Paragraph(
                        safe(" | ".join(footer_values)),
                        ParagraphStyle(
                            "Footer",
                            parent=body_style,
                            alignment=1,
                            textColor=colors.HexColor("#475569"),
                        ),
                    ),
                ]
            )
        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def upload_document_to_cloudinary(
        document_bytes: bytes,
        document_type: str,
        batch_id: str,
        file_extension: str,
        *,
        db=None,
        operator_id=None,
    ) -> Optional[str]:
        """
        Upload generated document to Cloudinary.

        Args:
            document_bytes: Bytes of the document
            document_type: Type of document ('excel' or 'pdf')
            batch_id: ID of the batch
            file_extension: File extension ('xlsx' or 'pdf')

        Returns:
            URL to uploaded document, or None if failed
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                suffix=f".{file_extension}", delete=False
            ) as temp_file:
                temp_file.write(document_bytes)
                temp_file.flush()

                # Upload to Cloudinary
                folder = f"documents/{document_type}"
                safe_document_token = re.sub(
                    r"[^a-zA-Z0-9_-]+", "_", document_type or "document"
                ).strip("_")
                if not safe_document_token:
                    safe_document_token = "document"
                public_id = (
                    f"{safe_document_token}_{batch_id}_"
                    f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                )

                company = None
                if db is not None and operator_id is not None:
                    from app.services.subscriptions import company_for_operator

                    company = company_for_operator(db, operator_id)

                document_url = upload_to_cloudinary(
                    file=temp_file.name,
                    folder=folder,
                    public_id=public_id,
                    resource_type="raw",
                    db_session=db if company else None,
                    company_id=company.id if company else None,
                    uploaded_by_id=operator_id,
                    asset_kind=document_type,
                )

                return document_url

        except HTTPException:
            raise
        except Exception as e:
            print(
                (
                    f"Warning: Failed to upload {document_type} "
                    f"document to Cloudinary: {str(e)}"
                )
            )
            return None
        finally:
            if "temp_file" in locals() and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
