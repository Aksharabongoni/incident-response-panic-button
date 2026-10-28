import urllib.request
import json
import uuid
import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE = 'http://127.0.0.1:5000'

def api_call(path, method='GET', data=None, headers=None):
    if headers is None:
        headers = {}
    headers['Content-Type'] = 'application/json'
    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))

def get_page(path):
    req = urllib.request.Request(f"{BASE}{path}")
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read().decode('utf-8')

def main():
    print("[1/10] VERIFYING DATABASE & SEEDED USERS...")
    # Check instance directory and sqlite database
    db_path = os.path.join("instance", "incident_panic.db")
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)
    print(f"  ✓ Database file exists: {db_path} ({os.path.getsize(db_path)} bytes)")

    print("[2/10] VERIFYING LOGIN ACROSS ROLES...")
    # Login Admin
    st, res = api_call('/api/auth/login', 'POST', {'username': 'admin', 'password': 'admin123'})
    assert st == 200 and res['user']['role'] == 'Admin', f"Admin login failed: {res}"
    admin_token = res['user']['api_token']
    admin_hdr = {'Authorization': f'Bearer {admin_token}'}
    print(f"  ✓ Admin login verified: {res['user']['username']} (Role: {res['user']['role']})")

    # Login Responder
    st, res = api_call('/api/auth/login', 'POST', {'username': 'responder', 'password': 'responder123'})
    assert st == 200 and res['user']['role'] == 'Responder', f"Responder login failed: {res}"
    responder_token = res['user']['api_token']
    responder_hdr = {'Authorization': f'Bearer {responder_token}'}
    print(f"  ✓ Responder login verified: {res['user']['username']} (Role: {res['user']['role']})")

    # Login Reporter
    st, res = api_call('/api/auth/login', 'POST', {'username': 'reporter', 'password': 'reporter123'})
    assert st == 200 and res['user']['role'] == 'Reporter', f"Reporter login failed: {res}"
    print(f"  ✓ Reporter login verified: {res['user']['username']} (Role: {res['user']['role']})")

    print("[3/10] VERIFYING PANIC BUTTON & P1 CRITICAL CREATION...")
    idem_key = f"verify-panic-{uuid.uuid4()}"
    panic_payload = {
        'title': 'VERIFICATION: Core Datacenter Ingress Cluster Collapse',
        'service_name': 'Edge Ingress Gateway',
        'description': 'Cascading 502 Bad Gateway across all external traffic.',
        'triggered_by': 'Verification Operator'
    }
    st, res = api_call('/api/panic', 'POST', panic_payload, {'Idempotency-Key': idem_key, **admin_hdr})
    assert st == 201, f"Panic trigger failed: {res}"
    inc = res['incident']
    inc_id = inc['id']
    inc_key = inc['key']
    assert inc['severity'] == 'P1_CRITICAL', f"Expected P1_CRITICAL, got {inc['severity']}"
    assert inc['status'] == 'OPEN', f"Expected OPEN, got {inc['status']}"
    assert inc['is_panic'] is True, "Expected is_panic=True"
    print(f"  ✓ Panic Button activated successfully!")
    print(f"  ✓ P1 Incident Created -> Key: {inc_key}, Severity: {inc['severity']}, Status: {inc['status']}")

    print("[4/10] VERIFYING IDEMPOTENCY REPLAY SAFETY...")
    st_dup, res_dup = api_call('/api/panic', 'POST', panic_payload, {'Idempotency-Key': idem_key, **admin_hdr})
    assert st_dup == 201, f"Idempotent replay failed: {res_dup}"
    assert res_dup['incident']['id'] == inc_id, "Idempotency failed to return cached incident ID"
    assert res_dup['incident']['key'] == inc_key, "Idempotency failed to return matching key"
    print(f"  ✓ Idempotency verified: duplicate POST returned cached response without creating duplicate incident")

    print("[5/10] VERIFYING MULTI-CHANNEL NOTIFICATIONS...")
    st, inc_detail = api_call(f'/api/incidents/{inc_id}', 'GET', headers=admin_hdr)
    assert st == 200
    notifs = inc_detail['incident']['notifications']
    assert len(notifs) >= 4, f"Expected at least 4 notifications, got {len(notifs)}"
    channels = [n['channel'] for n in notifs]
    for ch in ['PAGER_SMS', 'SLACK', 'EMAIL', 'NOC_BROADCAST']:
        assert ch in channels, f"Missing notification channel {ch}"
    print(f"  ✓ Dispatched to all 4 channels: {', '.join(channels)}")

    print("[6/10] VERIFYING INCIDENT ACKNOWLEDGMENT...")
    st, ack_res = api_call(f'/api/incidents/{inc_id}/acknowledge', 'POST', {
        'actor': 'On-Call Responder (Alex)',
        'assigned_to': 'responder'
    }, responder_hdr)
    assert st == 200, f"Acknowledge failed: {ack_res}"
    assert ack_res['incident']['status'] == 'ACKNOWLEDGED'
    assert ack_res['incident']['acknowledged_at'] is not None
    assert ack_res['incident']['mtta_seconds'] is not None
    print(f"  ✓ Incident acknowledged! Status: {ack_res['incident']['status']}, MTTA: {ack_res['incident']['mtta_seconds']}s")

    print("[7/10] VERIFYING TIMELINE NOTES...")
    st, comment_res = api_call(f'/api/incidents/{inc_id}/comments', 'POST', {
        'comment': 'Rerouting border BGP routes to redundant transit provider.',
        'author': 'Alex'
    }, responder_hdr)
    assert st == 201, f"Comment failed: {comment_res}"
    print(f"  ✓ Timeline comment recorded: \"{comment_res['comment']['comment']}\"")

    print("[8/10] VERIFYING INCIDENT RESOLUTION...")
    st, res_res = api_call(f'/api/incidents/{inc_id}/resolve', 'POST', {
        'actor': 'On-Call Responder (Alex)',
        'root_cause': 'Corrupted TCAM routing table on border leaf router.',
        'resolution_notes': 'Flushed FIB/RIB tables and failed over to standby supervisor.'
    }, responder_hdr)
    assert st == 200, f"Resolve failed: {res_res}"
    assert res_res['incident']['status'] == 'RESOLVED'
    assert res_res['incident']['resolved_at'] is not None
    assert res_res['incident']['mttr_seconds'] is not None
    assert res_res['incident']['root_cause'] == 'Corrupted TCAM routing table on border leaf router.'
    print(f"  ✓ Incident resolved! Status: {res_res['incident']['status']}, MTTR: {res_res['incident']['mttr_seconds']}s")

    print("[9/10] VERIFYING IMMUTABLE AUDIT HISTORY...")
    st, audit_res = api_call(f'/api/incidents/{inc_id}/audit', 'GET', headers=admin_hdr)
    assert st == 200, f"Audit fetch failed: {audit_res}"
    logs = audit_res['audit_logs']
    actions = [l['action'] for l in logs]
    assert 'PANIC_TRIGGERED' in actions
    assert 'NOTIFICATIONS_DISPATCHED' in actions
    assert 'ACKNOWLEDGED' in actions
    assert 'RESOLVED' in actions
    print(f"  ✓ Audit history verified ({len(logs)} records captured):")
    for l in logs:
        print(f"     • [{l['timestamp']}] {l['action']} by {l['actor']}")

    print("[10/10] VERIFYING ALL FRONTEND WEB VIEWS...")
    views = ['/', '/analytics', '/audit', '/notifications', '/users', '/login', f'/incidents/{inc_id}']
    for path in views:
        st, html = get_page(path)
        assert st == 200 and '<!DOCTYPE html>' in html, f"Failed rendering view {path}"
        print(f"  ✓ {path} -> HTTP 200 OK")

    print("\n============================================================")
    print("ALL 10 VERIFICATION CHECKS PASSED FLAWLESSLY WITH ZERO ERRORS!")
    print("============================================================")

if __name__ == '__main__':
    main()
