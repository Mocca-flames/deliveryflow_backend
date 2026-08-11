import secrets


def generate_tracking_token() -> str:
    """Generate URL-safe token for tracking links."""
    return secrets.token_urlsafe(32)


def generate_carrier_token() -> str:
    """Generate URL-safe token for carrier portal."""
    return secrets.token_urlsafe(32)
