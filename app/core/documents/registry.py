"""
SADC Cross-Border Document Registry.

Central registry that ties all document modules together and provides
route-aware document requirement logic.

Usage:
    from app.core.documents.registry import (
        get_required_doc_types,
        is_sacu_only,
        get_doc_type,
        ALL_DOC_TYPES,
    )
"""
from app.core.documents.commercial import ALL_COMMERCIAL
from app.core.documents.commercial import BY_KEY as COMMERCIAL_BY_KEY
from app.core.documents.customs import ALL_CUSTOMS
from app.core.documents.customs import BY_KEY as CUSTOMS_BY_KEY
from app.core.documents.driver_pack import ALL_DRIVER_PACK
from app.core.documents.insurance import ALL_INSURANCE
from app.core.documents.insurance import BY_KEY as INSURANCE_BY_KEY
from app.core.documents.permits import ALL_PERMITS
from app.core.documents.permits import BY_KEY as PERMITS_BY_KEY
from app.core.documents.transport import ALL_TRANSPORT
from app.core.documents.transport import BY_KEY as TRANSPORT_BY_KEY

# ── Categories ──────────────────────────────────────────────────
COMMERCIAL = "commercial"
TRANSPORT = "transport"
CUSTOMS = "customs"
PERMIT = "permit"
INSURANCE = "insurance"
DRIVER_PACK_CAT = "driver_pack"

# ── All doc types (trip-level, not driver-pack) ─────────────────
ALL_TRIP_DOCS = ALL_COMMERCIAL + ALL_TRANSPORT + ALL_CUSTOMS + ALL_PERMITS + ALL_INSURANCE

# ── Unified lookup ──────────────────────────────────────────────
ALL_BY_KEY: dict[str, object] = {}
ALL_BY_KEY.update(COMMERCIAL_BY_KEY)
ALL_BY_KEY.update(TRANSPORT_BY_KEY)
ALL_BY_KEY.update(CUSTOMS_BY_KEY)
ALL_BY_KEY.update(PERMITS_BY_KEY)
ALL_BY_KEY.update(INSURANCE_BY_KEY)

CATEGORY_MAP: dict[str, str] = {}
for d in ALL_COMMERCIAL:
    CATEGORY_MAP[d.key] = COMMERCIAL
for d in ALL_TRANSPORT:
    CATEGORY_MAP[d.key] = TRANSPORT
for d in ALL_CUSTOMS:
    CATEGORY_MAP[d.key] = CUSTOMS
for d in ALL_PERMITS:
    CATEGORY_MAP[d.key] = PERMIT
for d in ALL_INSURANCE:
    CATEGORY_MAP[d.key] = INSURANCE
for d in ALL_DRIVER_PACK:
    CATEGORY_MAP[d.key] = DRIVER_PACK_CAT


def get_doc_type(key: str):
    """Look up a DocType by its key. Returns None if not found."""
    return ALL_BY_KEY.get(key)


def get_category(key: str) -> str:
    """Get the category for a doc_type key."""
    return CATEGORY_MAP.get(key, "other")


# ── SACU members (simplified process) ──────────────────────────
SACU_MEMBERS = {"ZA", "BW", "LS", "NA", "SZ"}


def is_sacu_only(
    origin_country: str,
    destination_country: str,
    transit_countries: list[str] | None = None,
) -> bool:
    """Check if a trip is entirely within SACU (simplified document requirements)."""
    all_countries = {origin_country, destination_country}
    if transit_countries:
        all_countries.update(transit_countries)
    return all_countries.issubset(SACU_MEMBERS)


# ── Country-specific additional requirements ────────────────────
# Key: country code, Value: doc_type keys that become mandatory
COUNTRY_SPECIFIC_DOCS: dict[str, list[str]] = {
    "ZW": ["transit_bond"],                          # Zimbabwe
    "MZ": ["transit_bond"],                          # Mozambique
    "ZMB": ["transit_bond"],                         # Zambia
    "MW": ["transit_bond"],                          # Malawi (transit through Mozambique)
    "DRC": ["transit_bond"],                         # DRC (BIVAC/OCC + multi-transit)
}


# ── Mandatory baseline (SA-origin, non-SACU) ───────────────────
MANDATORY_SA_ORIGIN: list[str] = [
    "commercial_invoice",
    "packing_list",
    "certificate_of_origin",
    "road_waybill",
    "customs_road_manifest",
    "sad_500",
    "export_declaration",
    "cbrrta_permit",
    "sadc_driver_certificate",
    "prdp",
    "git_insurance",
]


# ── SACU-only baseline ─────────────────────────────────────────
MANDATORY_SACU: list[str] = [
    "commercial_invoice",
    "packing_list",
    "road_waybill",
    "cbrrta_permit",
    "prdp",
    "git_insurance",
]


def get_required_doc_types(
    origin_country: str,
    destination_country: str,
    transit_countries: list[str] | None = None,
) -> list[str]:
    """
    Get list of required doc_type keys for a trip based on route.

    - SACU-only trips get reduced requirements
    - Non-SACU trips get the full baseline + country-specific additions
    """
    if is_sacu_only(origin_country, destination_country, transit_countries):
        return list(MANDATORY_SACU)

    docs = list(MANDATORY_SA_ORIGIN)

    # Add country-specific docs for destination
    if destination_country in COUNTRY_SPECIFIC_DOCS:
        docs.extend(COUNTRY_SPECIFIC_DOCS[destination_country])

    # Add country-specific docs for transit countries
    if transit_countries:
        for tc in transit_countries:
            if tc in COUNTRY_SPECIFIC_DOCS:
                docs.extend(COUNTRY_SPECIFIC_DOCS[tc])

    return list(set(docs))  # Deduplicate


def get_all_doc_keys() -> list[str]:
    """Return all registered document type keys."""
    return list(ALL_BY_KEY.keys())
