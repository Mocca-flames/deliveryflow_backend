import asyncio
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

    async def _render(self, template_name: str, data: dict) -> bytes:
        template = self.env.get_template(template_name)
        html_string = template.render(**data)
        return await asyncio.to_thread(
            lambda: HTML(string=html_string, base_url=str(TEMPLATE_DIR)).write_pdf()
        )

    async def generate_invoice(self, data: dict) -> bytes:
        return await self._render("invoice.html", data)

    async def generate_quotation(self, data: dict) -> bytes:
        return await self._render("quotation.html", data)

    async def generate_contract(self, data: dict) -> bytes:
        return await self._render("contract.html", data)

    async def generate_waybill(self, data: dict) -> bytes:
        return await self._render("waybill.html", data)


pdf_generator = PDFGenerator()
