from datetime import datetime
from typing import Optional, Generic, TypeVar, List
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime


class HealthReadyResponse(BaseModel):
    status: str
    database: str
    storage: str
    timestamp: datetime


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int

