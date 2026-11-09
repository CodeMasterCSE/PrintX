def test_register_user_success(client):
    payload = {
        "email": "newstudent@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Student"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newstudent@example.com"
    assert data["full_name"] == "Test Student"
    assert data["role"] == "student"
    assert data["is_active"] is True
    assert "id" in data


def test_register_duplicate_email_fails(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "full_name": "Student A"
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_login_success(client):
    # Test logging in with seeded default student
    login_data = {
        "email": "student@printx.local",
        "password": "StudentPrintX2026!"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "student@printx.local"


def test_login_invalid_credentials(client):
    login_data = {
        "email": "student@printx.local",
        "password": "WrongPassword!"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_refresh_token_cycle(client):
    # 1. Login
    login_data = {
        "email": "student@printx.local",
        "password": "StudentPrintX2026!"
    }
    login_res = client.post("/api/v1/auth/login", json=login_data)
    refresh_token = login_res.json()["refresh_token"]

    # 2. Refresh
    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_get_current_user_profile(client):
    # 1. Login
    login_data = {
        "email": "student@printx.local",
        "password": "StudentPrintX2026!"
    }
    login_res = client.post("/api/v1/auth/login", json=login_data)
    token = login_res.json()["access_token"]

    # 2. Access /auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "student@printx.local"

