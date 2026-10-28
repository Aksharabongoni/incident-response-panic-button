from datetime import timedelta
from database import db, utcnow
from models import Incident, IncidentSeverity, IncidentStatus, AuditLog, NotificationLog, TimelineComment, User, UserRole
from services.auth_service import AuthService

def populate_sample_data():
    """Seeds realistic incident data demonstrating the complete workflow."""
    # Ensure default users exist
    AuthService.ensure_default_users()

    # Check if data already exists
    if Incident.query.count() > 0:
        return Incident.query.count()

    admin_user = User.query.filter_by(role=UserRole.ADMIN).first()
    responder_user = User.query.filter_by(role=UserRole.RESPONDER).first()
    reporter_user = User.query.filter_by(role=UserRole.REPORTER).first()

    now = utcnow()

    # 1. Past Resolved P1 Panic Incident (Database Outage)
    t1_created = now - timedelta(hours=4)
    t1_ack = t1_created + timedelta(minutes=2, seconds=45)
    t1_res = t1_created + timedelta(minutes=24, seconds=10)

    inc1 = Incident(
        key="INC-2026-0001-88",
        title="CRITICAL: Primary PostgreSQL Cluster Failover Exhaustion",
        description="Write pool exhaustion triggered replication lag > 450s. Master node unresponsive. Transactions failing across all checkout flows.",
        severity=IncidentSeverity.P1_CRITICAL,
        status=IncidentStatus.RESOLVED,
        service_name="Database Cluster (PostgreSQL)",
        triggered_by="NOC Panic Trigger (Sarah Connor)",
        assigned_to="Neo Anderson (DBA)",
        is_panic=True,
        user_id=reporter_user.id if reporter_user else None,
        root_cause="Unindexed query surge from automated batch analytics job locked table rows and starved write connections.",
        resolution_notes="Killed rogue query PIDs, scaled connection pooler max_connections by 50%, and promoted warm standby replica.",
        created_at=t1_created,
        acknowledged_at=t1_ack,
        resolved_at=t1_res
    )
    db.session.add(inc1)
    db.session.flush()

    audit1_1 = AuditLog(
        incident_id=inc1.id,
        user_id=reporter_user.id if reporter_user else None,
        action="PANIC_TRIGGERED",
        actor="Sarah Connor (Reporter)",
        old_value=None,
        new_value="Status: OPEN | Severity: P1_CRITICAL",
        message="PANIC BUTTON ACTIVATED by 'Sarah Connor'. Incident INC-2026-0001-88 created for service 'Database Cluster (PostgreSQL)' with P1 Critical severity.",
        timestamp=t1_created
    )
    audit1_2 = AuditLog(
        incident_id=inc1.id,
        action="NOTIFICATIONS_DISPATCHED",
        actor="NotificationEngine",
        old_value=None,
        new_value="Channels: PAGER_SMS, SLACK, EMAIL, NOC_BROADCAST",
        message="Dispatched 4 emergency notification(s) across channels: PAGER_SMS, SLACK, EMAIL, NOC_BROADCAST for event 'TRIGGERED'.",
        timestamp=t1_created + timedelta(seconds=2)
    )
    audit1_3 = AuditLog(
        incident_id=inc1.id,
        user_id=responder_user.id if responder_user else None,
        action="ACKNOWLEDGED",
        actor="Neo Anderson (Responder)",
        old_value="Status: OPEN",
        new_value="Status: ACKNOWLEDGED | Assignee: Neo Anderson (DBA)",
        message="Incident INC-2026-0001-88 acknowledged by 'Neo Anderson'. TTA recorded: 165s. Assignee: 'Neo Anderson (DBA)'.",
        timestamp=t1_ack
    )
    audit1_4 = AuditLog(
        incident_id=inc1.id,
        user_id=responder_user.id if responder_user else None,
        action="RESOLVED",
        actor="Neo Anderson (Responder)",
        old_value="Status: ACKNOWLEDGED",
        new_value="Status: RESOLVED",
        message="Incident INC-2026-0001-88 marked RESOLVED by 'Neo Anderson'. MTTR: 1450s. Root Cause: 'Unindexed query surge'. Resolution: 'Connection pool scaled & replica promoted'.",
        timestamp=t1_res
    )
    db.session.add_all([audit1_1, audit1_2, audit1_3, audit1_4])

    notif1_1 = NotificationLog(
        incident_id=inc1.id,
        channel="PAGER_SMS",
        recipient="Neo Anderson (+1-555-0177)",
        subject="URGENT PAGER: INC-2026-0001-88",
        message="[P1 CRITICAL] INC-2026-0001-88 on Database Cluster (PostgreSQL): Primary failover exhaustion. Respond immediately.",
        status="DELIVERED",
        sent_at=t1_created + timedelta(seconds=1)
    )
    notif1_2 = NotificationLog(
        incident_id=inc1.id,
        channel="SLACK",
        recipient="#incident-war-room",
        subject="🚨 [P1 CRITICAL] Incident INC-2026-0001-88",
        message=":rotating_light: *[P1 CRITICAL INCIDENT DECLARED]* Primary PostgreSQL Cluster Failover Exhaustion.",
        status="DELIVERED",
        sent_at=t1_created + timedelta(seconds=2)
    )
    notif1_3 = NotificationLog(
        incident_id=inc1.id,
        channel="EMAIL",
        recipient="leadership@ops.internal",
        subject="🚨 [P1 CRITICAL] Incident INC-2026-0001-88",
        message="Emergency declared for database cluster.",
        status="DELIVERED",
        sent_at=t1_created + timedelta(seconds=3)
    )
    db.session.add_all([notif1_1, notif1_2, notif1_3])

    c1_1 = TimelineComment(
        incident_id=inc1.id,
        author="Neo Anderson (DBA)",
        comment="Investigating lock contention in pg_stat_activity. Found 14 long-running queries.",
        created_at=t1_ack + timedelta(minutes=5)
    )
    c1_2 = TimelineComment(
        incident_id=inc1.id,
        author="Alex Murphy (SRE)",
        comment="Traffic rerouted to read-only replica to alleviate load while master recovers.",
        created_at=t1_ack + timedelta(minutes=12)
    )
    db.session.add_all([c1_1, c1_2])

    # 2. Acknowledged P1 Incident (Payment Gateway Failure - In Progress)
    t2_created = now - timedelta(minutes=35)
    t2_ack = t2_created + timedelta(minutes=1, seconds=30)

    inc2 = Incident(
        key="INC-2026-0002-42",
        title="CRITICAL: Global Checkout & Payment Gateway Dropping All Charges",
        description="Stripe Webhook timeouts spiked to 98%. HTTP 504 Gateway Timeouts returning to all checkout sessions globally.",
        severity=IncidentSeverity.P1_CRITICAL,
        status=IncidentStatus.ACKNOWLEDGED,
        service_name="Payment Gateway (Stripe Service)",
        triggered_by="NOC Panic Trigger (Alex Murphy)",
        assigned_to="Alex Murphy (DevOps SRE)",
        is_panic=True,
        user_id=responder_user.id if responder_user else None,
        created_at=t2_created,
        acknowledged_at=t2_ack
    )
    db.session.add(inc2)
    db.session.flush()

    audit2_1 = AuditLog(
        incident_id=inc2.id,
        user_id=responder_user.id if responder_user else None,
        action="PANIC_TRIGGERED",
        actor="Alex Murphy (Responder)",
        old_value=None,
        new_value="Status: OPEN | Severity: P1_CRITICAL",
        message="PANIC BUTTON ACTIVATED by 'Alex Murphy'. Incident INC-2026-0002-42 created for service 'Payment Gateway (Stripe Service)'.",
        timestamp=t2_created
    )
    audit2_2 = AuditLog(
        incident_id=inc2.id,
        user_id=responder_user.id if responder_user else None,
        action="ACKNOWLEDGED",
        actor="Alex Murphy (Responder)",
        old_value="Status: OPEN",
        new_value="Status: ACKNOWLEDGED | Assignee: Alex Murphy (DevOps SRE)",
        message="Incident INC-2026-0002-42 acknowledged by 'Alex Murphy'. War room active.",
        timestamp=t2_ack
    )
    db.session.add_all([audit2_1, audit2_2])

    notif2_1 = NotificationLog(
        incident_id=inc2.id,
        channel="PAGER_SMS",
        recipient="Alex Murphy (+1-555-0144)",
        subject="URGENT PAGER: INC-2026-0002-42",
        message="[P1 CRITICAL] Payment Gateway Dropping All Charges. War room opened.",
        status="DELIVERED",
        sent_at=t2_created + timedelta(seconds=1)
    )
    notif2_2 = NotificationLog(
        incident_id=inc2.id,
        channel="SLACK",
        recipient="#incident-war-room",
        subject="🚨 [P1 CRITICAL] INC-2026-0002-42",
        message="War room active: Payment Gateway failure.",
        status="DELIVERED",
        sent_at=t2_created + timedelta(seconds=2)
    )
    db.session.add_all([notif2_1, notif2_2])

    # 3. High P2 Incident (Auth API)
    t3_created = now - timedelta(hours=8)
    t3_ack = t3_created + timedelta(minutes=5)
    t3_res = t3_created + timedelta(minutes=45)

    inc3 = Incident(
        key="INC-2026-0003-19",
        title="HIGH: OAuth Token Expiration Spike in Identity Provider",
        description="Users experiencing premature token expirations during active session renewals.",
        severity=IncidentSeverity.P2_HIGH,
        status=IncidentStatus.RESOLVED,
        service_name="Authentication & SSO Service",
        triggered_by="Automated Monitor (Datadog)",
        assigned_to="Ellen Ripley (SecOps)",
        is_panic=False,
        user_id=admin_user.id if admin_user else None,
        root_cause="Clock drift on Auth worker node pod 3 caused JWT expiry mismatch.",
        resolution_notes="Synchronized NTP daemons across cluster nodes and recycled affected pods.",
        created_at=t3_created,
        acknowledged_at=t3_ack,
        resolved_at=t3_res
    )
    db.session.add(inc3)
    db.session.flush()

    audit3 = AuditLog(
        incident_id=inc3.id,
        user_id=admin_user.id if admin_user else None,
        action="RESOLVED",
        actor="Ellen Ripley (Admin)",
        old_value="Status: ACKNOWLEDGED",
        new_value="Status: RESOLVED",
        message="Resolved NTP sync issue across pods.",
        timestamp=t3_res
    )
    db.session.add(audit3)

    db.session.commit()
    return Incident.query.count()

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        count = populate_sample_data()
        print(f"Database seeded successfully with {count} incidents.")

