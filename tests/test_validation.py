import pytest

def test_empty_json_payload(client):
    """Verify that an empty JSON body returns 400 VALIDATION_ERROR."""
    res = client.post("/api/panic", json={})
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False
    assert data["code"] == "VALIDATION_ERROR"

def test_missing_title(client):
    """Verify missing title returns 400 VALIDATION_ERROR."""
    res = client.post("/api/panic", json={"service_name": "API Gateway"})
    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"
    assert "title is required" in res.get_json()["error"].lower()

def test_title_too_short(client):
    """Verify title with fewer than 5 characters returns 400 VALIDATION_ERROR."""
    res = client.post("/api/panic", json={"title": "OOM", "service_name": "API Gateway"})
    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"
    assert "at least 5 characters" in res.get_json()["error"].lower()

def test_missing_service_name(client):
    """Verify missing service name returns 400 VALIDATION_ERROR."""
    res = client.post("/api/panic", json={"title": "Payment Checkout Down"})
    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"
    assert "service" in res.get_json()["error"].lower() and "required" in res.get_json()["error"].lower()

def test_service_name_too_short(client):
    """Verify service name with fewer than 2 characters returns 400 VALIDATION_ERROR."""
    res = client.post("/api/panic", json={"title": "Payment Checkout Down", "service_name": "A"})
    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"
    assert "at least 2 characters" in res.get_json()["error"].lower()

def test_invalid_severity(client):
    """Verify invalid severity level returns 400 VALIDATION_ERROR."""
    res = client.post("/api/incidents", json={
        "title": "Valid Incident Title",
        "service_name": "Authentication",
        "severity": "P9_SUPER_CRITICAL"
    })
    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"

def test_resolve_missing_root_cause(client, responder_headers):
    """Verify resolving without root cause returns 400 VALIDATION_ERROR."""
    # Create incident
    res = client.post("/api/panic", json={"title": "Worker Node Disk Full", "service_name": "Kubelet"})
    inc_id = res.get_json()["incident"]["id"]

    # Try resolving without root_cause
    bad_resolve = client.post(f"/api/incidents/{inc_id}/resolve", json={
        "root_cause": "",
        "resolution_notes": "Cleaned up /tmp"
    }, headers=responder_headers)
    assert bad_resolve.status_code == 400
    assert bad_resolve.get_json()["code"] == "VALIDATION_ERROR"
    assert "root cause" in bad_resolve.get_json()["error"].lower() and "required" in bad_resolve.get_json()["error"].lower()

def test_nonexistent_incident_not_found(client):
    """Verify querying or acting on a non-existent incident returns 404 NOT_FOUND."""
    res = client.get("/api/incidents/9999999")
    assert res.status_code == 404
    data = res.get_json()
    assert data["code"] == "NOT_FOUND"

    ack_res = client.post("/api/incidents/9999999/acknowledge")
    assert ack_res.status_code == 404
    assert ack_res.get_json()["code"] == "NOT_FOUND"

def test_register_invalid_role(client):
    """Verify registering with an invalid role returns 400 VALIDATION_ERROR."""
    res = client.post("/api/auth/register", json={
        "username": "hacker_bob",
        "email": "hacker@test.com",
        "password": "password123",
        "role": "SuperRootOwner"
    })
    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"
