# Phase 1: Currency code validation only — no multi-currency logic.
# Per MASTER_PLAN.md §4.4: every money field carries a currency code (default ZAR).

VALID_CURRENCIES = frozenset({
    "ZAR",  # South African Rand (default)
    # SADC currencies — schema-ready, logic deferred
    "BWP",  # Botswana Pula
    "NAD",  # Namibian Dollar
    "LSL",  # Lesotho Loti
    "SZL",  # Swazi Lilangeni
    "MZN",  # Mozambican Metical
    "ZMW",  # Zambian Kwacha
    "ZWL",  # Zimbabwean Dollar
    "MWK",  # Malawian Kwacha
    "AOA",  # Angolan Kwanza
    "CD",   # Congolese Franc
    "USD",  # US Dollar
})

DEFAULT_CURRENCY = "ZAR"


def is_valid_currency(code: str) -> bool:
    return code.upper() in VALID_CURRENCIES


def validate_currency(code: str) -> str:
    """Validate and normalize currency code. Raises ValueError if invalid."""
    normalized = code.upper()
    if normalized not in VALID_CURRENCIES:
        raise ValueError(f"Invalid currency: {code}. Valid: {sorted(VALID_CURRENCIES)}")
    return normalized
