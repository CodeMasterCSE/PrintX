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

    # 3. Seed Target HP Smart Tank 585 Printer
    printer = db.query(Printer).filter(Printer.name == "HP Smart Tank 580-590 series").first()
    if not printer:
        logger.info("Seeding default target printer: HP Smart Tank 580-590 series")
        printer = Printer(
            name="HP Smart Tank 580-590 series",
            driver_name="HP Smart Tank 580-590 series",
            port_name="USB001",
            location="Ground Floor Kiosk #1",
            is_online=True,
            is_default=True,
            supports_color=True,
            supports_duplex=False,  # Target printer HP Smart Tank 585 is single-sided only
            status=PrinterStatus.ONLINE.value,
            status_details="Ready for incoming print jobs",
            queue_length=0
        )
        db.add(printer)
        db.flush()

    # 4. Seed Fallback Virtual PDF Printer for testing
    pdf_printer = db.query(Printer).filter(Printer.name == "Microsoft Print to PDF").first()
    if not pdf_printer:
        logger.info("Seeding virtual test printer: Microsoft Print to PDF")
        pdf_printer = Printer(
            name="Microsoft Print to PDF",
            driver_name="Microsoft Print To PDF",
            port_name="PORTPROMPT:",
            location="Virtual Test Spooler",
            is_online=True,
            is_default=False,
            supports_color=True,
            supports_duplex=False,
            status=PrinterStatus.ONLINE.value,
            status_details="Virtual test printer",
            queue_length=0
        )
        db.add(pdf_printer)

    # 5. Seed Kiosk KIOSK-01
    kiosk = db.query(Kiosk).filter(Kiosk.code == "KIOSK-01").first()
    if not kiosk:
        logger.info("Seeding default kiosk: KIOSK-01")
        kiosk = Kiosk(
            code="KIOSK-01",
            name="Central Library Self-Service Hub",
            location="Central Library, Ground Floor East",
            is_active=True,
            default_printer_id=printer.id if printer else None,
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
