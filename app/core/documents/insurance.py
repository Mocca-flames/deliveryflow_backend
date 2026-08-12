"""
Insurance Documents for SADC cross-border freight.

These documents provide coverage for the vehicle, cargo, and
third-party liability across SADC member states.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DocType:
    key: str
    label: str
    description: str
    mandatory: bool = True
    ocr_extractable: bool = False


# ── COMESA Yellow Card ─────────────────────────────────────────
COMESA_YELLOW_CARD = DocType(
    key="comesa_yellow_card",
    label="COMESA Yellow Card",
    description=(
        "Third-party motor vehicle insurance for COMESA member "
        "states (Zimbabwe, Mozambique, Zambia, etc.). Covers "
        "third-party liability — replaces separate country-by-country "
        "insurance. Covers the vehicle, NOT the cargo. Front page "
        "lists covered countries — verify before departure. "
        "USSD verification: *284*8070#. Available from SA insurers "
        "and at some border posts — carry original physical certificate."
    ),
    mandatory=True,
)

# ── Goods in Transit (GIT) Insurance ───────────────────────────
GIT_INSURANCE = DocType(
    key="git_insurance",
    label="Goods in Transit (GIT) Insurance",
    description=(
        "Covers the cargo itself during transit. Separate from "
        "vehicle insurance (COMESA Yellow Card). Required for all "
        "cross-border loads. Covers loss, theft, damage during "
        "transportation."
    ),
    mandatory=True,
)

# ── Temporary Import Permit (TIP) ──────────────────────────────
TEMPORARY_IMPORT_PERMIT = DocType(
    key="temporary_import_permit",
    label="Temporary Import Permit (TIP)",
    description=(
        "For the truck/trailer entering a foreign country temporarily. "
        "Ensures the vehicle is not permanently imported and avoids "
        "duty liability. Usually processed at the border."
    ),
    mandatory=True,
)

# ── All insurance doc types ─────────────────────────────────────
ALL_INSURANCE: list[DocType] = [
    COMESA_YELLOW_CARD,
    GIT_INSURANCE,
    TEMPORARY_IMPORT_PERMIT,
]

BY_KEY: dict[str, DocType] = {d.key: d for d in ALL_INSURANCE}
