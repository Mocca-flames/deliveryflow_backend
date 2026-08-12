"""
Driver's Pack Documents (KYC-style validation).

These documents are per-driver/vehicle, not per-trip. They form
the KYC package that must be verified before a driver/vehicle
can be assigned to a cross-border trip.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DocType:
    key: str
    label: str
    description: str
    mandatory: bool = True
    ocr_extractable: bool = False


# ── Vehicle Licence ─────────────────────────────────────────────
VEHICLE_LICENCE = DocType(
    key="vehicle_licence",
    label="Vehicle Licence Disc",
    description=(
        "Valid vehicle licence disc for the truck/trailer. "
        "Must be current and match the vehicle registration."
    ),
    mandatory=True,
    ocr_extractable=True,
)

# ── Driver's Licence ────────────────────────────────────────────
DRIVERS_LICENCE = DocType(
    key="drivers_licence",
    label="Driver's Licence",
    description=(
        "Valid driver's licence appropriate for the vehicle class. "
        "Must be valid and match the driver's details."
    ),
    mandatory=True,
    ocr_extractable=True,
)

# ── ID Document ─────────────────────────────────────────────────
ID_DOCUMENT = DocType(
    key="id_document",
    label="ID Document",
    description=(
        "South African ID book/card or passport. Used for identity "
        "verification and cross-border border control."
    ),
    mandatory=True,
    ocr_extractable=True,
)

# ── Insurance Letter ────────────────────────────────────────────
INSURANCE_LETTER = DocType(
    key="insurance_letter",
    label="Insurance Letter",
    description=(
        "Letter of insurance coverage for the vehicle/operator. "
        "Confirms active insurance policy for the carrier."
    ),
    mandatory=True,
)

# ── All driver's pack doc types ─────────────────────────────────
ALL_DRIVER_PACK: list[DocType] = [
    VEHICLE_LICENCE,
    DRIVERS_LICENCE,
    ID_DOCUMENT,
    INSURANCE_LETTER,
]

BY_KEY: dict[str, DocType] = {d.key: d for d in ALL_DRIVER_PACK}
