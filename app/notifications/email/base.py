from abc import ABC, abstractmethod


class QuotaExceededError(Exception):
    """Raised when an email provider's quota/credits are exhausted."""


class EmailProvider(ABC):
    """Abstract base for email provider adapters."""

    @abstractmethod
    async def send(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> None:
        """
        Send an email. Raises QuotaExceededError if quota is exhausted,
        or any other exception on transient failure.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'brevo', 'mailjet')."""
        ...

    @abstractmethod
    async def is_configured(self) -> bool:
        """Check if the provider has the required credentials."""
        ...
