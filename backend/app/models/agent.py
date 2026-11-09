from sqlalchemy import Column, String, Boolean, DateTime
from app.database.connection import Base
from app.models.base import UUIDMixin, TimestampMixin


class PrintAgent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "print_agents"

    agent_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    secret_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    version = Column(String(50), nullable=True)
    ip_address = Column(String(50), nullable=True)
    hostname = Column(String(255), nullable=True)

