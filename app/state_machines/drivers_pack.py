"""
Driver's Pack state machine.

States: pending -> auto_verified | flagged -> manually_cleared -> expired

Rules:
- pending -> auto_verified | flagged: Automatic OCR check
- flagged -> manually_cleared: Admin reviews in KYC queue
- Any state -> expired: Scheduled Taskiq job
- Hard gate: Trip cannot reach contract_awarded if pack is pending/expired
"""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drivers_pack import DriversPack
from app.core.exceptions import InvalidStateTransitionError


VALID_TRANSITIONS = {
    "pending": ["auto_verified", "flagged", "expired"],
    "auto_verified": ["expired"],
    "flagged": ["manually_cleared", "expired"],
    "manually_cleared": ["expired"],
    "expired": ["pending"],  # Can re-submit after expiry
}


def validate_transition(current: str, next_status: str) -> None:
    allowed = VALID_TRANSITIONS.get(current, [])
    if next_status not in allowed:
        raise InvalidStateTransitionError(
            f"Cannot transition DriversPack from '{current}' to '{next_status}'. "
            f"Allowed: {allowed}"
        )


async def transition_drivers_pack(
    db: AsyncSession,
    pack: DriversPack,
    new_status: str,
    triggered_by: "uuid.UUID | None" = None,
    notes: str | None = None,
) -> DriversPack:
    """Transition drivers pack to new status."""
    from app.core.exceptions import InvalidStateTransitionError
    import uuid

    validate_transition(pack.status, new_status)

    now = datetime.now(timezone.utc)
    old_status = pack.status

    pack.status = new_status
    pack.updated_at = now

    if new_status == "auto_verified":
        pack.verified_at = now
        pack.ocr_pass = True
    elif new_status == "flagged":
        pack.flagged_at = now
        pack.ocr_pass = False
    elif new_status == "manually_cleared":
        pack.cleared_at = now
        pack.reviewed_by = triggered_by
        if notes:
            pack.review_notes = notes
    elif new_status == "pending":
        # Re-submission after expiry
        pack.submitted_at = now
        pack.expires_at = None
        pack.ocr_cross_check = None
        pack.ocr_pass = None

    await db.flush()
    return pack


async def check_pack_gate(db: AsyncSession, driver_id: "uuid.UUID | None", vehicle_id: "uuid.UUID | None") -> bool:
    """
    Hard gate: Returns True if driver/vehicle packs are valid for contract award.
    Returns False if any required pack is pending or expired.
    """
    from sqlalchemy import select, or_
    import uuid

    if driver_id is None and vehicle_id is None:
        return True

    conditions = []
    if driver_id:
        conditions.append(DriversPack.driver_id == driver_id)
    if vehicle_id:
        conditions.append(DriversPack.vehicle_id == vehicle_id)

    stmt = select(DriversPack).where(
        or_(*conditions),
        DriversPack.status.in_(["pending", "expired"]),
    )
    result = await db.execute(stmt)
    invalid_packs = result.scalars().all()

    return len(invalid_packs) == 0
