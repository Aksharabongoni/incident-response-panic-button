import urllib.request
import json
import sys

BASE = 'http://127.0.0.1:5000/api'

def req(url, method='GET', data=None, headers=None):
    if headers is None:
        headers = {}
    headers['Content-Type'] = 'application/json'
    body = json.dumps(data).encode('utf-8') if data else None
    r = urllib.request.Request(f'{BASE}{url}', data=body, headers=headers, method=method)
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read().decode('utf-8'))

def main():
    print("==================================================")
    print("STARTING FULL END-TO-END LIVE WORKFLOW VALIDATION")
    print("==================================================")

    # 1. Login as Admin
    login_res = req('/auth/login', 'POST', {'username': 'admin', 'password': 'admin123'})
    token = login_res['user']['api_token']
    auth_hdr = {'Authorization': f'Bearer {token}'}
    print(f"[E2E 1/7] Authenticated as {login_res['user']['username']} (Role: {login_res['user']['role']})")

    # 2. Trigger Panic Button
    panic_payload = {
        'title': 'E2E TEST: Autonomous Database Replication Heartbeat Loss',
        'service_name': 'PostgreSQL Storage Engine',
        'description': 'Master database unreachable. Standby synchronization stalled.',
        'triggered_by': 'Admin Commander'
    }
    panic_res = req('/panic', 'POST', panic_payload, auth_hdr)
    inc = panic_res['incident']
    inc_id = inc['id']
    inc_key = inc['key']
    print(f"[E2E 2/7] Panic Button Triggered -> Key: {inc_key}, Severity: {inc['severity']}, Status: {inc['status']}")
    assert inc['severity'] == 'P1_CRITICAL'
    assert inc['status'] == 'OPEN'
    assert inc['is_panic'] is True

    # 3. Check Notifications
    inc_data = req(f'/incidents/{inc_id}', 'GET', headers=auth_hdr)
    notifs = inc_data['incident']['notifications']
    print(f"[E2E 3/7] Multi-Channel Notifications: {len(notifs)} alerts logged")
    channels = [n['channel'] for n in notifs]
    print(f"         Channels: {', '.join(channels)}")
    assert 'SLACK' in channels
    assert 'PAGER_SMS' in channels

    # 4. Acknowledge Incident (as Responder)
    ack_res = req(f'/incidents/{inc_id}/acknowledge', 'POST', {
        'actor': 'Responder Bob',
        'assigned_to': 'responder'
    }, auth_hdr)
    print(f"[E2E 4/7] Incident Acknowledged! Status: {ack_res['incident']['status']}, MTTA: {ack_res['incident']['mtta_seconds']}s")
    assert ack_res['incident']['status'] == 'ACKNOWLEDGED'

    # 5. Timeline Comment
    comment_res = req(f'/incidents/{inc_id}/comments', 'POST', {
        'comment': 'Investigating WAL logs and restoring network interface eth0.',
        'author': 'Responder Bob'
    }, auth_hdr)
    print(f"[E2E 5/7] Investigation Note: \"{comment_res['comment']['comment']}\"")

    # 6. Resolve Incident
    res_res = req(f'/incidents/{inc_id}/resolve', 'POST', {
        'actor': 'Responder Bob',
        'root_cause': 'Corrupted network bridge filter in hypervisor host.',
        'resolution_notes': 'Restarted vswitchd, synced replication slots, zero data loss verified.'
    }, auth_hdr)
    print(f"[E2E 6/7] Incident Resolved! Status: {res_res['incident']['status']}, MTTR: {res_res['incident']['mttr_seconds']}s")
    assert res_res['incident']['status'] == 'RESOLVED'

    # 7. Audit History Verification
    audit_data = req(f'/incidents/{inc_id}/audit', 'GET', headers=auth_hdr)
    audit_logs = audit_data['audit_logs']
    actions = [a['action'] for a in audit_logs]
    print(f"[E2E 7/7] Immutable Audit History ({len(audit_logs)} events logged):")
    for a in audit_logs:
        print(f"         • [{a['timestamp']}] {a['action']} by {a['actor']}: {a['message']}")

    assert 'PANIC_TRIGGERED' in actions
    assert 'ACKNOWLEDGED' in actions
    assert 'RESOLVED' in actions

    print("==================================================")
    print("SUCCESS: ALL 7 WORKFLOW PHASES FULLY VALIDATED!")
    print("==================================================")

if __name__ == '__main__':
    main()

