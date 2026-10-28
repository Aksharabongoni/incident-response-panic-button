import pytest

def test_incident_listing_and_filtering(client):
    """Verify GET /api/incidents with status, severity, and search filters."""
    # Create incidents
    client.post("/api/panic", json={"title": "Primary DB Replica Outage", "service_name": "Postgres"})
    client.post("/api/incidents", json={
        "title": "Minor Typo on Documentation Site",
        "service_name": "Docs",
        "severity": "P4_LOW"
    })

    # All incidents
    all_res = client.get("/api/incidents")
    assert all_res.status_code == 200
    assert len(all_res.get_json()["incidents"]) >= 2

    # Filter by severity
    p1_res = client.get("/api/incidents?severity=P1_CRITICAL")
    assert p1_res.status_code == 200
    p1s = p1_res.get_json()["incidents"]
    assert all(i["severity"] == "P1_CRITICAL" for i in p1s)

    # Filter by search query
    search_res = client.get("/api/incidents?q=Replica")
    assert search_res.status_code == 200
    assert len(search_res.get_json()["incidents"]) >= 1

def test_notifications_endpoint_filtering(client):
    """Verify GET /api/notifications with channel filter."""
    client.post("/api/panic", json={"title": "Notification Filter Test Incident", "service_name": "Alerting"})

    # Filter by channel SLACK
    slack_res = client.get("/api/notifications?channel=SLACK")
    assert slack_res.status_code == 200
    notifs = slack_res.get_json()["notifications"]
    assert len(notifs) >= 1
    assert all(n["channel"] == "SLACK" for n in notifs)

def test_test_notification_broadcast(client):
    """Verify POST /api/notifications/test sends manual alert."""
    res = client.post("/api/notifications/test", json={
        "channel": "PAGER_SMS",
        "recipient": "+1-555-0199",
        "subject": "On-Call Pager Test",
        "message": "Routine pager connectivity check."
    })
    assert res.status_code == 201
    assert res.get_json()["notification"]["channel"] == "PAGER_SMS"

def test_audit_logs_search_and_filters(client):
    """Verify GET /api/audit-logs with action and query parameters."""
    client.post("/api/panic", json={"title": "Audit Query Target Incident", "service_name": "Search"})

    # Query for PANIC_TRIGGERED
    res = client.get("/api/audit-logs?action=PANIC_TRIGGERED")
    assert res.status_code == 200
    logs = res.get_json()["audit_logs"]
    assert len(logs) >= 1
    assert all(l["action"] == "PANIC_TRIGGERED" for l in logs)

def test_metrics_endpoint(client, responder_headers):
    """Verify GET /api/metrics computes correct aggregation counts and MTTA/MTTR."""
    res = client.post("/api/panic", json={"title": "Metrics Calculation Outage", "service_name": "Metrics API"})
    inc_id = res.get_json()["incident"]["id"]
    client.post(f"/api/incidents/{inc_id}/acknowledge", headers=responder_headers)
    client.post(f"/api/incidents/{inc_id}/resolve", json={"root_cause": "Self-healing triggered"}, headers=responder_headers)

    m_res = client.get("/api/metrics")
    assert m_res.status_code == 200
    m = m_res.get_json()["metrics"]
    assert m["p1_critical_count"] >= 1
    assert m["resolved_count"] >= 1
    assert "avg_mtta_seconds" in m
    assert "avg_mttr_seconds" in m

def test_demo_seed_and_reset(client, admin_headers):
    """Verify POST /api/seed and POST /api/reset endpoints."""
    # Seed
    seed_res = client.post("/api/seed", headers=admin_headers)
    assert seed_res.status_code == 200
    assert seed_res.get_json()["success"] is True

    # Check incidents exist
    inc_res = client.get("/api/incidents")
    assert len(inc_res.get_json()["incidents"]) >= 3

    # Reset
    reset_res = client.post("/api/reset", headers=admin_headers)
    assert reset_res.status_code == 200
    assert reset_res.get_json()["success"] is True

    # Check reset emptied incidents
    inc_res_after = client.get("/api/incidents")
    assert len(inc_res_after.get_json()["incidents"]) == 0

def test_all_web_views_render(client):
    """Verify that all HTML frontend views render with HTTP 200."""
    res = client.post("/api/panic", json={"title": "Web View Rendering Target", "service_name": "Web UI"})
    inc_id = res.get_json()["incident"]["id"]

    views = [
        "/",
        "/analytics",
        "/audit",
        "/notifications",
        "/users",
        "/login",
        f"/incidents/{inc_id}"
    ]

    for path in views:
        resp = client.get(path)
        assert resp.status_code == 200, f"Failed on path {path}: status {resp.status_code}"
        assert b"<!DOCTYPE html>" in resp.data

