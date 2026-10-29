import re
import pytest
from models import IncidentSeverity, IncidentStatus

def test_panic_creates_p1_critical(client, reporter_headers):
    """Verify that triggering the Panic Button immediately creates a P1 Critical incident."""
    res = client.post("/api/panic", json={
        "title": "EMERGENCY: Payment Processing Service Degraded",
        "service_name": "Checkout API",
        "description": "504 Gateway Timeout across all credit card checkout endpoints.",
        "triggered_by": "Ops Lead"
    }, headers=reporter_headers)
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert "incident" in data
    
    inc = data["incident"]
    assert inc["severity"] == IncidentSeverity.P1_CRITICAL
    assert inc["status"] == IncidentStatus.OPEN
    assert inc["is_panic"] is True
    assert inc["service_name"] == "Checkout API"
    assert inc["triggered_by"] == "Ops Lead"
    
    # Verify incident key format: INC-YYYY-XXXX-SS
    assert re.match(r"^INC-\d{4}-\d{4}-\d{2}$", inc["key"]) is not None

def test_panic_dispatches_multi_channel_notifications(client, reporter_headers):
    """Verify that Panic Button activation broadcasts to Pager/SMS, Slack, Email, and NOC."""
    res = client.post("/api/panic", json={
        "title": "EMERGENCY: Redis Replication Outage",
        "service_name": "Cache Layer"
    }, headers=reporter_headers)
    assert res.status_code == 201
    inc_id = res.get_json()["incident"]["id"]

    # Fetch incident details and inspect notifications
    inc_res = client.get(f"/api/incidents/{inc_id}")
    assert inc_res.status_code == 200
    notifs = inc_res.get_json()["incident"]["notifications"]
    
    assert len(notifs) >= 4
    channels = [n["channel"] for n in notifs]
    assert "PAGER_SMS" in channels
    assert "SLACK" in channels
    assert "EMAIL" in channels
    assert "NOC_BROADCAST" in channels

    for n in notifs:
        assert n["incident_id"] == inc_id
        assert n["status"] in ["SENT", "DELIVERED"]
        assert len(n["message"]) > 0

def test_panic_creates_immutable_audit_records(client, reporter_headers):
    """Verify that activating the Panic Button logs PANIC_TRIGGERED and NOTIFICATIONS_DISPATCHED in audit trail."""
    res = client.post("/api/panic", json={
        "title": "EMERGENCY: Edge CDN DNS Resolver Failure",
        "service_name": "DNS Ingress",
        "triggered_by": "Senior SRE"
    }, headers=reporter_headers)
    inc_id = res.get_json()["incident"]["id"]

    audit_res = client.get(f"/api/incidents/{inc_id}/audit")
    assert audit_res.status_code == 200
    logs = audit_res.get_json()["audit_logs"]
    
    actions = [l["action"] for l in logs]
    assert "PANIC_TRIGGERED" in actions
    assert "NOTIFICATIONS_DISPATCHED" in actions

    panic_log = next(l for l in logs if l["action"] == "PANIC_TRIGGERED")
    assert panic_log["actor"] == "Senior SRE"
    assert "P1_CRITICAL" in panic_log["new_value"]
    assert "PANIC BUTTON ACTIVATED" in panic_log["message"]

def test_panic_defaults_to_authenticated_user(client, responder_headers):
    """Verify that if triggered_by is omitted, authenticated user identity is used."""
    res = client.post("/api/panic", json={
        "title": "EMERGENCY: Background Job Worker Starvation",
        "service_name": "Celery Worker Queue"
    }, headers=responder_headers)
    assert res.status_code == 201
    inc = res.get_json()["incident"]
    assert "responder" in inc["triggered_by"].lower()
