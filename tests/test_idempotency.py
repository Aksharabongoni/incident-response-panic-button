import uuid
import pytest
from database import db
from models import Incident

def test_panic_button_idempotency(client):
    """
    Verify that multiple identical requests with the same Idempotency-Key
    return cached response and create exactly one incident record.
    """
    idempotency_key = f"panic-test-{uuid.uuid4()}"
    headers = {"Idempotency-Key": idempotency_key}

    payload = {
        "title": "IDEMPOTENCY TEST: Network Switch 10G Trunk Drops",
        "service_name": "Datacenter Switch Fabric",
        "description": "BGP flapping detected on spine switch 01."
    }

    # First request: Creates incident
    res1 = client.post("/api/panic", json=payload, headers=headers)
    assert res1.status_code == 201
    data1 = res1.get_json()
    inc1_id = data1["incident"]["id"]
    inc1_key = data1["incident"]["key"]

    # Second request with SAME idempotency key: Returns cached response
    res2 = client.post("/api/panic", json=payload, headers=headers)
    assert res2.status_code == 201
    data2 = res2.get_json()
    assert data2["incident"]["id"] == inc1_id
    assert data2["incident"]["key"] == inc1_key

    # Third request with SAME key: Still cached
    res3 = client.post("/api/panic", json=payload, headers=headers)
    assert res3.status_code == 201
    data3 = res3.get_json()
    assert data3["incident"]["id"] == inc1_id

    # Verify database contains ONLY ONE incident for this title
    with client.application.app_context():
        matching = Incident.query.filter_by(title="IDEMPOTENCY TEST: Network Switch 10G Trunk Drops").all()
        assert len(matching) == 1

def test_manual_incident_creation_idempotency(client):
    """Verify that POST /api/incidents honors Idempotency-Key."""
    key = f"manual-test-{uuid.uuid4()}"
    headers = {"Idempotency-Key": key}

    payload = {
        "title": "IDEMPOTENCY MANUAL: DNS Resolution Timeout",
        "severity": "P2_HIGH",
        "service_name": "Internal DNS"
    }

    res1 = client.post("/api/incidents", json=payload, headers=headers)
    assert res1.status_code == 201
    id1 = res1.get_json()["incident"]["id"]

    res2 = client.post("/api/incidents", json=payload, headers=headers)
    assert res2.status_code == 201
    id2 = res2.get_json()["incident"]["id"]

    assert id1 == id2

def test_x_idempotency_key_header_support(client):
    """Verify support for X-Idempotency-Key header alias."""
    key = f"alias-key-{uuid.uuid4()}"
    headers = {"X-Idempotency-Key": key}

    payload = {
        "title": "IDEMPOTENCY ALIAS: Payment Webhook Latency",
        "service_name": "Payment Webhook"
    }

    res1 = client.post("/api/panic", json=payload, headers=headers)
    assert res1.status_code == 201

    res2 = client.post("/api/panic", json=payload, headers=headers)
    assert res2.status_code == 201
    assert res1.get_json()["incident"]["id"] == res2.get_json()["incident"]["id"]

