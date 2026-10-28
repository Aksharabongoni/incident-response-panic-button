from flask import Blueprint, request, jsonify, g
from database import db
from models import Incident, IncidentSeverity, IncidentStatus, UserRole
from services.incident_service import IncidentService
from services.audit_service import AuditService
from services.auth_service import optional_auth, role_required
from services.idempotency_service import IdempotencyService
from exceptions import AppException, ValidationError, NotFoundError

api_incidents_bp = Blueprint("api_incidents", __name__, url_prefix="/api")

@api_incidents_bp.route("/panic", methods=["POST"])
@optional_auth
def panic():
    """
    PANIC BUTTON ENDPOINT:
    Instantly triggers a P1 Critical Incident, dispatches notifications,
    creates audit history entry.
    Supports Idempotency-Key header for safe network retries.
    """
    idempotency_key = IdempotencyService.extract_key_from_request()
    endpoint = "/api/panic"

    if idempotency_key:
        cached = IdempotencyService.get_cached_response(idempotency_key, endpoint)
        if cached:
            status_code, body = cached
            return jsonify(body), status_code

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    description = data.get("description")
    service_name = data.get("service_name")
    triggered_by = data.get("triggered_by")
    assigned_to = data.get("assigned_to")

    user = getattr(g, "current_user", None)

    try:
        incident = IncidentService.trigger_panic(
            title=title,
            description=description,
            service_name=service_name,
            triggered_by=triggered_by,
            assigned_to=assigned_to,
            user=user,
            idempotency_key=idempotency_key
        )
        response_payload = {
            "success": True,
            "message": f"🚨 PANIC TRIGGERED: P1 Critical Incident {incident.key} created.",
            "incident": incident.to_dict(include_details=True)
        }

        if idempotency_key:
            IdempotencyService.record_response(
                idempotency_key, endpoint, 201, response_payload, user_id=user.id if user else None
            )

        return jsonify(response_payload), 201
    except AppException as ae:
        return jsonify(ae.to_dict()), ae.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "code": "INTERNAL_ERROR"}), 500


@api_incidents_bp.route("/incidents", methods=["GET"])
@optional_auth
def list_incidents():
    """List all incidents with optional filtering."""
    query = Incident.query

    status = request.args.get("status")
    if status and status in IncidentStatus.ALL:
        query = query.filter_by(status=status)

    severity = request.args.get("severity")
    if severity and severity in IncidentSeverity.ALL:
        query = query.filter_by(severity=severity)

    service = request.args.get("service")
    if service:
        query = query.filter(Incident.service_name.ilike(f"%{service}%"))

    search = request.args.get("q")
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Incident.key.ilike(search_filter)) |
            (Incident.title.ilike(search_filter)) |
            (Incident.description.ilike(search_filter)) |
            (Incident.service_name.ilike(search_filter))
        )

    incidents = query.order_by(Incident.created_at.desc()).all()

    return jsonify({
        "success": True,
        "count": len(incidents),
        "incidents": [inc.to_dict() for inc in incidents]
    })


@api_incidents_bp.route("/incidents", methods=["POST"])
@optional_auth
def create_incident():
    """Manual incident creation endpoint with idempotency support."""
    idempotency_key = IdempotencyService.extract_key_from_request()
    endpoint = "/api/incidents"

    if idempotency_key:
        cached = IdempotencyService.get_cached_response(idempotency_key, endpoint)
        if cached:
            status_code, body = cached
            return jsonify(body), status_code

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    description = data.get("description", "")
    severity = data.get("severity", IncidentSeverity.P1_CRITICAL)
    service_name = data.get("service_name", "Core Infrastructure")
    triggered_by = data.get("triggered_by")
    assigned_to = data.get("assigned_to")

    user = getattr(g, "current_user", None)

    try:
        incident = IncidentService.create_incident(
            title=title,
            description=description,
            severity=severity,
            service_name=service_name,
            triggered_by=triggered_by,
            assigned_to=assigned_to,
            user=user,
            idempotency_key=idempotency_key
        )
        response_payload = {
            "success": True,
            "message": f"Incident {incident.key} created successfully.",
            "incident": incident.to_dict(include_details=True)
        }

        if idempotency_key:
            IdempotencyService.record_response(
                idempotency_key, endpoint, 201, response_payload, user_id=user.id if user else None
            )

        return jsonify(response_payload), 201
    except AppException as ae:
        return jsonify(ae.to_dict()), ae.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "code": "INTERNAL_ERROR"}), 500


@api_incidents_bp.route("/incidents/<int:incident_id>", methods=["GET"])
@optional_auth
def get_incident(incident_id):
    """Get single incident details with audit history and notifications."""
    incident = db.session.get(Incident, incident_id)
    if not incident:
        return jsonify({"success": False, "error": f"Incident {incident_id} not found", "code": "NOT_FOUND"}), 404
    return jsonify({
        "success": True,
        "incident": incident.to_dict(include_details=True)
    })


@api_incidents_bp.route("/incidents/<int:incident_id>/acknowledge", methods=["POST"])
@optional_auth
def acknowledge_incident(incident_id):
    """Acknowledge an open incident (Requires Responder or Admin role if logged in)."""
    data = request.get_json(silent=True) or {}
    actor = data.get("actor")
    assigned_to = data.get("assigned_to")
    user = getattr(g, "current_user", None)

    try:
        incident = IncidentService.acknowledge_incident(
            incident_id=incident_id,
            actor=actor,
            assigned_to=assigned_to,
            user=user
        )
        return jsonify({
            "success": True,
            "message": f"Incident {incident.key} acknowledged.",
            "incident": incident.to_dict(include_details=True)
        })
    except AppException as ae:
        return jsonify(ae.to_dict()), ae.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "code": "INTERNAL_ERROR"}), 500


@api_incidents_bp.route("/incidents/<int:incident_id>/resolve", methods=["POST"])
@optional_auth
def resolve_incident(incident_id):
    """Resolve an incident, providing root cause and resolution notes."""
    data = request.get_json(silent=True) or {}
    actor = data.get("actor")
    root_cause = data.get("root_cause")
    resolution_notes = data.get("resolution_notes")
    user = getattr(g, "current_user", None)

    try:
        incident = IncidentService.resolve_incident(
            incident_id=incident_id,
            actor=actor,
            root_cause=root_cause,
            resolution_notes=resolution_notes,
            user=user
        )
        return jsonify({
            "success": True,
            "message": f"Incident {incident.key} marked as RESOLVED.",
            "incident": incident.to_dict(include_details=True)
        })
    except AppException as ae:
        return jsonify(ae.to_dict()), ae.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "code": "INTERNAL_ERROR"}), 500


@api_incidents_bp.route("/incidents/<int:incident_id>/close", methods=["POST"])
@optional_auth
def close_incident(incident_id):
    """Close an incident after post-mortem."""
    data = request.get_json(silent=True) or {}
    actor = data.get("actor")
    user = getattr(g, "current_user", None)

    try:
        incident = IncidentService.close_incident(incident_id=incident_id, actor=actor, user=user)
        return jsonify({
            "success": True,
            "message": f"Incident {incident.key} formally closed.",
            "incident": incident.to_dict(include_details=True)
        })
    except AppException as ae:
        return jsonify(ae.to_dict()), ae.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "code": "INTERNAL_ERROR"}), 500


@api_incidents_bp.route("/incidents/<int:incident_id>/reopen", methods=["POST"])
@optional_auth
def reopen_incident(incident_id):
    """Reopen a resolved incident if an issue re-emerges."""
    data = request.get_json(silent=True) or {}
    actor = data.get("actor")
    reason = data.get("reason")
    user = getattr(g, "current_user", None)

    try:
        incident = IncidentService.reopen_incident(
            incident_id=incident_id,
            actor=actor,
            reason=reason,
            user=user
        )
        return jsonify({
            "success": True,
            "message": f"Incident {incident.key} has been REOPENED.",
            "incident": incident.to_dict(include_details=True)
        })
    except AppException as ae:
        return jsonify(ae.to_dict()), ae.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "code": "INTERNAL_ERROR"}), 500


@api_incidents_bp.route("/incidents/<int:incident_id>/status", methods=["PATCH"])
def update_status(incident_id):
    """Transition incident status via PATCH."""
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    if new_status == IncidentStatus.ACKNOWLEDGED:
        return acknowledge_incident(incident_id)
    elif new_status == IncidentStatus.RESOLVED:
        return resolve_incident(incident_id)
    elif new_status == IncidentStatus.CLOSED:
        return close_incident(incident_id)
    elif new_status == IncidentStatus.OPEN:
        return reopen_incident(incident_id)
    else:
        return jsonify({"success": False, "error": f"Invalid or unsupported status transition to '{new_status}'", "code": "INVALID_STATUS"}), 400


@api_incidents_bp.route("/incidents/<int:incident_id>/comments", methods=["POST"])
@optional_auth
def add_comment(incident_id):
    """Add a timeline comment/update."""
    data = request.get_json(silent=True) or {}
    author = data.get("author")
    comment_text = data.get("comment")
    user = getattr(g, "current_user", None)

    try:
        comment = IncidentService.add_comment(
            incident_id=incident_id,
            author=author,
            comment_text=comment_text,
            user=user
        )
        return jsonify({
            "success": True,
            "message": "Timeline comment added.",
            "comment": comment.to_dict()
        }), 201
    except AppException as ae:
        return jsonify(ae.to_dict()), ae.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "code": "INTERNAL_ERROR"}), 500


@api_incidents_bp.route("/incidents/<int:incident_id>/assign", methods=["POST"])
@optional_auth
def assign_incident(incident_id):
    """Assign or reassign an incident."""
    data = request.get_json(silent=True) or {}
    actor = data.get("actor")
    assigned_to = data.get("assigned_to")
    user = getattr(g, "current_user", None)

    try:
        incident = IncidentService.assign_incident(
            incident_id=incident_id,
            actor=actor,
            assigned_to=assigned_to,
            user=user
        )
        return jsonify({
            "success": True,
            "message": f"Incident assigned to {assigned_to}.",
            "incident": incident.to_dict()
        })
    except AppException as ae:
        return jsonify(ae.to_dict()), ae.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "code": "INTERNAL_ERROR"}), 500


@api_incidents_bp.route("/incidents/<int:incident_id>/audit", methods=["GET"])
def get_incident_audit(incident_id):
    """Retrieve full audit history for a specific incident."""
    incident = db.session.get(Incident, incident_id)
    if not incident:
        return jsonify({"success": False, "error": "Incident not found", "code": "NOT_FOUND"}), 404
    logs = AuditService.get_audit_trail_for_incident(incident_id)
    return jsonify({
        "success": True,
        "incident_id": incident_id,
        "count": len(logs),
        "audit_logs": [log.to_dict() for log in logs]
    })

