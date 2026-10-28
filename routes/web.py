from flask import Blueprint, render_template, abort
from database import db
from models import Incident

web_bp = Blueprint("web", __name__)

@web_bp.route("/")
def index():
    """Main NOC Dashboard with prominent Panic Button, Active Incidents, and KPIs."""
    return render_template("index.html")

@web_bp.route("/incidents/<int:incident_id>")
def incident_detail(incident_id):
    """Incident War Room with State Transition Stepper, Timeline, and Audit History."""
    incident = db.session.get(Incident, incident_id)
    if not incident:
        abort(404)
    return render_template("incident_detail.html", incident_id=incident_id)

@web_bp.route("/analytics")
def analytics():
    """Chart.js Analytics and MTTA/MTTR Performance Dashboard."""
    return render_template("analytics.html")

@web_bp.route("/audit")
def audit_view():
    """System-wide Immutable Audit Log Search and Compliance View."""
    return render_template("audit_logs.html")

@web_bp.route("/notifications")
def notifications_view():
    """System-wide Notification Center: live delivery logs and test broadcast."""
    return render_template("notifications.html")

@web_bp.route("/users")
def users_view():
    """User Management and RBAC Administration."""
    return render_template("users.html")

@web_bp.route("/login")
def login_view():
    """Dedicated Login and User Registration page."""
    return render_template("login.html")

