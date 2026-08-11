"""
Invoice milestone state machine.

Transitions are explicit functions — never direct column updates.
Each transition writes to invoice_milestones (append-only log).
"""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice, InvoiceMilestone
from app.core.exceptions import InvalidStateTransitionError


# Valid transitions: current_status -> list of allowed next statuses
VALID_TRANSITIONS = {
    "draft": ["issued", "cancelled"],
    "issued": ["upfront_requested", "cancelled"],
    "upfront_requested": ["upfront_paid", "cancelled"],
    "upfront_paid": ["in_transit"],
    "in_transit": ["pod_captured"],
    "pod_captured": ["pod_verified"],  # HITL only in Phase 1
    "pod_verified": ["balance_released"],
    "balance_released": ["fully_paid"],
    "fully_paid": [],
    "cancelled": [],
}

# Mapping from transition to milestone name
TRANSITION_MILESTONES = {
    ("draft", "issued"): "invoice_issued",
    ("issued", "upfront_requested"): "upfront_requested",
    ("upfront_requested", "upfront_paid"): "upfront_paid",
    ("upfront_paid", "in_transit"): "transit_started",
    ("in_transit", "pod_captured"): "pod_captured",
    ("pod_captured", "pod_verified"): "pod_verified",
    ("pod_verified", "balance_released"): "balance_released",
    ("balance_released", "fully_paid"): "fully_paid",
}


def validate_transition(current: str, next_status: str) -> None:
    allowed = VALID_TRANSITIONS.get(current, [])
    if next_status not in allowed:
        raise InvalidStateTransitionError(
            f"Cannot transition from '{current}' to '{next_status}'. "
            f"Allowed: {allowed}"
        )


async def transition_invoice(
    db: AsyncSession,
    invoice: Invoice,
    new_status: str,
    triggered_by: "uuid.UUID | None" = None,
    trigger_source: str = "manual",
    notes: str | None = None,
) -> Invoice:
    """Transition invoice to new status, recording milestone event."""
    from app.core.exceptions import InvalidStateTransitionError
    import uuid

    validate_transition(invoice.status, new_status)

    old_status = invoice.status
    now = datetime.now(timezone.utc)

    # Update invoice status
    invoice.status = new_status
    invoice.updated_at = now

    # Set milestone-specific fields
    if new_status == "issued":
        invoice.issued_at = now
        invoice.upfront_amount = invoice.total_amount * (invoice.upfront_pct / Decimal("100"))
        invoice.balance_amount = invoice.total_amount * (invoice.balance_pct / Decimal("100"))
        invoice.current_milestone = "upfront_requested"
    elif new_status == "upfront_paid":
        invoice.upfront_paid_at = now
        invoice.current_milestone = "upfront_paid"
    elif new_status == "in_transit":
        invoice.current_milestone = "in_transit"
    elif new_status == "pod_captured":
        invoice.current_milestone = "pod_captured"
    elif new_status == "pod_verified":
        invoice.current_milestone = "pod_verified"
    elif new_status == "balance_released":
        invoice.current_milestone = "balance_released"
    elif new_status == "fully_paid":
        invoice.balance_paid_at = now
        invoice.current_milestone = "fully_paid"

    # Record milestone event (append-only)
    milestone_name = TRANSITION_MILESTONES.get((old_status, new_status), new_status)
    milestone_event = InvoiceMilestone(
        tenant_id=invoice.tenant_id,
        invoice_id=invoice.id,
        milestone=milestone_name,
        from_status=old_status,
        to_status=new_status,
        triggered_by=triggered_by,
        trigger_source=trigger_source,
        notes=notes,
    )
    db.add(milestone_event)
    await db.flush()

    return invoice
