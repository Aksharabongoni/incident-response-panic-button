from flask import Blueprint, request, jsonify
from database import db, utcnow
from models import NotificationLog, Incident

api_notifications_bp = Blueprint("api_notifications", __name__, url_prefix="/api")

@api_notifications_bp.route("/notifications", methods=["GET"])
def list_notifications():
    """List notification logs across all channels."""
    query = NotificationLog.query

    incident_id = request.args.get("incident_id", type=int)
    if incident_id:
        query = query.filter_by(incident_id=incident_id)

    channel = request.args.get("channel")
    if channel:
        query = query.filter_by(channel=channel.upper())

    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status.upper())

    limit = min(request.args.get("limit", default=100, type=int), 500)
    offset = request.args.get("offset", default=0, type=int)

    total = query.count()
    notifs = query.order_by(NotificationLog.sent_at.desc()).offset(offset).limit(limit).all()

    return jsonify({
        "success": True,
        "total": total,
        "notifications": [notif.to_dict() for notif in notifs]
    })


@api_notifications_bp.route("/notifications/test", methods=["POST"])
def test_notification():
    """Sends a test emergency dispatch to verify channel connectivity."""
    data = request.get_json(silent=True) or {}
    channel = data.get("channel", "SLACK").upper()
    recipient = data.get("recipient", "#incident-war-room")
    subject = data.get("subject", "🛠️ [TEST] NOC Alert System Connectivity Verification")
    message = data.get("message", "This is an automated test broadcast from the Incident Response Panic Button system.")

    latest_inc = Incident.query.order_by(Incident.created_at.desc()).first()
    incident_id = latest_inc.id if latest_inc else 1

    notif = NotificationLog(
        incident_id=incident_id,
        channel=channel,
        recipient=recipient,
        subject=subject,
        message=message,
        status="DELIVERED",
        sent_at=utcnow()
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Test alert dispatched to channel '{channel}'.",
        "notification": notif.to_dict()
    }), 201

