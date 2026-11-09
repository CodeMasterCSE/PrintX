import enum
from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import UUIDMixin, TimestampMixin


class UserRole(str, enum.Enum):
    STUDENT = "student"
    ADMIN = "admin"
    AGENT = "agent"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    print_jobs = relationship("PrintJob", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")

