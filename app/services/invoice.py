"""
Invoice service — CRUD operations, 70/30 split, milestone transitions.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.trip import Trip
from app.state_machines.invoice import transition_invoice
from app.core.exceptions import DeliveryFlowError


class InvoiceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: UUID, trip_id: UUID) -> Invoice:
        """Create invoice for a trip (auto-generates 70/30 split)."""
        # Fetch trip for reference
        trip = await self.db.get(Trip, trip_id)
        if trip is None:
            raise DeliveryFlowError("Trip not found")

        if trip.quoted_amount is None:
            raise DeliveryFlowError("Trip has no quoted amount")

        now = datetime.now(timezone.utc)
        invoice_number = f"INV-{trip.reference}-{now.strftime('%Y%m%d')}"

        invoice = Invoice(
            tenant_id=tenant_id,
            trip_id=trip_id,
            invoice_number=invoice_number,
            status="draft",
            total_amount=trip.quoted_amount,
            currency=trip.currency,
            upfront_pct=Decimal("70.00"),
            balance_pct=Decimal("30.00"),
            current_milestone="draft",
            created_at=now,
            updated_at=now,
        )
        self.db.add(invoice)
        await self.db.flush()
        return invoice

    async def list(
        self,
        tenant_id: UUID,
        page: int = 1,
        per_page: int = 20,
        status: str | None = None,
    ) -> tuple[list[Invoice], int]:
        """List invoices with pagination."""
        stmt = select(Invoice).where(Invoice.tenant_id == tenant_id)
        count_stmt = select(func.count()).select_from(Invoice).where(Invoice.tenant_id == tenant_id)

        if status:
            stmt = stmt.where(Invoice.status == status)
            count_stmt = count_stmt.where(Invoice.status == status)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.order_by(Invoice.created_at.desc())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)

        result = await self.db.execute(stmt)
        invoices = list(result.scalars().all())

        return invoices, total

    async def get(self, invoice_id: UUID, tenant_id: UUID) -> Invoice | None:
        """Get an invoice by ID."""
        stmt = select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def issue(self, invoice: Invoice, user_id: UUID) -> Invoice:
        """Issue invoice — calculates 70/30 split."""
        return await transition_invoice(
            self.db,
            invoice,
            "issued",
            triggered_by=user_id,
            trigger_source="manual",
        )

    async def verify_pod(self, invoice: Invoice, user_id: UUID) -> Invoice:
        """HITL verify PoD — triggers balance release."""
        # Transition through pod_captured -> pod_verified
        invoice = await transition_invoice(
            self.db,
            invoice,
            "pod_captured",
            triggered_by=user_id,
            trigger_source="manual",
        )
        invoice = await transition_invoice(
            self.db,
            invoice,
            "pod_verified",
            triggered_by=user_id,
            trigger_source="manual",
        )
        return invoice

    async def get_milestones(self, invoice_id: UUID, tenant_id: UUID) -> list:
        """Get milestone history for an invoice."""
        from app.models.invoice import InvoiceMilestone

        stmt = (
            select(InvoiceMilestone)
            .where(
                InvoiceMilestone.invoice_id == invoice_id,
                InvoiceMilestone.tenant_id == tenant_id,
            )
            .order_by(InvoiceMilestone.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
