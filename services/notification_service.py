import requests
from flask import current_app
from database import db, utcnow
from models import NotificationLog
from services.audit_service import AuditService

class NotificationService:
    @staticmethod
    def dispatch_incident_notifications(incident, event_type="TRIGGERED", extra_info=""):
        """
        Dispatches multi-channel notifications (Pager, Slack, Email, NOC Broadcast, Webhook)
        for an incident event.
        """
        roster = current_app.config.get("ON_CALL_ROSTER", [])
        primary_responder = roster[0] if roster else {"name": "Primary On-Call", "phone": "+1-555-0100", "email": "oncall@ops.internal"}
        
        dispatched_logs = []

        if event_type == "TRIGGERED":
            subject = f"🚨 [P1 CRITICAL] Incident {incident.key}: {incident.title}"
            base_msg = (
                f"EMERGENCY ALERT: P1 Critical incident {incident.key} triggered on service '{incident.service_name}'.\n"
                f"Description: {incident.description or 'No description provided.'}\n"
                f"Triggered by: {incident.triggered_by} at {incident.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}.\n"
                f"Immediate response required."
            )
            
            # 1. SMS / Pager Alert to Primary Responder
            sms_log = NotificationLog(
                incident_id=incident.id,
                channel="PAGER_SMS",
                recipient=f"{primary_responder['name']} ({primary_responder['phone']})",
                subject=f"URGENT PAGER: {incident.key}",
                message=f"[P1 CRITICAL] {incident.key} on {incident.service_name}: {incident.title}. Respond immediately.",
                status="DELIVERED",
                sent_at=utcnow()
            )
            db.session.add(sms_log)
            dispatched_logs.append(sms_log)

            # 2. Slack / Chat Ops Broadcast
            slack_log = NotificationLog(
                incident_id=incident.id,
                channel="SLACK",
                recipient="#incident-war-room",
                subject=subject,
                message=(
                    f":rotating_light: *[P1 CRITICAL INCIDENT DECLARED]*\n"
                    f"*Key*: `{incident.key}`\n"
                    f"*Service*: *{incident.service_name}*\n"
                    f"*Title*: {incident.title}\n"
                    f"*Triggered By*: {incident.triggered_by}\n"
                    f"*Status*: `{incident.status}`\n"
                    f"War room channel initiated. Responders please acknowledge ASAP."
                ),
                status="DELIVERED",
                sent_at=utcnow()
            )
            db.session.add(slack_log)
            dispatched_logs.append(slack_log)

            # 3. Leadership & Team Email Broadcast
            email_log = NotificationLog(
                incident_id=incident.id,
                channel="EMAIL",
                recipient="incident-commander-team@ops.internal, leadership@ops.internal",
                subject=subject,
                message=base_msg,
                status="DELIVERED",
                sent_at=utcnow()
            )
            db.session.add(email_log)
            dispatched_logs.append(email_log)

            # 4. NOC In-App Emergency Broadcast
            noc_log = NotificationLog(
                incident_id=incident.id,
                channel="NOC_BROADCAST",
                recipient="Global NOC Operations Dashboard",
                subject=f"NOC FLASH: {incident.key}",
                message=f"P1 Critical incident declared for service: {incident.service_name}.",
                status="DELIVERED",
                sent_at=utcnow()
            )
            db.session.add(noc_log)
            dispatched_logs.append(noc_log)

        elif event_type == "ACKNOWLEDGED":
            subject = f"👤 [ACKNOWLEDGED] Incident {incident.key}: {incident.title}"
            slack_log = NotificationLog(
                incident_id=incident.id,
                channel="SLACK",
                recipient="#incident-war-room",
                subject=subject,
                message=f":eyes: Incident `{incident.key}` acknowledged by *{incident.assigned_to or 'Operator'}*. Investigation underway.",
                status="DELIVERED",
                sent_at=utcnow()
            )
            db.session.add(slack_log)
            dispatched_logs.append(slack_log)

        elif event_type == "RESOLVED":
            subject = f"✅ [RESOLVED] Incident {incident.key}: {incident.title}"
            msg = (
                f"Incident {incident.key} on {incident.service_name} has been successfully RESOLVED.\n"
                f"Root Cause: {incident.root_cause or 'N/A'}\n"
                f"Resolution Notes: {incident.resolution_notes or 'N/A'}\n"
                f"Time to Resolve: {incident.mttr_seconds}s"
            )
            slack_log = NotificationLog(
                incident_id=incident.id,
                channel="SLACK",
                recipient="#incident-war-room",
                subject=subject,
                message=(
                    f":white_check_mark: *Incident `{incident.key}` RESOLVED*\n"
                    f"*Root Cause*: {incident.root_cause or 'Under review'}\n"
                    f"*Resolution*: {incident.resolution_notes or 'Resolved'}\n"
                    f"*Total MTTR*: {incident.mttr_seconds}s"
                ),
                status="DELIVERED",
                sent_at=utcnow()
            )
            db.session.add(slack_log)
            dispatched_logs.append(slack_log)

            email_log = NotificationLog(
                incident_id=incident.id,
                channel="EMAIL",
                recipient="incident-commander-team@ops.internal, leadership@ops.internal",
                subject=subject,
                message=msg,
                status="DELIVERED",
                sent_at=utcnow()
            )
            db.session.add(email_log)
            dispatched_logs.append(email_log)

        # 5. External Webhook (if configured)
        webhook_url = current_app.config.get("NOTIFICATION_WEBHOOK_URL")
        if webhook_url:
            try:
                payload = {
                    "event": event_type,
                    "incident": incident.to_dict(),
                    "timestamp": utcnow().isoformat()
                }
                res = requests.post(webhook_url, json=payload, timeout=3)
                webhook_status = "DELIVERED" if res.status_code < 400 else "FAILED"
            except Exception:
                webhook_status = "FAILED"
            
            wh_log = NotificationLog(
                incident_id=incident.id,
                channel="WEBHOOK",
                recipient=webhook_url,
                subject=f"Webhook Alert: {incident.key}",
                message=f"Dispatched event {event_type} to external webhook",
                status=webhook_status,
                sent_at=utcnow()
            )
            db.session.add(wh_log)
            dispatched_logs.append(wh_log)

        db.session.flush()

        channels_str = ", ".join(set(log.channel for log in dispatched_logs))
        AuditService.record_audit(
            incident_id=incident.id,
            action="NOTIFICATIONS_DISPATCHED",
            actor="NotificationEngine",
            old_value=None,
            new_value=f"Channels: {channels_str}",
            message=f"Dispatched {len(dispatched_logs)} notification(s) across channels: {channels_str} for event '{event_type}'."
        )

        return dispatched_logs

