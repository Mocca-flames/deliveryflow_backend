"""
Customs Documents for SADC cross-border freight.

These documents are required for customs declarations, transit control,
and bonded movement of goods across SADC borders.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DocType:
    key: str
    label: str
    description: str
    mandatory: bool = True
    ocr_extractable: bool = False


# ── SAD 500 (Single Administrative Document) ───────────────────
SAD_500 = DocType(
    key="sad_500",
    label="SAD 500 (Customs Declaration)",
    description=(
        "Official customs declaration form used in South Africa and "
        "several SADC countries. Export entry lodged with SARS before "
        "or at time of departure. Import entry lodged by clearing agent. "
        "Electronic equivalents (eDec/ASYCUDA World) now standard."
    ),
    mandatory=True,
    ocr_extractable=True,
)

# ── SAD 502 ────────────────────────────────────────────────────
SAD_502 = DocType(
    key="sad_502",
    label="SAD 502 (Transit Control)",
    description=(
        "Customs declaration form for transit control and transport "
        "for examination. Required for bonded cargo movements."
    ),
    mandatory=False,  # Only for bonded/transit goods
)

# ── SAD 505 ────────────────────────────────────────────────────
SAD_505 = DocType(
    key="sad_505",
    label="SAD 505 (Bond Transit Control)",
    description=(
        "Customs declaration form for bond transit control and "
        "transport for examination."
    ),
    mandatory=False,
)

# ── SAD 507 ────────────────────────────────────────────────────
SAD_507 = DocType(
    key="sad_507",
    label="SAD 507",
    description=(
        "Additional customs declaration form for specific transit "
        "and bonded goods scenarios."
    ),
    mandatory=False,
)

# ── Export Declaration ──────────────────────────────────────────
EXPORT_DECLARATION = DocType(
    key="export_declaration",
    label="Export Declaration",
    description=(
        "Must be lodged with customs before goods are loaded onto "
        "carrier. Includes Local Reference Number (LRN) and Movement "
        "Reference Number (MRN). For road freight, place of clearance "
        "and port of exit must be the same."
    ),
    mandatory=True,
)

# ── Import Declaration ──────────────────────────────────────────
IMPORT_DECLARATION = DocType(
    key="import_declaration",
    label="Import Declaration",
    description=(
        "Lodged by destination country's clearing agent. Pre-arrival "
        "lodgement strongly recommended to reduce border processing "
        "time. Each country has its own system (ASYCUDA World, SeW, etc.)."
    ),
    mandatory=True,
)

# ── Transit Bond ────────────────────────────────────────────────
TRANSIT_BOND = DocType(
    key="transit_bond",
    label="Transit Bond",
    description=(
        "Required when goods pass through a transit country "
        "(e.g., SA → Mozambique → Malawi). Guarantees customs duties "
        "until goods reach final destination."
    ),
    mandatory=False,  # Conditional — only for transit routes
)

# ── SRCTD (SADC Regional Customs Transit Declaration) ──────────
SRCTD = DocType(
    key="srctd",
    label="SADC Regional Customs Transit Declaration",
    description=(
        "Under the SADC Regional Customs Transit Guarantee (RCTG) "
        "Regulations. Single guarantee from port of commencement to "
        "port of destination. Simplifies clearance and cuts costs."
    ),
    mandatory=False,
)

# ── All customs doc types ───────────────────────────────────────
ALL_CUSTOMS: list[DocType] = [
    SAD_500,
    SAD_502,
    SAD_505,
    SAD_507,
    EXPORT_DECLARATION,
    IMPORT_DECLARATION,
    TRANSIT_BOND,
    SRCTD,
]

BY_KEY: dict[str, DocType] = {d.key: d for d in ALL_CUSTOMS}
