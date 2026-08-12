"""
Permits & Licences for SADC cross-border freight.

These documents authorize the carrier, driver, and vehicle to operate
across international borders within the SADC region.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DocType:
    key: str
    label: str
    description: str
    mandatory: bool = True
    ocr_extractable: bool = False


# ── CBRTA Permit ───────────────────────────────────────────────
CBRTA_PERMIT = DocType(
    key="cbrrta_permit",
    label="Cross-Border Road Transport Permit (CBRTA)",
    description=(
        "Issued by Cross-Border Road Transport Agency. Specifies "
        "countries the vehicle is authorised to enter, vehicle "
        "registration and operator details, validity period. "
        "Annual permits available. Fees (2025): single-country R2,500; "
        "two countries R3,800; 3-5 countries R5,200. Always carry "
        "original — border officials will not accept scanned copies."
    ),
    mandatory=True,
)

# ── SADC Driver Certificate ────────────────────────────────────
SADC_DRIVER_CERTIFICATE = DocType(
    key="sadc_driver_certificate",
    label="SADC Driver Certificate",
    description=(
        "Required for cross-border drivers in addition to SA PrDP. "
        "Issued by CBRTA. Requires valid SA driver's licence "
        "(appropriate code), valid PrDP, medical certificate of "
        "fitness, and eye test certificate."
    ),
    mandatory=True,
)

# ── PrDP (Professional Driving Permit) ─────────────────────────
PRDP = DocType(
    key="prdp",
    label="Professional Driving Permit (PrDP)",
    description=(
        "Required for drivers of commercial vehicles. Must be valid "
        "and appropriate for the vehicle class being operated."
    ),
    mandatory=True,
)

# ── Import Permit (destination country) ─────────────────────────
IMPORT_PERMIT = DocType(
    key="import_permit",
    label="Import Permit (Destination Country)",
    description=(
        "Country-specific import permit for controlled goods. "
        "Zimbabwe: agricultural inputs, manufactured goods. "
        "Zambia: certain food products. Always check destination "
        "country's import control list before dispatching."
    ),
    mandatory=False,  # Conditional — depends on cargo and destination
)

# ── Export Permit (origin country) ──────────────────────────────
EXPORT_PERMIT = DocType(
    key="export_permit",
    label="Export Permit",
    description=(
        "Required for controlled goods leaving the origin country. "
        "Depends on cargo type and origin country regulations."
    ),
    mandatory=False,
)

# ── All permit doc types ────────────────────────────────────────
ALL_PERMITS: list[DocType] = [
    CBRTA_PERMIT,
    SADC_DRIVER_CERTIFICATE,
    PRDP,
    IMPORT_PERMIT,
    EXPORT_PERMIT,
]

BY_KEY: dict[str, DocType] = {d.key: d for d in ALL_PERMITS}
