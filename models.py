import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, utcnow, ensure_naive_utc

class UserRole:
    ADMIN = "Admin"
    RESPONDER = "Responder"
    REPORTER = "Reporter"

    ALL = [ADMIN, RESPONDER, REPORTER]

    @classmethod
    def can_manage_incidents(cls, role):
        return role in [cls.ADMIN, cls.RESPONDER]

    @classmethod
    def can_admin(cls, role):
        return role == cls.ADMIN

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), default=UserRole.REPORTER, nullable=False)
    api_token = db.Column(db.String(128), unique=True, index=True, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    incidents = db.relationship("Incident", backref="creator", lazy="select", foreign_keys="Incident.user_id")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_token(self):
        self.api_token = f"tok_{secrets.token_urlsafe(32)}"
        return self.api_token

    def to_dict(self, include_token=False):
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_token:
            data["api_token"] = self.api_token
        return data


class IdempotencyRecord(db.Model):
    __tablename__ = "idempotency_records"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False, index=True)
    endpoint = db.Column(db.String(128), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    response_json = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "endpoint": self.endpoint,
            "status_code": self.status_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class IncidentSeverity:
    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_LOW = "P4_LOW"

    ALL = [P1_CRITICAL, P2_HIGH, P3_MEDIUM, P4_LOW]


class IncidentStatus:
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

    ALL = [OPEN, ACKNOWLEDGED, RESOLVED, CLOSED]


class Incident(db.Model):
    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(32), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(32), default=IncidentSeverity.P1_CRITICAL, nullable=False)
    status = db.Column(db.String(32), default=IncidentStatus.OPEN, nullable=False, index=True)
    service_name = db.Column(db.String(128), default="Core Infrastructure", nullable=False)
    triggered_by = db.Column(db.String(128), default="NOC Panic Trigger", nullable=False)
    assigned_to = db.Column(db.String(128), nullable=True)
    is_panic = db.Column(db.Boolean, default=False, nullable=False)
    root_cause = db.Column(db.Text, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    idempotency_key = db.Column(db.String(128), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    audit_logs = db.relationship(
        "AuditLog",
        backref="incident",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="AuditLog.timestamp.desc()"
    )
    notifications = db.relationship(
        "NotificationLog",
        backref="incident",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="NotificationLog.sent_at.desc()"
    )
    comments = db.relationship(
        "TimelineComment",
        backref="incident",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="TimelineComment.created_at.asc()"
    )

    @property
    def mtta_seconds(self):
        """Time to Acknowledge in seconds."""
        ack = ensure_naive_utc(self.acknowledged_at)
        created = ensure_naive_utc(self.created_at)
        if ack and created:
            delta = ack - created
            return max(0, int(delta.total_seconds()))
        elif self.status == IncidentStatus.OPEN and created:
            now = utcnow()
            delta = now - created
            return max(0, int(delta.total_seconds()))
        return None

    @property
    def mttr_seconds(self):
        """Time to Resolve in seconds."""
        resolved = ensure_naive_utc(self.resolved_at)
        created = ensure_naive_utc(self.created_at)
        if resolved and created:
            delta = resolved - created
            return max(0, int(delta.total_seconds()))
        elif self.status in [IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED] and created:
            now = utcnow()
            delta = now - created
            return max(0, int(delta.total_seconds()))
        return None

    def to_dict(self, include_details=False):
        data = {
            "id": self.id,
            "key": self.key,
            "title": self.title,
            "description": self.description or "",
            "severity": self.severity,
            "status": self.status,
            "service_name": self.service_name,
            "triggered_by": self.triggered_by,
            "assigned_to": self.assigned_to or "Unassigned",
            "is_panic": self.is_panic,
            "root_cause": self.root_cause or "",
            "resolution_notes": self.resolution_notes or "",
            "user_id": self.user_id,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "mtta_seconds": self.mtta_seconds,
            "mttr_seconds": self.mttr_seconds,
            "audit_count": len(self.audit_logs),
            "notification_count": len(self.notifications),
            "comment_count": len(self.comments),
        }

        if include_details:
            data["audit_logs"] = [log.to_dict() for log in self.audit_logs]
            data["notifications"] = [notif.to_dict() for notif in self.notifications]
            data["comments"] = [comment.to_dict() for comment in self.comments]

        return data


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("incidents.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(64), nullable=False, index=True)
    actor = db.Column(db.String(128), default="System", nullable=False)
    old_value = db.Column(db.String(255), nullable=True)
    new_value = db.Column(db.String(255), nullable=True)
    message = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "incident_key": self.incident.key if self.incident else None,
            "user_id": self.user_id,
            "action": self.action,
            "actor": self.actor,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "message": self.message,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class NotificationLog(db.Model):
    __tablename__ = "notification_logs"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("incidents.id"), nullable=False, index=True)
    channel = db.Column(db.String(64), nullable=False)  # PAGER_SMS, SLACK, EMAIL, WEBHOOK, NOC_BROADCAST
    recipient = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), default="DELIVERED", nullable=False)
    sent_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "incident_key": self.incident.key if self.incident else None,
            "channel": self.channel,
            "recipient": self.recipient,
            "subject": self.subject,
            "message": self.message,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }


class TimelineComment(db.Model):
    __tablename__ = "timeline_comments"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("incidents.id"), nullable=False, index=True)
    author = db.Column(db.String(128), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "author": self.author,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

