class DeliveryFlowError(Exception):
    """Base exception for DeliveryFlow business logic errors."""
    pass


class InvalidStateTransitionError(DeliveryFlowError):
    """Raised when a state machine transition is invalid."""
    pass


class DriverPackGateError(DeliveryFlowError):
    """Raised when a trip cannot be awarded due to driver pack status."""
    pass


class TokenNotFoundError(DeliveryFlowError):
    """Raised when a tokenized link is invalid or expired."""
    pass


class NotificationError(DeliveryFlowError):
    """Raised when notification dispatch fails."""
    pass


class StorageError(DeliveryFlowError):
    """Raised when object storage operations fail."""
    pass
