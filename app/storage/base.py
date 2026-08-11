from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Abstract base for object storage backends."""

    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Store object, return storage key."""
        ...

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Retrieve object by key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete object by key."""
        ...

    @abstractmethod
    async def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate pre-signed download URL."""
        ...
