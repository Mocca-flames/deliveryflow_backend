"""
Shared enums for DeliveryFlow models.
"""
import enum


class BusinessType(str, enum.Enum):
    """Business operation type for a tenant."""
    OWN_FLEET = "own_fleet"
    LOGISTICS = "logistics"
    HYBRID = "hybrid"
