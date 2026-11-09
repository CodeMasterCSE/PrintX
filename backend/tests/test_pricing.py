def test_pricing_estimate_black_and_white(client):
    # 5 pages, 1 copy, grayscale @ ₹2.00 = ₹10.00
    payload = {
        "page_count": 5,
        "copies": 1,
        "color_mode": "grayscale",
        "page_range": "all"
    }
    response = client.post("/api/v1/pricing/estimate", json=payload)
    assert response.status_code == 200
    data = response.json()
    breakdown = data["breakdown"]
    assert breakdown["selected_pages"] == 5
    assert breakdown["copies"] == 1
    assert breakdown["total_impressions"] == 5
    assert breakdown["rate_per_page"] == 2.0
    assert breakdown["total_amount"] == 10.0


def test_pricing_estimate_color(client):
    # 3 pages, 2 copies, color @ ₹10.00 = ₹60.00
    payload = {
        "page_count": 3,
        "copies": 2,
        "color_mode": "color",
        "page_range": "all"
    }
    response = client.post("/api/v1/pricing/estimate", json=payload)
    assert response.status_code == 200
    data = response.json()
    breakdown = data["breakdown"]
    assert breakdown["selected_pages"] == 3
    assert breakdown["copies"] == 2
    assert breakdown["total_impressions"] == 6
    assert breakdown["rate_per_page"] == 10.0
    assert breakdown["total_amount"] == 60.0


def test_pricing_estimate_custom_page_range(client):
    # Document has 10 pages, user selects '1-3, 5' -> 4 selected pages
    # 1 copy, grayscale @ ₹2.00 = ₹8.00
    payload = {
        "page_count": 10,
        "copies": 1,
        "color_mode": "grayscale",
        "page_range": "1-3, 5"
    }
    response = client.post("/api/v1/pricing/estimate", json=payload)
    assert response.status_code == 200
    data = response.json()
    breakdown = data["breakdown"]
    assert breakdown["selected_pages"] == 4
    assert breakdown["total_amount"] == 8.0


def test_get_pricing_rules(client):
    response = client.get("/api/v1/pricing/rules")
    assert response.status_code == 200
    rules = response.json()
    assert len(rules) >= 1
    assert rules[0]["per_page_bw"] == 2.0
    assert rules[0]["per_page_color"] == 10.0

