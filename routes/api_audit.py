from flask import Blueprint, request, jsonify
from database import db
from models import AuditLog

api_audit_bp = Blueprint("api_audit", __name__, url_prefix="/api")

@api_audit_bp.route("/audit-logs", methods=["GET"])
def list_audit_logs():
    """Returns global immutable audit logs across all incidents."""
    query = AuditLog.query

    incident_id = request.args.get("incident_id", type=int)
    if incident_id:
        query = query.filter_by(incident_id=incident_id)

    action = request.args.get("action")
    if action:
        query = query.filter_by(action=action)

    actor = request.args.get("actor")
    if actor:
        query = query.filter(AuditLog.actor.ilike(f"%{actor}%"))

    search = request.args.get("q")
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (AuditLog.message.ilike(search_filter)) |
            (AuditLog.action.ilike(search_filter)) |
            (AuditLog.actor.ilike(search_filter))
        )

    limit = min(request.args.get("limit", default=100, type=int), 500)
    offset = request.args.get("offset", default=0, type=int)

    total = query.count()
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return jsonify({
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "audit_logs": [log.to_dict() for log in logs]
    })


@api_audit_bp.route("/audit-logs/<int:log_id>", methods=["GET"])
def get_audit_log(log_id):
    """Retrieve single audit log entry."""
    log = db.session.get(AuditLog, log_id)
    if not log:
        return jsonify({"success": False, "error": "Audit log not found"}), 404
    return jsonify({
        "success": True,
        "audit_log": log.to_dict()
    })

