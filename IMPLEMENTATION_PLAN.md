# Incident Response Panic Button System - Implementation Plan

## 1. Overview
The **Incident Response Panic Button** is a full-stack mission-critical incident management system designed for DevOps, SRE, and NOC teams. When an emergency strikes, an operator triggers the **Panic Button**, instantly raising a **P1 Critical Incident**, broadcasting multi-channel alerts to on-call engineers, and tracking the complete lifecycle with an immutable audit trail.

---

## 2. Core Workflow State Machine

```
   ┌────────────────────────────────────────────────────────┐
   │                  [ PANIC BUTTON ]                      │
   └──────────────────────────┬─────────────────────────────┘
                              │ Instant Trigger (POST /api/panic)
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │             [ P1 CRITICAL INCIDENT CREATED ]           │
   │  - Auto-generated incident key (INC-YYYY-XXXX)         │
   │  - Status: OPEN                                        │
   │  - Priority: P1_CRITICAL                               │
   └──────────────────────────┬─────────────────────────────┘
                              │
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │               [ NOTIFICATION BROADCAST ]               │
   │  - On-Call Pager / SMS simulated alert                 │
   │  - Slack / Teams Incident Channel Webhook              │
   │  - Urgent Email Dispatch                               │
   │  - Live NOC In-App Audio & Visual Flash                │
   └──────────────────────────┬─────────────────────────────┘
                              │
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │                        [ OPEN ]                        │
   │  - Timer: MTTA (Mean Time to Acknowledge) ticking      │
   │  - War room active, team alerted                       │
   └──────────────────────────┬─────────────────────────────┘
                              │ Operator Acknowledges (POST /api/incidents/<id>/acknowledge)
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │                    [ ACKNOWLEDGED ]                    │
   │  - Responder assigned                                  │
   │  - MTTA recorded                                       │
   │  - Escalation silenced, triage in progress             │
   └──────────────────────────┬─────────────────────────────┘
                              │ Incident Resolved (POST /api/incidents/<id>/resolve)
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │                      [ RESOLVED ]                      │
   │  - Root cause and resolution summary captured          │
   │  - MTTR (Mean Time to Resolve) finalized               │
   │  - Notification of resolution broadcasted              │
   └──────────────────────────┬─────────────────────────────┘
                              │
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │                   [ AUDIT HISTORY ]                    │
   │  - Immutable chronological log of all transitions     │
   │  - Actor, timestamp, previous & new state, notes       │
   │  - Compliance and post-mortem export readiness         │
   └────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack & Architecture
- **Backend**: Python 3.14, Flask 3.1, Flask-SQLAlchemy 3.1, SQLAlchemy 2.0
- **Database**: SQLite (persisted local file: `instance/incident_panic.db`)
- **Authentication & RBAC**:
  - Roles: `Admin`, `Responder`, `Reporter`
  - Token-based (`Bearer <api_token>`) & Session cookies
  - Role hierarchy: Admin > Responder > Reporter
- **Idempotency Engine**:
  - `Idempotency-Key` header prevents duplicate incident creation and duplicate notification broadcasts.
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons, Chart.js 4.4
- **Audio Synthesis**: Native Web Audio API for NOC sound alerts (no external sound binaries needed)
- **Testing**: Pytest for end-to-end API lifecycle and unit testing

---

## 4. Database Models

1. **`User`**:
   - `id`, `username`, `email`, `password_hash`, `role` (Admin/Responder/Reporter), `api_token`, `created_at`
2. **`IdempotencyRecord`**:
   - `id`, `key`, `endpoint`, `status_code`, `response_json`, `user_id`, `created_at`
3. **`Incident`**:
   - `id`, `key`, `title`, `description`, `severity`, `status`, `service_name`, `triggered_by`, `assigned_to`, `is_panic`, `user_id`, `idempotency_key`, `root_cause`, `resolution_notes`, `created_at`, `acknowledged_at`, `resolved_at`, `closed_at`
4. **`AuditLog`**:
   - `id`, `incident_id`, `user_id`, `action`, `actor`, `old_value`, `new_value`, `message`, `ip_address`, `user_agent`, `timestamp`
5. **`NotificationLog`**:
   - `id`, `incident_id`, `channel`, `recipient`, `subject`, `message`, `status`, `sent_at`
6. **`TimelineComment`**:
   - `id`, `incident_id`, `author`, `comment`, `created_at`

