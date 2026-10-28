import pytest

def create_sample_incident(client, headers):
    """Helper to create an incident for RBAC testing."""
    res = client.post("/api/panic", json={
        "title": "RBAC Test Outage: Redis Cache Latency Spike",
        "service_name": "Cache Service"
    }, headers=headers)
    assert res.status_code == 201
    return res.get_json()["incident"]["id"]

def test_reporter_cannot_acknowledge_incident(client, reporter_headers):
    """Verify that Reporter role is forbidden from acknowledging incidents."""
    inc_id = create_sample_incident(client, reporter_headers)
    
    ack_res = client.post(f"/api/incidents/{inc_id}/acknowledge", headers=reporter_headers)
    assert ack_res.status_code == 403
    data = ack_res.get_json()
    assert data["success"] is False
    assert data["code"] == "FORBIDDEN"
    assert "responder or admin" in data["error"].lower()

def test_reporter_cannot_resolve_incident(client, reporter_headers):
    """Verify that Reporter role is forbidden from resolving incidents."""
    inc_id = create_sample_incident(client, reporter_headers)
    
    res_res = client.post(f"/api/incidents/{inc_id}/resolve", json={
        "root_cause": "Restarted service",
        "resolution_notes": "All green"
    }, headers=reporter_headers)
    assert res_res.status_code == 403
    assert res_res.get_json()["code"] == "FORBIDDEN"

def test_reporter_cannot_close_incident(client, reporter_headers):
    """Verify that Reporter role is forbidden from closing incidents."""
    inc_id = create_sample_incident(client, reporter_headers)
    
    close_res = client.post(f"/api/incidents/{inc_id}/close", headers=reporter_headers)
    assert close_res.status_code == 403
    assert close_res.get_json()["code"] == "FORBIDDEN"

def test_reporter_cannot_view_users(client, reporter_headers):
    """Verify that Reporter role cannot access user management endpoint."""
    users_res = client.get("/api/auth/users", headers=reporter_headers)
    assert users_res.status_code == 403
    assert users_res.get_json()["code"] == "FORBIDDEN"

def test_responder_can_acknowledge_and_resolve(client, reporter_headers, responder_headers):
    """Verify that Responder role can successfully acknowledge and resolve incidents."""
    inc_id = create_sample_incident(client, reporter_headers)
    
    # Acknowledge
    ack_res = client.post(f"/api/incidents/{inc_id}/acknowledge", json={
        "actor": "Primary Responder",
        "assigned_to": "responder"
    }, headers=responder_headers)
    assert ack_res.status_code == 200
    assert ack_res.get_json()["incident"]["status"] == "ACKNOWLEDGED"

    # Resolve
    resolve_res = client.post(f"/api/incidents/{inc_id}/resolve", json={
        "actor": "Primary Responder",
        "root_cause": "OOM in caching layer",
        "resolution_notes": "Bumped memory limits in Kubernetes manifest"
    }, headers=responder_headers)
    assert resolve_res.status_code == 200
    assert resolve_res.get_json()["incident"]["status"] == "RESOLVED"

def test_responder_cannot_delete_users(client, responder_headers):
    """Verify that Responder role cannot delete user accounts (Admin only)."""
    res = client.delete("/api/auth/users/2", headers=responder_headers)
    assert res.status_code == 403
    assert res.get_json()["code"] == "FORBIDDEN"

def test_admin_full_privileges(client, admin_headers):
    """Verify that Admin role can perform all privileged operations."""
    inc_id = create_sample_incident(client, admin_headers)

    # Admin acknowledges
    ack_res = client.post(f"/api/incidents/{inc_id}/acknowledge", headers=admin_headers)
    assert ack_res.status_code == 200

    # Admin resolves
    res_res = client.post(f"/api/incidents/{inc_id}/resolve", json={
        "root_cause": "Fixed by Admin"
    }, headers=admin_headers)
    assert res_res.status_code == 200

    # Admin closes incident
    close_res = client.post(f"/api/incidents/{inc_id}/close", headers=admin_headers)
    assert close_res.status_code == 200
    assert close_res.get_json()["incident"]["status"] == "CLOSED"

    # Admin accesses users
    users_res = client.get("/api/auth/users", headers=admin_headers)
    assert users_res.status_code == 200
    assert len(users_res.get_json()["users"]) >= 3

