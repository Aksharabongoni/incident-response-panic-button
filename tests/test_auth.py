import pytest

def test_login_success(client):
    """Verify user authentication with valid credentials returns token and user payload."""
    res = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "user" in data
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "Admin"
    assert "api_token" in data["user"]
    assert data["user"]["api_token"].startswith("tok_")

def test_login_invalid_credentials(client):
    """Verify invalid password returns 401 Unauthorized."""
    res = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert res.status_code == 401
    data = res.get_json()
    assert data["success"] is False
    assert data["code"] in ["AUTHENTICATION_FAILED", "UNAUTHORIZED"]

def test_login_nonexistent_user(client):
    """Verify non-existent username returns 401 Unauthorized."""
    res = client.post("/api/auth/login", json={
        "username": "ghost_user",
        "password": "password123"
    })
    assert res.status_code == 401
    data = res.get_json()
    assert data["code"] in ["AUTHENTICATION_FAILED", "UNAUTHORIZED"]

def test_user_registration(client):
    """Verify registration creates new user with requested role and generates API token."""
    res = client.post("/api/auth/register", json={
        "username": "test_engineer",
        "email": "engineer@ops.internal",
        "password": "secretpassword123",
        "role": "Responder"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["username"] == "test_engineer"
    assert data["user"]["role"] == "Responder"
    assert data["user"]["api_token"].startswith("tok_")

    # Login with new credentials
    login_res = client.post("/api/auth/login", json={
        "username": "test_engineer",
        "password": "secretpassword123"
    })
    assert login_res.status_code == 200

def test_register_duplicate_username(client):
    """Verify duplicate username returns 409 Conflict."""
    res = client.post("/api/auth/register", json={
        "username": "admin",  # Already exists
        "email": "newadmin@ops.internal",
        "password": "password123",
        "role": "Admin"
    })
    assert res.status_code in [400, 409]
    data = res.get_json()
    assert data["code"] in ["CONFLICT", "VALIDATION_ERROR"]
    assert "already exists" in data["error"].lower()

def test_auth_me_bearer_token(client, admin_headers):
    """Verify /api/auth/me returns current user identity when Bearer token is provided."""
    res = client.get("/api/auth/me", headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "Admin"

def test_auth_me_x_api_key(client):
    """Verify /api/auth/me accepts X-API-Key header."""
    login_res = client.post("/api/auth/login", json={"username": "responder", "password": "responder123"})
    token = login_res.get_json()["user"]["api_token"]

    res = client.get("/api/auth/me", headers={"X-API-Key": token})
    assert res.status_code == 200
    data = res.get_json()
    assert data["user"]["username"] == "responder"

def test_unauthenticated_protected_endpoint(client):
    """Verify accessing an authenticated endpoint without credentials returns 401."""
    res = client.get("/api/auth/users")
    assert res.status_code == 401
    data = res.get_json()
    assert data["code"] in ["AUTHENTICATION_FAILED", "UNAUTHORIZED"]

def test_auth_me_guest_when_unauthenticated(client):
    """Verify /api/auth/me returns guest payload when not logged in."""
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.get_json()
    assert data["authenticated"] is False
    assert data["user"]["is_guest"] is True

def test_logout(client):
    """Verify /api/auth/logout terminates session and clears cookies."""
    client.post("/api/auth/login", json={"username": "reporter", "password": "reporter123"})
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.get_json()["success"] is True

def test_switch_role(client):
    """Verify /api/auth/switch-role dynamically switches the active test user."""
    res = client.post("/api/auth/switch-role", json={"role": "Responder"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["role"] == "Responder"
    assert data["user"]["username"] == "responder"

    res_admin = client.post("/api/auth/switch-role", json={"role": "Admin"})
    assert res_admin.status_code == 200
    assert res_admin.get_json()["user"]["role"] == "Admin"
