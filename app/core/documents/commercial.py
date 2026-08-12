"""
Commercial / Trade Documents for SADC cross-border freight.

These documents are required for all cross-border movements and relate
to the commercial terms of the shipment (who's buying, who's selling,
what's being shipped, and where it originates).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DocType:
    key: str
    label: str
    description: str
    mandatory: bool = True
    ocr_extractable: bool = False  # Phase 3: can OCR auto-extract fields?


# ── Commercial Invoice ──────────────────────────────────────────
COMMERCIAL_INVOICE = DocType(
    key="commercial_invoice",
    label="Commercial Invoice",
    description=(
        "Seller/buyer details, HS codes, Incoterms, unit prices, "
        "total value, currency, country of origin. Must match packing "
        "list line-for-line."
    ),
    mandatory=True,
    ocr_extractable=True,
)

# ── Packing List ────────────────────────────────────────────────
PACKING_LIST = DocType(
    key="packing_list",
    label="Packing List",
    description=(
        "Itemised breakdown of all packages — weights, dimensions, "
        "contents. Customs uses for physical inspection verification. "
        "Must match commercial invoice."
    ),
    mandatory=True,
)

# ── Certificate of Origin (SADC Form CO) ───────────────────────
CERTIFICATE_OF_ORIGIN = DocType(
    key="certificate_of_origin",
    label="Certificate of Origin (SADC Form CO)",
    description=(
        "Confirms goods originate from an SADC member state and qualify "
        "for reduced/zero import duty under SADC Trade Protocol. Must be "
        "issued by authorised body (SARS/dti in SA, ZimTrade in ZIM, MCCI "
        "in MOZ, etc.). Original required — photocopies rejected at most "
        "borders. Goods must meet 35% value addition or sufficient "
        "transformation."
    ),
    mandatory=True,
    ocr_extractable=True,
)

# ── Dangerous Goods Declaration ─────────────────────────────────
DANGEROUS_GOODS_DECLARATION = DocType(
    key="dangerous_goods_declaration",
    label="Dangerous Goods Declaration",
    description=(
        "ADR/DG classification, UN number, packaging group. Required "
        "only when shipping hazardous materials."
    ),
    mandatory=False,  # Conditional — only for DG cargo
)

# ── Phytosanitary Certificate ───────────────────────────────────
PHYTOSANITARY_CERTIFICATE = DocType(
    key="phytosanitary_certificate",
    label="Phytosanitary Certificate",
    description=(
        "Issued by exporting country's plant health authority. "
        "Required for agricultural produce, plant material, seeds, "
        "grains."
    ),
    mandatory=False,  # Conditional — only for agricultural goods
)

# ── Veterinary Certificate ──────────────────────────────────────
VETERINARY_CERTIFICATE = DocType(
    key="veterinary_certificate",
    label="Veterinary Certificate",
    description=(
        "Issued by exporting country's veterinary authority. "
        "Required for animal products, livestock."
    ),
    mandatory=False,  # Conditional — only for animal products
)

# ── Export ──────────────────────────────────────────────────────
EXPORT = DocType(
    key="export",
    label="Export",
    description=(
        "Export"
    ),
    mandatory=True,
)

# ── All commercial doc types ────────────────────────────────────
ALL_COMMERCIAL: list[DocType] = [
    COMMERCIAL_INVOICE,
    PACKING_LIST,
    CERTIFICATE_OF_ORIGIN,
    DANGEROUS_GOODS_DECLARATION,
    PHYTOSANITARY_CERTIFICATE,
    VETERINARY_CERTIFICATE,
    EXPORT,
]

# Quick lookup by key
BY_KEY: dict[str, DocType] = {d.key: d for d in ALL_COMMERCIAL}
