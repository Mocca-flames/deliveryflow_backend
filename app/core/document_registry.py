"""
Document Registry — Classification and branding configuration for all document types.
"""
from dataclasses import dataclass
from enum import Enum


class DocumentCategory(str, Enum):
    """Document categories based on exchange partner."""
    CLIENT = "client"  # Documents exchanged with clients (Shippers)
    CARRIER = "carrier"  # Documents exchanged with transporters (Carriers)
    OPERATIONAL = "operational"  # Operational & legal documents (Both parties)


@dataclass
class DocumentType:
    """Document type definition with branding configuration."""
    key: str
    label: str
    description: str
    category: DocumentCategory
    template_name: str
    pdf_method: str
    requires_branding: bool = True  # Whether tenant branding is applied
    requires_carrier_branding: bool = False  # Whether carrier branding is used
    footer_key: str | None = None  # Key for custom footer in tenant.settings.branding


# ═══════════════════════════════════════════════════════════════════════════════
# Document Registry
# ═══════════════════════════════════════════════════════════════════════════════

DOCUMENT_TYPES: dict[str, DocumentType] = {
    # ─────────────────────────────────────────────────────────────────────────
    # CLIENT DOCUMENTS (Shippers)
    # ─────────────────────────────────────────────────────────────────────────
    "quotation": DocumentType(
        key="quotation",
        label="Quotation (Rate Sheet)",
        description="Estimated costs, fuel surcharges, and transit times for requested route",
        category=DocumentCategory.CLIENT,
        template_name="quotation.html",
        pdf_method="generate_quotation",
        footer_key="quotation_footer",
    ),
    "proforma_invoice": DocumentType(
        key="proforma_invoice",
        label="Proforma Invoice",
        description="Pre-pickup confirmation for client approval of rates and terms",
        category=DocumentCategory.CLIENT,
        template_name="proforma_invoice.html",
        pdf_method="generate_proforma_invoice",
        footer_key="proforma_footer",
    ),
    "booking_confirmation": DocumentType(
        key="booking_confirmation",
        label="Booking Confirmation",
        description="Shipment acceptance with pickup window and carrier details",
        category=DocumentCategory.CLIENT,
        template_name="booking_confirmation.html",
        pdf_method="generate_booking_confirmation",
        footer_key="booking_footer",
    ),
    "invoice": DocumentType(
        key="invoice",
        label="Commercial Invoice",
        description="Official payment request after cargo pickup or delivery",
        category=DocumentCategory.CLIENT,
        template_name="invoice.html",
        pdf_method="generate_invoice",
        footer_key="invoice_footer",
    ),
    "credit_note": DocumentType(
        key="credit_note",
        label="Credit Note",
        description="Refund or adjustment for mid-transit issues",
        category=DocumentCategory.CLIENT,
        template_name="credit_debit_note.html",
        pdf_method="generate_credit_note",
        footer_key="credit_debit_footer",
    ),
    "debit_note": DocumentType(
        key="debit_note",
        label="Debit Note",
        description="Additional charges such as demurrage fees",
        category=DocumentCategory.CLIENT,
        template_name="credit_debit_note.html",
        pdf_method="generate_debit_note",
        footer_key="credit_debit_footer",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # CARRIER DOCUMENTS (Transporters)
    # ─────────────────────────────────────────────────────────────────────────
    "load_confirmation": DocumentType(
        key="load_confirmation",
        label="Load Confirmation (Rate Confirmation)",
        description="Legally binding contract with transporter locking rates and instructions",
        category=DocumentCategory.CARRIER,
        template_name="load_confirmation.html",
        pdf_method="generate_load_confirmation",
        footer_key="load_confirmation_footer",
    ),
    "carrier_invoice": DocumentType(
        key="carrier_invoice",
        label="Carrier Invoice",
        description="Bill from transporter for their services",
        category=DocumentCategory.CARRIER,
        template_name="carrier_invoice.html",
        pdf_method="generate_carrier_invoice",
        requires_branding=False,  # Uses carrier branding
        requires_carrier_branding=True,
        footer_key="carrier_invoice_footer",
    ),
    "contract": DocumentType(
        key="contract",
        label="Transport Contract",
        description="Formal agreement between broker and carrier",
        category=DocumentCategory.CARRIER,
        template_name="contract.html",
        pdf_method="generate_contract",
        footer_key="contract_footer",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # OPERATIONAL & LEGAL DOCUMENTS (Both Parties)
    # ─────────────────────────────────────────────────────────────────────────
    "waybill": DocumentType(
        key="waybill",
        label="Waybill / Bill of Lading (BOL)",
        description="Receipt of goods, contract of carriage, and document of title",
        category=DocumentCategory.OPERATIONAL,
        template_name="waybill.html",
        pdf_method="generate_waybill",
        footer_key="footer_text",
    ),
    "proof_of_delivery": DocumentType(
        key="proof_of_delivery",
        label="Proof of Delivery (POD)",
        description="Signed confirmation of safe delivery without damages",
        category=DocumentCategory.OPERATIONAL,
        template_name="proof_of_delivery.html",
        pdf_method="generate_proof_of_delivery",
        footer_key="pod_footer",
    ),
    "packing_list": DocumentType(
        key="packing_list",
        label="Packing List",
        description="Detailed breakdown of weight, dimensions, and contents",
        category=DocumentCategory.OPERATIONAL,
        template_name="packing_list.html",
        pdf_method="generate_packing_list",
        footer_key="packing_list_footer",
    ),
    "goods_received_note": DocumentType(
        key="goods_received_note",
        label="Goods Received Note (GRN)",
        description="Receiver's confirmation of inventory into warehouse",
        category=DocumentCategory.OPERATIONAL,
        template_name="goods_received_note.html",
        pdf_method="generate_goods_received_note",
        footer_key="grn_footer",
    ),
}


def get_document_type(doc_type_key: str) -> DocumentType | None:
    """Get document type by key."""
    return DOCUMENT_TYPES.get(doc_type_key)


def get_documents_by_category(category: DocumentCategory) -> list[DocumentType]:
    """Get all document types for a category."""
    return [dt for dt in DOCUMENT_TYPES.values() if dt.category == category]


def get_client_documents() -> list[DocumentType]:
    """Get all client-facing documents."""
    return get_documents_by_category(DocumentCategory.CLIENT)


def get_carrier_documents() -> list[DocumentType]:
    """Get all carrier-facing documents."""
    return get_documents_by_category(DocumentCategory.CARRIER)


def get_operational_documents() -> list[DocumentType]:
    """Get all operational documents."""
    return get_documents_by_category(DocumentCategory.OPERATIONAL)


def get_all_document_types() -> list[DocumentType]:
    """Get all document types."""
    return list(DOCUMENT_TYPES.values())
