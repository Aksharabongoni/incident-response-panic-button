from datetime import datetime
import random
from database import db, utcnow, ensure_naive_utc
from models import Incident, IncidentSeverity, IncidentStatus, TimelineComment, UserRole
from services.audit_service import AuditService
from services.notification_service import NotificationService
from services.auth_service import AuthService
from exceptions import ValidationError, NotFoundError, InvalidStateTransitionError, AuthorizationError

class IncidentService:
    @staticmethod
    def _generate_incident_key():
        """Generates a readable sequential/unique incident key like INC-2026-0042-99."""
        current_year = utcnow().year
        count = Incident.query.count() + 1
        salt = random.randint(10, 99)
        return f"INC-{current_year}-{count:04d}-{salt}"

    @staticmethod
    def _validate_incident_inputs(title, service_name, severity=None, description=None):
        """Strict validation for incident creation parameters."""
        if not title or len(str(title).strip()) < 5:
            raise ValidationError("Incident title is required and must be at least 5 characters.")
        if len(str(title).strip()) > 255:
            raise ValidationError("Incident title cannot exceed 255 characters.")

        if not service_name or len(str(service_name).strip()) < 2:
            raise ValidationError("Service name is required and must be at least 2 characters.")
        if len(str(service_name).strip()) > 128:
            raise ValidationError("Service name cannot exceed 128 characters.")

        if severity and severity not in IncidentSeverity.ALL:
            raise ValidationError(f"Invalid severity '{severity}'. Must be one of: {IncidentSeverity.ALL}")

        if description and len(str(description)) > 5000:
            raise ValidationError("Description cannot exceed 5000 characters.")

    @classmethod
    def trigger_panic(cls, title=None, description=None, service_name=None,
                      triggered_by=None, assigned_to=None, user=None, idempotency_key=None):
        """
        Core Panic Button Trigger:
        1. Validates inputs
        2. Immediately declares a P1_CRITICAL Incident
        3. Sets status to OPEN, is_panic = True
        4. Logs audit entry: PANIC_TRIGGERED
        5. Automatically dispatches emergency multi-channel notifications
        6. Commits and returns Incident
        """
        if not title or len(str(title).strip()) < 5:
            raise ValidationError("Incident title is required and must be at least 5 characters.")
        if not service_name or len(str(service_name).strip()) < 2:
            raise ValidationError("Service name is required and must be at least 2 characters.")

        description = description or "Panic button pressed by operations personnel. Immediate investigation required."
        cls._validate_incident_inputs(title, service_name, severity=IncidentSeverity.P1_CRITICAL, description=description)

        actor_name = triggered_by or (f"{user.username} ({user.role})" if user else "NOC Panic Button Operator")

        incident = Incident(
            key=cls._generate_incident_key(),
            title=title.strip(),
            description=description.strip(),
            severity=IncidentSeverity.P1_CRITICAL,
            status=IncidentStatus.OPEN,
            service_name=service_name.strip(),
            triggered_by=actor_name,
            assigned_to=assigned_to,
            is_panic=True,
            user_id=user.id if user else None,
            idempotency_key=idempotency_key,
            created_at=utcnow()
        )

        db.session.add(incident)
        db.session.flush()

        # 1. Audit Log: Panic Button Activated
        AuditService.record_audit(
            incident_id=incident.id,
            action="PANIC_TRIGGERED",
            actor=actor_name,
            old_value=None,
            new_value=f"Status: OPEN | Severity: {IncidentSeverity.P1_CRITICAL}",
            message=f"PANIC BUTTON ACTIVATED by '{actor_name}'. Incident {incident.key} created for service '{service_name}' with P1 Critical severity.",
            user_id=user.id if user else None
        )

        # 2. Multi-channel Emergency Notification
        NotificationService.dispatch_incident_notifications(incident, event_type="TRIGGERED")

        db.session.commit()
        return incident

    @classmethod
    def create_incident(cls, title, description=None, severity=IncidentSeverity.P1_CRITICAL,
                        service_name="Core Infrastructure", triggered_by=None, assigned_to=None,
                        user=None, idempotency_key=None):
        """Standard incident creation with input validation."""
        cls._validate_incident_inputs(title, service_name, severity=severity, description=description)

        actor_name = triggered_by or (f"{user.username} ({user.role})" if user else "Operator")

        incident = Incident(
            key=cls._generate_incident_key(),
            title=title.strip(),
            description=(description or "").strip(),
            severity=severity,
            status=IncidentStatus.OPEN,
            service_name=service_name.strip(),
            triggered_by=actor_name,
            assigned_to=assigned_to,
            is_panic=False,
            user_id=user.id if user else None,
            idempotency_key=idempotency_key,
            created_at=utcnow()
        )

        db.session.add(incident)
        db.session.flush()

        AuditService.record_audit(
            incident_id=incident.id,
            action="INCIDENT_CREATED",
            actor=actor_name,
            old_value=None,
            new_value=f"Severity: {severity} | Status: OPEN",
            message=f"Incident {incident.key} created by '{actor_name}' for service '{service_name}'.",
            user_id=user.id if user else None
        )

        # Auto-dispatch notifications if P1 Critical
        if severity == IncidentSeverity.P1_CRITICAL:
            NotificationService.dispatch_incident_notifications(incident, event_type="TRIGGERED")

        db.session.commit()
        return incident

    @staticmethod
    def acknowledge_incident(incident_id, actor=None, assigned_to=None, user=None):
        """
        Transitions incident to ACKNOWLEDGED:
        - Validates role permissions (Responder or Admin)
        - Validates current state is OPEN
        - Sets acknowledged_at timestamp & assignee
        - Records audit log & dispatches notification
        """
        if user and not AuthService.user_has_role(user.role, UserRole.RESPONDER):
            raise AuthorizationError(f"User with role '{user.role}' cannot acknowledge incidents. Responder or Admin role required.")

        incident = db.session.get(Incident, incident_id)
        if not incident:
            raise NotFoundError(f"Incident with ID {incident_id} not found.")

        if incident.status != IncidentStatus.OPEN:
            raise InvalidStateTransitionError(
                f"Cannot acknowledge incident in '{incident.status}' state. Only OPEN incidents can be acknowledged."
            )

        actor_name = actor or (f"{user.username} ({user.role})" if user else "Responder")
        old_status = incident.status
        incident.status = IncidentStatus.ACKNOWLEDGED
        incident.acknowledged_at = utcnow()

        if assigned_to:
            incident.assigned_to = assigned_to
        elif not incident.assigned_to:
            incident.assigned_to = user.username if user else actor_name

        AuditService.record_audit(
            incident_id=incident.id,
            action="ACKNOWLEDGED",
            actor=actor_name,
            old_value=f"Status: {old_status}",
            new_value=f"Status: {incident.status} | Assignee: {incident.assigned_to}",
            message=f"Incident {incident.key} acknowledged by '{actor_name}'. TTA recorded: {incident.mtta_seconds}s. Assignee: '{incident.assigned_to}'.",
            user_id=user.id if user else None
        )

        NotificationService.dispatch_incident_notifications(incident, event_type="ACKNOWLEDGED")

        db.session.commit()
        return incident

    @staticmethod
    def resolve_incident(incident_id, actor=None, root_cause=None, resolution_notes=None, user=None):
        """
        Transitions incident to RESOLVED:
        - Validates role permissions (Responder or Admin)
        - Validates current state (must be OPEN or ACKNOWLEDGED)
        - Records root cause and resolution notes
        - Records MTTR & dispatches resolution alert
        """
        if user and not AuthService.user_has_role(user.role, UserRole.RESPONDER):
            raise AuthorizationError(f"User with role '{user.role}' cannot resolve incidents. Responder or Admin role required.")

        incident = db.session.get(Incident, incident_id)
        if not incident:
            raise NotFoundError(f"Incident with ID {incident_id} not found.")

        if incident.status in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]:
            raise InvalidStateTransitionError(f"Incident is already in '{incident.status}' state.")

        if not root_cause or len(str(root_cause).strip()) < 3:
            raise ValidationError("Root cause is required and must be at least 3 characters.")

        actor_name = actor or (f"{user.username} ({user.role})" if user else "Responder")
        old_status = incident.status
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = utcnow()
        incident.root_cause = root_cause.strip()
        if resolution_notes:
            incident.resolution_notes = resolution_notes.strip()

        # If it was never explicitly acknowledged, acknowledge it now
        if not incident.acknowledged_at:
            incident.acknowledged_at = incident.resolved_at

        AuditService.record_audit(
            incident_id=incident.id,
            action="RESOLVED",
            actor=actor_name,
            old_value=f"Status: {old_status}",
            new_value="Status: RESOLVED",
            message=(
                f"Incident {incident.key} marked RESOLVED by '{actor_name}'. "
                f"MTTR: {incident.mttr_seconds}s. "
                f"Root Cause: '{incident.root_cause or 'Not specified'}'. "
                f"Resolution: '{incident.resolution_notes or 'Not specified'}'."
            ),
            user_id=user.id if user else None
        )

        NotificationService.dispatch_incident_notifications(incident, event_type="RESOLVED")

        db.session.commit()
        return incident

    @staticmethod
    def close_incident(incident_id, actor=None, user=None):
        """Marks incident as CLOSED (archived post-mortem). Only Admin or Responder."""
        if user and not AuthService.user_has_role(user.role, UserRole.RESPONDER):
            raise AuthorizationError(f"User with role '{user.role}' cannot close incidents. Responder or Admin role required.")

        incident = db.session.get(Incident, incident_id)
        if not incident:
            raise NotFoundError(f"Incident with ID {incident_id} not found.")

        if incident.status != IncidentStatus.RESOLVED:
            raise InvalidStateTransitionError(f"Only RESOLVED incidents can be closed. Current status is '{incident.status}'.")

        actor_name = actor or (f"{user.username} ({user.role})" if user else "Incident Commander")
        old_status = incident.status
        incident.status = IncidentStatus.CLOSED
        incident.closed_at = utcnow()

        AuditService.record_audit(
            incident_id=incident.id,
            action="CLOSED",
            actor=actor_name,
            old_value=f"Status: {old_status}",
            new_value="Status: CLOSED",
            message=f"Incident {incident.key} formally closed by '{actor_name}'.",
            user_id=user.id if user else None
        )

        db.session.commit()
        return incident

    @staticmethod
    def reopen_incident(incident_id, actor=None, reason=None, user=None):
        """Re-opens a resolved incident if a regression occurs."""
        if user and not AuthService.user_has_role(user.role, UserRole.RESPONDER):
            raise AuthorizationError(f"User with role '{user.role}' cannot reopen incidents. Responder or Admin role required.")

        incident = db.session.get(Incident, incident_id)
        if not incident:
            raise NotFoundError(f"Incident with ID {incident_id} not found.")

        if incident.status not in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]:
            raise InvalidStateTransitionError(f"Cannot reopen incident in '{incident.status}' state.")

        actor_name = actor or (f"{user.username} ({user.role})" if user else "Responder")
        old_status = incident.status
        incident.status = IncidentStatus.OPEN
        incident.resolved_at = None
        incident.closed_at = None

        AuditService.record_audit(
            incident_id=incident.id,
            action="REOPENED",
            actor=actor_name,
            old_value=f"Status: {old_status}",
            new_value="Status: OPEN",
            message=f"Incident {incident.key} reopened by '{actor_name}'. Reason: '{reason or 'Regression detected'}'.",
            user_id=user.id if user else None
        )

        NotificationService.dispatch_incident_notifications(incident, event_type="TRIGGERED", extra_info="REOPENED")

        db.session.commit()
        return incident

    @staticmethod
    def add_comment(incident_id, author, comment_text, user=None):
        """Adds a timeline update / comment with length validation."""
        if not comment_text or len(str(comment_text).strip()) == 0:
            raise ValidationError("Comment text cannot be empty.")
        if len(str(comment_text).strip()) > 3000:
            raise ValidationError("Comment text cannot exceed 3000 characters.")

        incident = db.session.get(Incident, incident_id)
        if not incident:
            raise NotFoundError(f"Incident with ID {incident_id} not found.")

        author_name = author or (f"{user.username} ({user.role})" if user else "Operator")

        comment = TimelineComment(
            incident_id=incident.id,
            author=author_name,
            comment=comment_text.strip(),
            created_at=utcnow()
        )
        db.session.add(comment)
        db.session.flush()

        AuditService.record_audit(
            incident_id=incident.id,
            action="COMMENT_ADDED",
            actor=author_name,
            old_value=None,
            new_value=None,
            message=f"Timeline update by {author_name}: '{comment_text[:80]}...'" if len(comment_text) > 80 else f"Timeline update by {author_name}: '{comment_text}'",
            user_id=user.id if user else None
        )

        db.session.commit()
        return comment

    @staticmethod
    def assign_incident(incident_id, actor, assigned_to, user=None):
        """Reassigns or sets assignee for an incident."""
        if user and not AuthService.user_has_role(user.role, UserRole.RESPONDER):
            raise AuthorizationError(f"User with role '{user.role}' cannot reassign incidents. Responder or Admin role required.")

        if not assigned_to or len(str(assigned_to).strip()) == 0:
            raise ValidationError("Assignee name is required.")

        incident = db.session.get(Incident, incident_id)
        if not incident:
            raise NotFoundError(f"Incident with ID {incident_id} not found.")

        actor_name = actor or (f"{user.username} ({user.role})" if user else "Operator")
        old_assignee = incident.assigned_to or "Unassigned"
        incident.assigned_to = assigned_to.strip()

        AuditService.record_audit(
            incident_id=incident.id,
            action="ASSIGNMENT_CHANGED",
            actor=actor_name,
            old_value=f"Assignee: {old_assignee}",
            new_value=f"Assignee: {incident.assigned_to}",
            message=f"Incident {incident.key} reassigned from '{old_assignee}' to '{incident.assigned_to}' by '{actor_name}'.",
            user_id=user.id if user else None
        )

        db.session.commit()
        return incident

    @staticmethod
    def get_metrics():
        """Computes executive and operational metrics (MTTA, MTTR, breakdowns)."""
        incidents = Incident.query.all()
        total_incidents = len(incidents)
        p1_critical_count = sum(1 for inc in incidents if inc.severity == IncidentSeverity.P1_CRITICAL)
        open_count = sum(1 for inc in incidents if inc.status == IncidentStatus.OPEN)
        acknowledged_count = sum(1 for inc in incidents if inc.status == IncidentStatus.ACKNOWLEDGED)
        resolved_count = sum(1 for inc in incidents if inc.status in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED])
        panic_triggered_count = sum(1 for inc in incidents if inc.is_panic)

        # Calculate Mean Time to Acknowledge (MTTA)
        mtta_values = []
        for inc in incidents:
            ack = ensure_naive_utc(inc.acknowledged_at)
            created = ensure_naive_utc(inc.created_at)
            if ack and created:
                mtta_values.append(max(0, (ack - created).total_seconds()))

        avg_mtta_sec = round(sum(mtta_values) / len(mtta_values), 1) if mtta_values else 0
        avg_mtta_min = round(avg_mtta_sec / 60, 1)

        # Calculate Mean Time to Resolve (MTTR)
        mttr_values = []
        for inc in incidents:
            resolved = ensure_naive_utc(inc.resolved_at)
            created = ensure_naive_utc(inc.created_at)
            if resolved and created:
                mttr_values.append(max(0, (resolved - created).total_seconds()))

        avg_mttr_sec = round(sum(mttr_values) / len(mttr_values), 1) if mttr_values else 0
        avg_mttr_min = round(avg_mttr_sec / 60, 1)

        # Categorical distributions
        severity_dist = {sev: 0 for sev in IncidentSeverity.ALL}
        for inc in incidents:
            severity_dist[inc.severity] = severity_dist.get(inc.severity, 0) + 1

        status_dist = {st: 0 for st in IncidentStatus.ALL}
        for inc in incidents:
            status_dist[inc.status] = status_dist.get(inc.status, 0) + 1

        service_dist = {}
        for inc in incidents:
            srv = inc.service_name or "Unknown"
            service_dist[srv] = service_dist.get(srv, 0) + 1

        return {
            "total_incidents": total_incidents,
            "p1_critical_count": p1_critical_count,
            "open_count": open_count,
            "acknowledged_count": acknowledged_count,
            "resolved_count": resolved_count,
            "panic_triggered_count": panic_triggered_count,
            "avg_mtta_seconds": avg_mtta_sec,
            "avg_mtta_minutes": avg_mtta_min,
            "avg_mttr_seconds": avg_mttr_sec,
            "avg_mttr_minutes": avg_mttr_min,
            "severity_distribution": severity_dist,
            "status_distribution": status_dist,
            "service_distribution": service_dist
        }

