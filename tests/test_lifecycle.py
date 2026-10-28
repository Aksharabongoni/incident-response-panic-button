import pytest
from models import IncidentStatus

def test_full_lifecycle_progression(client, responder_headers, admin_headers):
    """
    Test complete lifecycle progression:
    OPEN -> ACKNOWLEDGED -> RESOLVED -> CLOSED
    Validates timestamps, duration metrics (MTTA, MTTR), and audit history.
    """
    # 1. CREATE INCIDENT (OPEN)
    create_res = client.post("/api/panic", json={
        "title": "Database Connection Pool Exhaustion Outage",
        "service_name": "PostgreSQL Primary"
    })
    inc_id = create_res.get_json()["incident"]["id"]
    assert create_res.get_json()["incident"]["status"] == IncidentStatus.OPEN

    # 2. ACKNOWLEDGE INCIDENT (OPEN -> ACKNOWLEDGED)
    ack_res = client.post(f"/api/incidents/{inc_id}/acknowledge", json={
        "actor": "Sarah OnCall",
        "assigned_to": "responder"
    }, headers=responder_headers)
    assert ack_res.status_code == 200
    ack_inc = ack_res.get_json()["incident"]
    assert ack_inc["status"] == IncidentStatus.ACKNOWLEDGED
    assert ack_inc["acknowledged_at"] is not None
    assert ack_inc["mtta_seconds"] is not None
    assert ack_inc["assigned_to"] == "responder"

    # 3. RESOLVE INCIDENT (ACKNOWLEDGED -> RESOLVED)
    resolve_res = client.post(f"/api/incidents/{inc_id}/resolve", json={
        "actor": "Sarah OnCall",
        "root_cause": "Unindexed analytics query leaking open db connections",
        "resolution_notes": "Killed zombie connections, deployed index on created_at"
    }, headers=responder_headers)
    assert resolve_res.status_code == 200
    res_inc = resolve_res.get_json()["incident"]
    assert res_inc["status"] == IncidentStatus.RESOLVED
    assert res_inc["resolved_at"] is not None
    assert res_inc["mttr_seconds"] is not None
    assert res_inc["root_cause"] == "Unindexed analytics query leaking open db connections"

    # 4. CLOSE INCIDENT (RESOLVED -> CLOSED)
    close_res = client.post(f"/api/incidents/{inc_id}/close", headers=admin_headers)
    assert close_res.status_code == 200
    assert close_res.get_json()["incident"]["status"] == IncidentStatus.CLOSED

    # 5. VERIFY AUDIT TRAIL RECORDED ALL STEPS
    audit_res = client.get(f"/api/incidents/{inc_id}/audit")
    actions = [l["action"] for l in audit_res.get_json()["audit_logs"]]
    assert "PANIC_TRIGGERED" in actions
    assert "ACKNOWLEDGED" in actions
    assert "RESOLVED" in actions
    assert "CLOSED" in actions

def test_reopen_incident(client, responder_headers):
    """Verify reopening an incident transitions status back to OPEN."""
    res = client.post("/api/panic", json={"title": "Intermittent API Flapping", "service_name": "API"})
    inc_id = res.get_json()["incident"]["id"]
    
    # Ack & Resolve
    client.post(f"/api/incidents/{inc_id}/acknowledge", headers=responder_headers)
    client.post(f"/api/incidents/{inc_id}/resolve", json={"root_cause": "Pod restart"}, headers=responder_headers)

    # Reopen
    reopen_res = client.post(f"/api/incidents/{inc_id}/reopen", json={
        "actor": "QA Engineer",
        "reason": "Errors resurfaced after 5 minutes"
    }, headers=responder_headers)
    assert reopen_res.status_code == 200
    assert reopen_res.get_json()["incident"]["status"] == IncidentStatus.OPEN

    # Check audit log contains REOPENED
    audit = client.get(f"/api/incidents/{inc_id}/audit").get_json()["audit_logs"]
    assert any(a["action"] == "REOPENED" for a in audit)

def test_prohibited_state_transitions(client, responder_headers):
    """Verify invalid state transitions return 400 with INVALID_STATE_TRANSITION."""
    res = client.post("/api/panic", json={"title": "Storage Volume Unmounted", "service_name": "NFS"})
    inc_id = res.get_json()["incident"]["id"]

    # Cannot reopen an already OPEN incident
    bad_reopen = client.post(f"/api/incidents/{inc_id}/reopen", headers=responder_headers)
    assert bad_reopen.status_code == 400
    assert bad_reopen.get_json()["code"] == "INVALID_STATE_TRANSITION"

    # Resolve incident
    client.post(f"/api/incidents/{inc_id}/resolve", json={"root_cause": "Remounted NFS"}, headers=responder_headers)

    # Cannot acknowledge an already RESOLVED incident
    bad_ack = client.post(f"/api/incidents/{inc_id}/acknowledge", headers=responder_headers)
    assert bad_ack.status_code == 400
    assert bad_ack.get_json()["code"] == "INVALID_STATE_TRANSITION"

def test_timeline_comments(client, responder_headers):
    """Verify timeline comments can be added and retrieved chronologically."""
    res = client.post("/api/panic", json={"title": "Kafka Broker 3 Down", "service_name": "Kafka"})
    inc_id = res.get_json()["incident"]["id"]

    c1 = client.post(f"/api/incidents/{inc_id}/comments", json={
        "comment": "Identified high disk I/O on /var/lib/kafka",
        "author": "Alice"
    }, headers=responder_headers)
    assert c1.status_code == 201

    c2 = client.post(f"/api/incidents/{inc_id}/comments", json={
        "comment": "Replaced failing SAS drive, resyncing partitions",
        "author": "Bob"
    }, headers=responder_headers)
    assert c2.status_code == 201

    # Check incident detail has both comments in order
    inc = client.get(f"/api/incidents/{inc_id}").get_json()["incident"]
    comments = inc["comments"]
    assert len(comments) == 2
    assert comments[0]["comment"] == "Identified high disk I/O on /var/lib/kafka"
    assert comments[1]["comment"] == "Replaced failing SAS drive, resyncing partitions"

def test_assign_responder(client, responder_headers):
    """Verify assigning a responder updates assignee and creates ASSIGNMENT_CHANGED audit record."""
    res = client.post("/api/panic", json={"title": "Search Cluster Yellow Health", "service_name": "Elasticsearch"})
    inc_id = res.get_json()["incident"]["id"]

    assign_res = client.post(f"/api/incidents/{inc_id}/assign", json={
        "assigned_to": "elasticsearch_lead",
        "actor": "Incident Commander"
    }, headers=responder_headers)
    assert assign_res.status_code == 200
    assert assign_res.get_json()["incident"]["assigned_to"] == "elasticsearch_lead"

    audit = client.get(f"/api/incidents/{inc_id}/audit").get_json()["audit_logs"]
    assert any(a["action"] == "ASSIGNMENT_CHANGED" for a in audit)

