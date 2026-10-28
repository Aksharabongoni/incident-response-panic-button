from flask import has_request_context, request, g
from database import db, utcnow
from models import AuditLog

class AuditService:
    @staticmethod
    def record_audit(incident_id, action, actor=None, old_value=None, new_value=None,
                     message="", user_id=None, ip_address=None, user_agent=None):
        """
        Records an immutable audit event for an incident or system event.
        Automatically captures actor, user_id, ip_address, and user_agent from request context if available.
        """
        # Auto-extract from request context if available
        if has_request_context():
            if not user_id and hasattr(g, "current_user") and g.current_user:
                user_id = g.current_user.id
                if not actor:
                    actor = f"{g.current_user.username} ({g.current_user.role})"

            if not ip_address:
                ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)

            if not user_agent and request.user_agent:
                user_agent = str(request.user_agent.string)[:255]

        actor = actor or "System"

        log = AuditLog(
            incident_id=incident_id,
            user_id=user_id,
            action=action,
            actor=actor,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            message=message or f"Action {action} performed by {actor}",
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=utcnow()
        )
        db.session.add(log)
        db.session.flush()
        return log

    @staticmethod
    def get_audit_trail_for_incident(incident_id):
        return AuditLog.query.filter_by(incident_id=incident_id).order_by(AuditLog.timestamp.desc()).all()

    @staticmethod
    def get_all_audit_logs(limit=100, action=None, actor=None, user_id=None):
        query = AuditLog.query
        if action:
            query = query.filter_by(action=action)
        if actor:
            query = query.filter(AuditLog.actor.ilike(f"%{actor}%"))
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

