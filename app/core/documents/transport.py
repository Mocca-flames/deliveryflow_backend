"""
Transport Documents for SADC cross-border freight.

These documents govern the contract of carriage and the physical
movement of goods by road between SADC member states.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DocType:
    key: str
    label: str
    description: str
    mandatory: bool = True
    ocr_extractable: bool = False


# ── Road Waybill / CMR ─────────────────────────────────────────
ROAD_WAYBILL = DocType(
    key="road_waybill",
    label="Road Waybill / CMR",
    description=(
        "Convention on the Contract for the International Carriage of "
        "Goods by Road. Consignor/consignee details, loading/delivery "
        "points, goods description, number of packages, gross weight, "
        "truck+trailer registration, driver name, date and place of "
        "issue. Serves as contract of carriage and proof of receipt."
    ),
    mandatory=True,
)

# ── CMR Note ────────────────────────────────────────────────────
CMR_NOTE = DocType(
    key="cmr_note",
    label="CMR Consignment Note",
    description=(
        "International consignment note under the CMR Convention. "
        "Standard transport document for road freight between CMR "
        "contracting states."
    ),
    mandatory=True,
)

# ── Road Consignment Note ──────────────────────────────────────
ROAD_CONSIGNMENT_NOTE = DocType(
    key="road_consignment_note",
    label="Road Consignment Note",
    description=(
        "Proof of receipt of goods for road transportation, evidence "
        "of contract of carriage, freight invoice, guide for handling "
        "and delivery. Must be accompanied by commercial invoice and "
        "packing list for customs clearance."
    ),
    mandatory=True,
)

# ── Customs Road Freight Manifest (DA 187) ─────────────────────
CUSTOMS_ROAD_MANIFEST = DocType(
    key="customs_road_manifest",
    label="Customs Road Freight Manifest (DA 187)",
    description=(
        "Must accompany vehicle at all times. Lists all goods carried "
        "on the truck. Certified by licensed remover of goods in bond. "
        "Required by SARS for all cross-border road freight. Completed "
        "in at least triplicate."
    ),
    mandatory=True,
)

# ── All transport doc types ─────────────────────────────────────
ALL_TRANSPORT: list[DocType] = [
    ROAD_WAYBILL,
    CMR_NOTE,
    ROAD_CONSIGNMENT_NOTE,
    CUSTOMS_ROAD_MANIFEST,
]

BY_KEY: dict[str, DocType] = {d.key: d for d in ALL_TRANSPORT}
