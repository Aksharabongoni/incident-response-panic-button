from flask import Blueprint, jsonify
from services.incident_service import IncidentService
from database import db
from models import Incident, AuditLog, NotificationLog, TimelineComment, UserRole
from services.auth_service import role_required

api_metrics_bp = Blueprint("api_metrics", __name__, url_prefix="/api")

@api_metrics_bp.route("/metrics", methods=["GET"])
def get_metrics():
    """Returns MTTA, MTTR, counts, and categorical distributions for Chart.js."""
    try:
        metrics = IncidentService.get_metrics()
        return jsonify({
            "success": True,
            "metrics": metrics
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_metrics_bp.route("/seed", methods=["POST"])
@role_required(UserRole.ADMIN)
def seed_data():
    """Populates realistic demo incidents across different states and services."""
    from seed_data import populate_sample_data
    try:
        count = populate_sample_data()
        return jsonify({
            "success": True,
            "message": f"Successfully seeded {count} incidents with audit trails and notifications."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_metrics_bp.route("/reset", methods=["POST"])
@role_required(UserRole.ADMIN)
def reset_data():
    """Resets all incidents, audit logs, and notification logs."""
    try:
        TimelineComment.query.delete()
        NotificationLog.query.delete()
        AuditLog.query.delete()
        Incident.query.delete()
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "All incident and audit records have been cleared."
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

