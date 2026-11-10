import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.core.config import settings
settings.ENVIRONMENT = "testing"
from app.main import app
from app.database.init_db import init_db
from app.models.printer import Printer
from app.models.kiosk import Kiosk

# Use an in-memory SQLite database with StaticPool for test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Creates a fresh database schema for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    init_db(session)
    # Seed a generic test printer for test harness execution
    test_printer = Printer(
        name="Test Hardware Queue",
        driver_name="Test Generic Driver",
        port_name="USB001",
        location="Lab Kiosk",
        is_online=True,
        is_default=True,
        supports_color=True,
        supports_duplex=False,
        status="READY",
        queue_length=0
    )
    session.add(test_printer)
    session.commit()
    kiosk = session.query(Kiosk).first()
    if kiosk:
        kiosk.default_printer_id = test_printer.id
        session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient that uses the isolated test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
