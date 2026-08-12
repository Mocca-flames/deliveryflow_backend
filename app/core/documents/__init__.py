"""
SADC Cross-Border Documents — Modular Package.

Each document type lives in its own category module:
  - commercial.py  — Invoices, packing lists, certificates of origin
  - transport.py   — Waybills, CMR notes, road manifests
  - customs.py     — SAD forms, declarations, transit bonds
  - permits.py     — CBRTA, driver certs, PrDP
  - insurance.py   — COMESA Yellow Card, GIT, TIP
  - driver_pack.py — Vehicle licence, driver licence, ID, insurance letter
  - registry.py    — Central registry, route-aware requirements

Usage:
    from app.core.documents import get_required_doc_types, is_sacu_only
    from app.core.documents.commercial import COMMERCIAL_INVOICE
    from app.core.documents.registry import get_doc_type, get_category
"""
from app.core.documents.registry import (
    get_required_doc_types,
    is_sacu_only,
    get_doc_type,
    get_category,
    get_all_doc_keys,
    ALL_TRIP_DOCS,
    ALL_BY_KEY,
    CATEGORY_MAP,
    SACU_MEMBERS,
)

__all__ = [
    "get_required_doc_types",
    "is_sacu_only",
    "get_doc_type",
    "get_category",
    "get_all_doc_keys",
    "ALL_TRIP_DOCS",
    "ALL_BY_KEY",
    "CATEGORY_MAP",
    "SACU_MEMBERS",
]
