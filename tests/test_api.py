import pytest
from app import create_app
from config import TestConfig
from database import db
from models import Incident, AuditLog, NotificationLog, User, UserRole, IncidentSeverity, IncidentStatus

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        from services.auth_service import AuthService
        AuthService.ensure_default_users()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    test_client = app.test_client()
    login = test_client.post("/api/auth/login", json={"username": "responder", "password": "responder123"})
    token = login.get_json()["user"]["api_token"]
    original_post = test_client.post
    original_get = test_client.get

    def authenticated_post(*args, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        if "Authorization" not in headers and "X-API-Key" not in headers:
            headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
        return original_post(*args, **kwargs)

    def authenticated_get(*args, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        if "Authorization" not in headers and "X-API-Key" not in headers:
            headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
        return original_get(*args, **kwargs)

    test_client.post = authenticated_post
    test_client.get = authenticated_get
    return test_client

def get_auth_headers(client, username, password):
    """Helper to log in and get Authorization Bearer header."""
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    token = res.get_json()["user"]["api_token"]
    return {"Authorization": f"Bearer {token}"}

# =========================================================================
# 1. CORE PANIC BUTTON LIFECYCLE WORKFLOW TEST
# =========================================================================
def test_full_incident_panic_lifecycle(client):
    """
    Validates end-to-end core workflow:
    Panic Button
    → P1 Critical Incident
    → Notification Broadcast
    → Open
    → Acknowledged
    → Resolved
    → Audit History
    """
    # 1. PANIC BUTTON TRIGGER
    panic_payload = {
        "title": "EMERGENCY: Primary Payment API Outage",
        "service_name": "Payment Gateway (Stripe)",
        "description": "504 Gateway Timeouts returning on all checkout sessions.",
        "triggered_by": "Sarah Connor (NOC Commander)"
    }
    res = client.post("/api/panic", json=panic_payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    inc = data["incident"]
    inc_id = inc["id"]

    # Verify P1 Critical Incident Created & Status == OPEN
    assert inc["severity"] == IncidentSeverity.P1_CRITICAL
    assert inc["status"] == IncidentStatus.OPEN
    assert inc["is_panic"] is True
    assert "INC-" in inc["key"]
    assert inc["service_name"] == "Payment Gateway (Stripe)"

    # Verify Multi-Channel Notifications Dispatched
    assert len(inc["notifications"]) >= 3
    channels = [n["channel"] for n in inc["notifications"]]
    assert "PAGER_SMS" in channels
    assert "SLACK" in channels
    assert "EMAIL" in channels

    # Verify Initial Audit History
    audit_res = client.get(f"/api/incidents/{inc_id}/audit")
    assert audit_res.status_code == 200
    audit_data = audit_res.get_json()
    audit_actions = [log["action"] for log in audit_data["audit_logs"]]
    assert "PANIC_TRIGGERED" in audit_actions
    assert "NOTIFICATIONS_DISPATCHED" in audit_actions

    # 2. ACKNOWLEDGE INCIDENT (OPEN -> ACKNOWLEDGED)
    ack_res = client.post(f"/api/incidents/{inc_id}/acknowledge", json={
        "actor": "Alex Murphy (DevOps SRE)",
        "assigned_to": "Alex Murphy (DevOps SRE)"
    })
    assert ack_res.status_code == 200
    ack_data = ack_res.get_json()
    assert ack_data["incident"]["status"] == IncidentStatus.ACKNOWLEDGED
    assert ack_data["incident"]["assigned_to"] == "Alex Murphy (DevOps SRE)"
    assert ack_data["incident"]["acknowledged_at"] is not None

    # Check notification dispatched for acknowledgment
    notif_res = client.get(f"/api/notifications?incident_id={inc_id}")
    notifs = notif_res.get_json()["notifications"]
    assert any("ACKNOWLEDGED" in n["subject"] for n in notifs)

    # 3. ADD WAR ROOM COMMENT
    comment_res = client.post(f"/api/incidents/{inc_id}/comments", json={
        "author": "Alex Murphy (DevOps SRE)",
        "comment": "Identified bad config push in release 4.2.1. Preparing immediate hotfix rollback."
    })
    assert comment_res.status_code == 201

    # 4. RESOLVE INCIDENT (ACKNOWLEDGED -> RESOLVED)
    resolve_res = client.post(f"/api/incidents/{inc_id}/resolve", json={
        "actor": "Alex Murphy (DevOps SRE)",
        "root_cause": "Misconfigured HTTP timeout in proxy container introduced in release 4.2.1",
        "resolution_notes": "Rolled back release to 4.2.0 and purged edge CDN caches. Traffic restored."
    })
    assert resolve_res.status_code == 200
    res_data = resolve_res.get_json()
    assert res_data["incident"]["status"] == IncidentStatus.RESOLVED
    assert res_data["incident"]["resolved_at"] is not None
    assert res_data["incident"]["root_cause"] == "Misconfigured HTTP timeout in proxy container introduced in release 4.2.1"
    assert res_data["incident"]["mttr_seconds"] is not None

    # 5. VERIFY COMPLETE IMMUTABLE AUDIT HISTORY
    final_audit_res = client.get(f"/api/incidents/{inc_id}/audit")
    assert final_audit_res.status_code == 200
    final_audit_logs = final_audit_res.get_json()["audit_logs"]

    # Actions must include the full chain in history
    actions_logged = [l["action"] for l in final_audit_logs]
    assert "RESOLVED" in actions_logged
    assert "COMMENT_ADDED" in actions_logged
    assert "ACKNOWLEDGED" in actions_logged
    assert "NOTIFICATIONS_DISPATCHED" in actions_logged
    assert "PANIC_TRIGGERED" in actions_logged

# =========================================================================
# 2. IDEMPOTENCY TESTS
# =========================================================================
def test_panic_button_idempotency(client):
    """
    Ensure that multiple calls with the same Idempotency-Key
    return identical response and do not create duplicate incidents.
    """
    headers = {"Idempotency-Key": "unique-panic-uuid-12345"}
    payload = {
        "title": "Database Outage: Master failover",
        "service_name": "Database Cluster"
    }

    # First call creates incident
    res1 = client.post("/api/panic", json=payload, headers=headers)
    assert res1.status_code == 201
    inc1 = res1.get_json()["incident"]

    # Duplicate call with identical Idempotency-Key
    res2 = client.post("/api/panic", json=payload, headers=headers)
    assert res2.status_code == 201
    inc2 = res2.get_json()["incident"]

    # Must return exact same incident key and id
    assert inc1["id"] == inc2["id"]
    assert inc1["key"] == inc2["key"]

    # Database must contain exactly 1 incident
    all_incidents = client.get("/api/incidents").get_json()["incidents"]
    assert len(all_incidents) == 1

# =========================================================================
# 3. AUTHENTICATION & ROLE-BASED ACCESS CONTROL TESTS
# =========================================================================
def test_authentication_and_roles(client):
    """
    Test user registration, login, and role enforcement:
    - Reporter cannot acknowledge or resolve incidents (403)
    - Responder can acknowledge and resolve incidents (200)
    - Admin can manage users and close incidents (200)
    """
    # 1. Login as default Reporter
    reporter_headers = get_auth_headers(client, "reporter", "reporter123")
    
    # Reporter triggers panic (Allowed!)
    panic_res = client.post("/api/panic", json={"title": "Service Degradation", "service_name": "Search API"}, headers=reporter_headers)
    assert panic_res.status_code == 201
    inc_id = panic_res.get_json()["incident"]["id"]

    # Reporter tries to acknowledge incident (Forbidden!)
    ack_res = client.post(f"/api/incidents/{inc_id}/acknowledge", headers=reporter_headers)
    assert ack_res.status_code == 403
    assert ack_res.get_json()["code"] == "FORBIDDEN"

    # Reporter tries to resolve incident (Forbidden!)
    res_res = client.post(f"/api/incidents/{inc_id}/resolve", json={"root_cause": "Fixed"}, headers=reporter_headers)
    assert res_res.status_code == 403

    # 2. Login as Responder (Allowed!)
    responder_headers = get_auth_headers(client, "responder", "responder123")
    ack_resp = client.post(f"/api/incidents/{inc_id}/acknowledge", headers=responder_headers)
    assert ack_resp.status_code == 200
    assert ack_resp.get_json()["incident"]["status"] == "ACKNOWLEDGED"

    resolve_resp = client.post(f"/api/incidents/{inc_id}/resolve", json={"root_cause": "Cache cleared"}, headers=responder_headers)
    assert resolve_resp.status_code == 200
    assert resolve_resp.get_json()["incident"]["status"] == "RESOLVED"

    # 3. Login as Admin and Close
    admin_headers = get_auth_headers(client, "admin", "admin123")
    close_resp = client.post(f"/api/incidents/{inc_id}/close", headers=admin_headers)
    assert close_resp.status_code == 200
    assert close_resp.get_json()["incident"]["status"] == "CLOSED"

    # Admin lists users
    users_resp = client.get("/api/auth/users", headers=admin_headers)
    assert users_resp.status_code == 200
    assert len(users_resp.get_json()["users"]) >= 3

# =========================================================================
# 4. VALIDATION & ERROR HANDLING TESTS
# =========================================================================
def test_input_validation_and_errors(client):
    """Verify input validation rules and error codes."""
    # Title too short (< 5 chars)
    res = client.post("/api/panic", json={"title": "Fix", "service_name": "API"})
    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"

    # Service name missing
    res2 = client.post("/api/panic", json={"title": "Valid Incident Title Here", "service_name": ""})
    assert res2.status_code == 400
    assert res2.get_json()["code"] == "VALIDATION_ERROR"

    # Non-existent incident
    res3 = client.get("/api/incidents/999999")
    assert res3.status_code == 404
    assert res3.get_json()["code"] == "NOT_FOUND"

    # Invalid state transition: acknowledging an already resolved incident
    inc = client.post("/api/panic", json={"title": "Test Valid Title", "service_name": "Auth API"}).get_json()["incident"]
    client.post(f"/api/incidents/{inc['id']}/resolve", json={"root_cause": "Done"})
    
    bad_ack = client.post(f"/api/incidents/{inc['id']}/acknowledge")
    assert bad_ack.status_code == 400
    assert bad_ack.get_json()["code"] == "INVALID_STATE_TRANSITION"

# =========================================================================
# 5. METRICS & WEB ROUTES TESTS
# =========================================================================
def test_metrics_and_web_routes(client):
    """Verify metrics calculation and all frontend routes."""
    res = client.post("/api/panic", json={"title": "Production Auth Outage", "service_name": "Auth API"})
    inc_id = res.get_json()["incident"]["id"]
    client.post(f"/api/incidents/{inc_id}/acknowledge")
    client.post(f"/api/incidents/{inc_id}/resolve", json={"root_cause": "NTP sync"})

    m_res = client.get("/api/metrics")
    assert m_res.status_code == 200
    m = m_res.get_json()["metrics"]
    assert m["p1_critical_count"] >= 1
    assert m["resolved_count"] >= 1

    # Verify all 7 core frontend web views render with 200 OK
    assert client.get("/").status_code == 200
    assert client.get("/analytics").status_code == 200
    assert client.get("/audit").status_code == 200
    assert client.get("/notifications").status_code == 200
    assert client.get("/users").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get(f"/incidents/{inc_id}").status_code == 200

# =========================================================================
# 6. NOTIFICATION TEST BROADCAST & USER MANAGEMENT TESTS
# =========================================================================
def test_notification_and_user_flows(client):
    """Verify manual test alerts and user provisioning."""
    # Test notification dispatch
    notif_res = client.post("/api/notifications/test", json={
        "channel": "SLACK",
        "recipient": "#incident-war-room",
        "subject": "Test Dispatch",
        "message": "Testing multi-channel alerting"
    })
    assert notif_res.status_code == 201
    assert notif_res.get_json()["notification"]["channel"] == "SLACK"

    # Fetch notifications log
    get_notifs = client.get("/api/notifications?channel=SLACK")
    assert get_notifs.status_code == 200
    assert len(get_notifs.get_json()["notifications"]) >= 1

    # Admin provisions a new responder
    admin_headers = get_auth_headers(client, "admin", "admin123")
    create_user_res = client.post("/api/auth/users", json={
        "username": "lead_responder",
        "email": "lead@ops.internal",
        "password": "securepassword123",
        "role": "Responder"
    }, headers=admin_headers)
    assert create_user_res.status_code == 201
    new_user_id = create_user_res.get_json()["user"]["id"]

    # Change role to Admin
    role_change_res = client.patch(f"/api/auth/users/{new_user_id}/role", json={
        "role": "Admin"
    }, headers=admin_headers)
    assert role_change_res.status_code == 200
    assert role_change_res.get_json()["user"]["role"] == "Admin"


