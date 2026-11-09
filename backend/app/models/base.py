import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from app.database.connection import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UUIDMixin:
    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

