import asyncio
import base64
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class PDFGenerator:
    """Generate PDF documents from Jinja2 HTML templates using WeasyPrint."""

    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True,
        )
        self.env.filters["currency"] = self._format_currency
        self.env.filters["address_block"] = self._format_address_block
        self.env.filters["base64_logo"] = self._get_base64_logo

    @staticmethod
    def _format_currency(value: float, currency: str = "ZAR") -> str:
        return f"{currency} {value:,.2f}"

    @staticmethod
    def _format_address_block(addr: dict) -> str:
        lines = [
            addr.get("name", ""),
            addr.get("line1", ""),
            addr.get("line2", ""),
            f"{addr.get('city', '')} {addr.get('postal_code', '')}".strip(),
            addr.get("country", ""),
        ]
        return "<br>".join(line for line in lines if line)

    @staticmethod
    def _get_base64_logo(logo_storage_key: str | None) -> str:
        """Convert logo storage key to base64 data URI for HTML embedding."""
        if not logo_storage_key:
            return ""
        
        try:
            from app.storage.seaweed import SeaweedStorage
            storage = SeaweedStorage()
            logo_bytes = asyncio.get_event_loop().run_until_complete(
                storage.get(logo_storage_key)
            )
            # Determine MIME type from key
            if logo_storage_key.endswith(".png"):
                mime_type = "image/png"
            elif logo_storage_key.endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"
            elif logo_storage_key.endswith(".svg"):
                mime_type = "image/svg+xml"
            else:
                mime_type = "image/png"
            
            base64_data = base64.b64encode(logo_bytes).decode("utf-8")
            return f"data:{mime_type};base64,{base64_data}"
        except Exception:
            return ""

    async def _render(self, template_name: str, data: dict) -> bytes:
        template = self.env.get_template(template_name)
        html_string = template.render(**data)
        return await asyncio.to_thread(
            lambda: HTML(string=html_string, base_url=str(TEMPLATE_DIR)).write_pdf()
        )

    # ═══════════════════════════════════════════════════════════════════
    # Client Documents (Shippers)
    # ═══════════════════════════════════════════════════════════════════

    async def generate_invoice(self, data: dict) -> bytes:
        """Commercial Invoice - Official payment request after delivery."""
        return await self._render("invoice.html", data)

    async def generate_quotation(self, data: dict) -> bytes:
        """Quotation (Rate Sheet) - Estimated costs for requested route."""
        return await self._render("quotation.html", data)

    async def generate_proforma_invoice(self, data: dict) -> bytes:
        """Proforma Invoice - Pre-pickup confirmation for client approval."""
        return await self._render("proforma_invoice.html", data)

    async def generate_booking_confirmation(self, data: dict) -> bytes:
        """Booking Confirmation - Shipment acceptance with carrier details."""
        return await self._render("booking_confirmation.html", data)

    async def generate_credit_note(self, data: dict) -> bytes:
        """Credit Note - Refund or adjustment document."""
        data["note_type"] = "credit_note"
        return await self._render("credit_debit_note.html", data)

    async def generate_debit_note(self, data: dict) -> bytes:
        """Debit Note - Additional charges document."""
        data["note_type"] = "debit_note"
        return await self._render("credit_debit_note.html", data)

    # ═══════════════════════════════════════════════════════════════════
    # Transporter Documents (Carriers)
    # ═══════════════════════════════════════════════════════════════════

    async def generate_load_confirmation(self, data: dict) -> bytes:
        """Load Confirmation - Binding contract with transporter."""
        return await self._render("load_confirmation.html", data)

    async def generate_carrier_invoice(self, data: dict) -> bytes:
        """Carrier Invoice - Bill from transporter for services."""
        return await self._render("carrier_invoice.html", data)

    async def generate_contract(self, data: dict) -> bytes:
        """Transport Contract - Formal agreement between broker and carrier."""
        return await self._render("contract.html", data)

    # ═══════════════════════════════════════════════════════════════════
    # Operational & Legal Documents (Both Parties)
    # ═══════════════════════════════════════════════════════════════════

    async def generate_waybill(self, data: dict) -> bytes:
        """Waybill / Bill of Lading - Receipt, contract, and title document."""
        return await self._render("waybill.html", data)

    async def generate_proof_of_delivery(self, data: dict) -> bytes:
        """Proof of Delivery (POD) - Signed confirmation of safe delivery."""
        return await self._render("proof_of_delivery.html", data)

    async def generate_packing_list(self, data: dict) -> bytes:
        """Packing List - Detailed breakdown of shipment contents."""
        return await self._render("packing_list.html", data)

    async def generate_goods_received_note(self, data: dict) -> bytes:
        """Goods Received Note (GRN) - Receiver's confirmation of inventory."""
        return await self._render("goods_received_note.html", data)


pdf_generator = PDFGenerator()
