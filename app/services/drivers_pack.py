"""
Driver's Pack service — KYC orchestration, review queue, state transitions.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drivers_pack import DriversPack
from app.state_machines.drivers_pack import transition_drivers_pack
from app.core.exceptions import DeliveryFlowError
from app.config import get_settings

settings = get_settings()


class DriversPackService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: UUID, driver_id: UUID | None, vehicle_id: UUID | None) -> DriversPack:
        """Create a new drivers pack."""
        now = datetime.now(timezone.utc)
        pack = DriversPack(
            tenant_id=tenant_id,
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            status="pending",
            submitted_at=now,
            created_at=now,
            updated_at=now,
        )
        self.db.add(pack)
        await self.db.flush()
        return pack

    async def list(
        self,
        tenant_id: UUID,
        page: int = 1,
        per_page: int = 20,
        status: str | None = None,
    ) -> tuple[list[DriversPack], int]:
        """List drivers packs with pagination."""
        from sqlalchemy import func

        stmt = select(DriversPack).where(DriversPack.tenant_id == tenant_id)
        count_stmt = select(func.count()).select_from(DriversPack).where(DriversPack.tenant_id == tenant_id)

        if status:
            stmt = stmt.where(DriversPack.status == status)
            count_stmt = count_stmt.where(DriversPack.status == status)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.order_by(DriversPack.created_at.desc())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)

        result = await self.db.execute(stmt)
        packs = list(result.scalars().all())

        return packs, total

    async def get(self, pack_id: UUID, tenant_id: UUID) -> DriversPack | None:
        """Get a drivers pack by ID."""
        stmt = select(DriversPack).where(
            DriversPack.id == pack_id,
            DriversPack.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def review_queue(self, tenant_id: UUID) -> list[DriversPack]:
        """Get flagged packs for admin review."""
        stmt = (
            select(DriversPack)
            .where(
                DriversPack.tenant_id == tenant_id,
                DriversPack.status == "flagged",
            )
            .order_by(DriversPack.flagged_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def clear(
        self,
        pack: DriversPack,
        user_id: UUID,
        notes: str | None = None,
    ) -> DriversPack:
        """Admin manual clearance of a flagged pack."""
        return await transition_drivers_pack(
            self.db,
            pack,
            "manually_cleared",
            triggered_by=user_id,
            notes=notes,
        )

    async def run_auto_verification(self, pack: DriversPack) -> DriversPack:
        """
        Auto-verify pack using LLM extraction results.
        Checks all 4 required documents have been uploaded and OCR passed.
        """
        # Check if all documents are uploaded
        required_docs = [
            pack.vehicle_licence_doc_id,
            pack.drivers_licence_doc_id,
            pack.id_document_doc_id,
            pack.insurance_letter_doc_id,
        ]

        all_uploaded = all(doc_id is not None for doc_id in required_docs)

        if not all_uploaded:
            return await transition_drivers_pack(self.db, pack, "flagged", notes="Missing required documents")

        # Check OCR results
        ocr_results = pack.ocr_cross_check or {}
        all_pass = all(
            ocr_results.get(doc_type, {}).get("confidence", 0) >= 0.7
            for doc_type in ["vehicle_licence", "drivers_licence", "id_document", "insurance_letter"]
        )

        if all_pass:
            return await transition_drivers_pack(self.db, pack, "auto_verified")
        else:
            return await transition_drivers_pack(self.db, pack, "flagged", notes="OCR confidence below threshold")

    async def check_and_expire(self) -> int:
        """Expire old packs. Returns count of expired packs."""
        expiry_days = settings.DRIVERS_PACK_EXPIRY_DAYS
        cutoff = datetime.now(timezone.utc) - timedelta(days=expiry_days)

        stmt = select(DriversPack).where(
            DriversPack.status.in_(["pending", "auto_verified", "manually_cleared"]),
            DriversPack.submitted_at < cutoff,
        )
        result = await self.db.execute(stmt)
        expired_packs = result.scalars().all()

        count = 0
        for pack in expired_packs:
            await transition_drivers_pack(self.db, pack, "expired")
            count += 1

        await self.db.flush()
        return count
