import pytest
from app.models.printer import Printer
from app.models.pricing import PricingRule
from app.models.kiosk import Kiosk
from app.models.audit import SystemSetting


def test_get_admin_analytics(client):
    res = client.get("/api/v1/admin/analytics")
    assert res.status_code == 200
    data = res.json()
    assert "total_jobs" in data
    assert "total_revenue" in data
    assert "daily_revenue" in data
    assert "weekly_revenue" in data
    assert "monthly_revenue" in data
    assert "active_printers_count" in data
    assert "active_agents_count" in data
    assert "system_health" in data


def test_admin_pricing_update(client, db_session):
    # Ensure active pricing rule exists
    rule = db_session.query(PricingRule).filter(PricingRule.is_active == True).first()
    if not rule:
        rule = PricingRule(
            name="Default Campus Pricing",
            per_page_bw=2.0,
            per_page_color=10.0,
            base_fee=0.0,
            min_order_amount=2.0,
            is_active=True
        )
        db_session.add(rule)
        db_session.commit()

    update_payload = {
        "per_page_bw": 2.50,
        "per_page_color": 12.00,
        "base_fee": 1.00
    }
    res = client.put("/api/v1/admin/pricing", json=update_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["per_page_bw"] == 2.50
    assert data["per_page_color"] == 12.00
    assert data["base_fee"] == 1.00


def test_get_and_update_system_settings(client):
    # 1. Fetch settings (triggers automated baseline seeding if empty)
    get_res = client.get("/api/v1/admin/settings")
    assert get_res.status_code == 200
    settings = get_res.json()["settings"]
    assert len(settings) >= 5
    keys = [s["key"] for s in settings]
    assert "MAX_UPLOAD_SIZE_MB" in keys
    assert "MAX_PAGE_COUNT" in keys

    # 2. Update settings
    update_res = client.put("/api/v1/admin/settings", json={
        "settings": {
            "MAX_UPLOAD_SIZE_MB": "100",
            "CUSTOM_POLICY": "Campus Rule 2026"
        }
    })
    assert update_res.status_code == 200
    updated_items = {s["key"]: s["value"] for s in update_res.json()["settings"]}
    assert updated_items["MAX_UPLOAD_SIZE_MB"] == "100"
    assert updated_items["CUSTOM_POLICY"] == "Campus Rule 2026"


def test_admin_kiosk_management(client):
    # 1. List kiosks
    list_res = client.get("/api/v1/admin/kiosks")
    assert list_res.status_code == 200

    # 2. Register new kiosk
    new_kiosk_code = "KIOSK-NORTH-01"
    create_res = client.post("/api/v1/admin/kiosks", json={
        "code": new_kiosk_code,
        "name": "North Campus Terminal",
        "location": "North Library 2nd Floor"
    })
    assert create_res.status_code == 201
    assert create_res.json()["code"] == new_kiosk_code

    # 3. Duplicate code rejected
    dup_res = client.post("/api/v1/admin/kiosks", json={
        "code": new_kiosk_code,
        "name": "Another",
        "location": "Loc"
    })
    assert dup_res.status_code == 400


def test_admin_printer_status_toggle(client, db_session):
    printer = db_session.query(Printer).first()
    if not printer:
        printer = Printer(
            name="HP Smart Tank 580-590 series",
            driver_name="HP PCL-3",
            port_name="USB001",
            is_online=True,
            is_default=True,
            status="READY",
            queue_length=0
        )
        db_session.add(printer)
        db_session.commit()
        db_session.refresh(printer)

    # Toggle to Maintenance (offline)
    toggle_res = client.post(
        f"/api/v1/admin/printers/{printer.id}/toggle-status",
        json={"is_online": False}
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_online"] is False
    assert toggle_res.json()["status"] == "MAINTENANCE"

    # Toggle back to Ready (online)
    ready_res = client.post(
        f"/api/v1/admin/printers/{printer.id}/toggle-status",
        json={"is_online": True}
    )
    assert ready_res.status_code == 200
    assert ready_res.json()["is_online"] is True
    assert ready_res.json()["status"] == "READY"


def test_admin_set_default_printer(client, db_session):
    p1 = Printer(name="Printer A", is_online=True, is_default=True, status="READY", queue_length=0)
    p2 = Printer(name="Printer B", is_online=True, is_default=False, status="READY", queue_length=0)
    db_session.add_all([p1, p2])
    db_session.commit()

    # Set Printer B as default
    res = client.post(f"/api/v1/admin/printers/{p2.id}/set-default")
    assert res.status_code == 200
    assert res.json()["is_default"] is True

    # Verify Printer A is no longer default
    db_session.refresh(p1)
    assert p1.is_default is False


def test_admin_register_and_list_print_agents(client):
    # 1. Register new agent
    payload = {
        "name": "Library Windows 11 Node",
        "hostname": "WIN11-LIB-01",
        "ip_address": "192.168.1.105"
    }
    reg_res = client.post("/api/v1/admin/agents/register", json=payload)
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert "agent_id" in data
    assert data["agent_id"].startswith("AGENT-WIN11-")
    assert "agent_secret" in data
    assert data["agent_secret"].startswith("px_sec_")
    assert data["name"] == "Library Windows 11 Node"

    # 2. List print agents
    list_res = client.get("/api/v1/admin/agents")
    assert list_res.status_code == 200
    agents = list_res.json()
    assert len(agents) >= 1
    agent_ids = [a["agent_id"] for a in agents]
    assert data["agent_id"] in agent_ids
    # Verify raw secret is NOT leaked in the list response
    for a in agents:
        assert "agent_secret" not in a
        assert "secret_hash" not in a


def test_discover_system_printers(client):
    """Verifies win32print hardware discovery endpoint categorizes USB and Wi-Fi printers."""
    res = client.get("/api/v1/admin/printers/discover")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    if items:
        first = items[0]
        assert "name" in first
        assert "driver_name" in first
        assert "port_name" in first
        assert "connection_type" in first
        assert "is_virtual" in first
        assert "is_already_added" in first
        assert first["connection_type"] in ["USB", "Wi-Fi / Network", "Local Port", "Virtual / Software"]


def test_add_and_delete_printer(client, db_session):
    """Verifies adding a discovered printer and deleting/decommissioning it."""
    # 1. Add printer
    new_printer_payload = {
        "name": "HP Smart Tank 580 Wi-Fi (Engineering Lab)",
        "driver_name": "HP Smart Tank 580-590 series",
        "port_name": "WSD-ab12cd34-5678",
        "location": "Engineering Lab 304",
        "supports_color": True,
        "supports_duplex": False
    }
    add_res = client.post("/api/v1/admin/printers/add", json=new_printer_payload)
    assert add_res.status_code == 201
    p_data = add_res.json()
    assert p_data["name"] == "HP Smart Tank 580 Wi-Fi (Engineering Lab)"
    assert p_data["supports_duplex"] is False
    assert p_data["location"] == "Engineering Lab 304"
    printer_id = p_data["id"]

    # 2. Reject duplicate registration
    dup_res = client.post("/api/v1/admin/printers/add", json=new_printer_payload)
    assert dup_res.status_code == 400
    assert "already registered" in dup_res.json()["detail"]

    # 3. Delete printer
    del_res = client.delete(f"/api/v1/admin/printers/{printer_id}")
    assert del_res.status_code == 200
    assert "successfully removed" in del_res.json()["message"]

    # 4. Verify printer is gone from database
    check_printer = db_session.query(Printer).filter(Printer.id == printer_id).first()
    assert check_printer is None



