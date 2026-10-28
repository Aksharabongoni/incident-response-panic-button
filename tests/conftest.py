import pytest
from app import create_app
from config import TestConfig
from database import db
from services.auth_service import AuthService

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        AuthService.ensure_default_users()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def get_auth_headers(client, username, password):
    """Helper to log in and get Authorization Bearer header."""
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.get_json()}"
    token = res.get_json()["user"]["api_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_headers(client):
    return get_auth_headers(client, "admin", "admin123")

@pytest.fixture
def responder_headers(client):
    return get_auth_headers(client, "responder", "responder123")

@pytest.fixture
def reporter_headers(client):
    return get_auth_headers(client, "reporter", "reporter123")

