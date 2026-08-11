from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = 1
    per_page: int = 20


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
    metadata: dict[str, Any] | None = None


class SuccessResponse(BaseModel):
    message: str
    data: Any = None
