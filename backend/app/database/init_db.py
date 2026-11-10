from sqlalchemy.orm import Session
from app.database.connection import engine, Base
from app.models import (
    User, UserRole,
    Printer, PrinterStatus,
    Kiosk,
    PricingRule,
    PrintAgent
)
from app.core.security import hash_password
from app.core.logging import logger


def init_db(db: Session) -> None:
    """Initializes tables and seeds baseline records for development and testing."""
    Base.metadata.create_all(bind=db.get_bind())

    # 1. Seed Default Admin User
    admin = db.query(User).filter(User.email == "admin@printx.local").first()
    if not admin:
        logger.info("Seeding default administrator account: admin@printx.local")
        admin = User(
            email="admin@printx.local",
            hashed_password=hash_password("AdminPrintX2026!"),
            full_name="PrintX Administrator",
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)

    # 2. Seed Default Student User
    student = db.query(User).filter(User.email == "student@printx.local").first()
    if not student:
        logger.info("Seeding default demo student account: student@printx.local")
        student = User(
            email="student@printx.local",
            hashed_password=hash_password("StudentPrintX2026!"),
            full_name="Demo Student",
            role=UserRole.STUDENT,
            is_active=True
        )
        db.add(student)

    # 3. Kiosk KIOSK-01 (Printers are discovered and connected dynamically by Admin)
    kiosk = db.query(Kiosk).filter(Kiosk.code == "KIOSK-01").first()
    if not kiosk:
        logger.info("Seeding default kiosk: KIOSK-01")
        default_printer = db.query(Printer).filter(Printer.is_default == True).first()
        kiosk = Kiosk(
            code="KIOSK-01",
            name="Central Library Self-Service Hub",
            location="Central Library, Ground Floor East",
            is_active=True,
            default_printer_id=default_printer.id if default_printer else None,
            qr_code_data="http://localhost:5173/print?device=KIOSK-01"
        )
        db.add(kiosk)

    # 6. Seed Default Standard Pricing Rules
    pricing = db.query(PricingRule).filter(PricingRule.name == "Standard University Rates").first()
    if not pricing:
        logger.info("Seeding baseline pricing rule: ₹2.00 B&W, ₹10.00 Color")
        pricing = PricingRule(
            name="Standard University Rates",
            per_page_bw=2.00,
            per_page_color=10.00,
            base_fee=0.00,
            min_order_amount=2.00,
            is_active=True
        )
        db.add(pricing)

    # 7. Seed Windows Agent identity
    agent = db.query(PrintAgent).filter(PrintAgent.agent_id == "AGENT-WIN11-01").first()
    if not agent:
        logger.info("Seeding default agent record: AGENT-WIN11-01")
        agent = PrintAgent(
            agent_id="AGENT-WIN11-01",
            name="Windows 11 Local Host Agent",
            secret_hash=hash_password("printx-agent-local-secret-key"),
            is_active=True,
            version="1.0.0",
            hostname="WIN11-LOCAL"
        )
        db.add(agent)

    db.commit()
    logger.info("Database schema and baseline seed records verified successfully.")
