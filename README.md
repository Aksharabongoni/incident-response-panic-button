# 🚨 Incident Response Panic Button System

A mission-critical, full-stack incident management and operations platform designed for SRE, DevOps, and NOC (Network Operations Center) teams. The system enables immediate declaration of P1 Critical outages via an emergency Panic Button, dispatches multi-channel alerts, orchestrates incident state transitions, enforces role-based access control, supports idempotency caching, and records immutable audit histories.

---

## ⚡ Core Incident Workflow

```
   ┌────────────────────────────────────────────────────────┐
   │                  EMERGENCY PANIC BUTTON                │
   └──────────────────────────┬─────────────────────────────┘
                              │
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │             P1 CRITICAL INCIDENT DECLARED              │
   │  - Severity: P1_CRITICAL                               │
   │  - Status: OPEN                                        │
   │  - Unique Key: INC-YYYY-XXXX-SS                        │
   │  - MTTA Stopwatch Initiated                            │
   └──────────────────────────┬─────────────────────────────┘
                              │
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │             NOTIFICATION BROADCAST ENGINE              │
   │  - Pager / SMS: Primary On-Call Engineer               │
   │  - Slack: #incident-war-room Dispatch                  │
   │  - Email: leadership@ops.internal Broadcast            │
   │  - NOC Alert: In-App Live Siren & Banner Flash         │
   └──────────────────────────┬─────────────────────────────┘
                              │
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │                    OPEN (TRIAGE)                       │
   │  - Responders paged, war room links activated          │
   └──────────────────────────┬─────────────────────────────┘
                              │
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │                     ACKNOWLEDGED                       │
   │  - Claimed by Responder                                │
   │  - Latency captured: Mean Time to Acknowledge (MTTA)   │
   └──────────────────────────┬─────────────────────────────┘
                              │
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │                       RESOLVED                         │
   │  - Root Cause & Remediation Notes recorded             │
   │  - Latency captured: Mean Time to Resolve (MTTR)       │
   └──────────────────────────┬─────────────────────────────┘
                              │
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │              IMMUTABLE AUDIT TRAIL RECORD              │
   │  - Actor identity, state delta, client IP, timestamp   │
   └────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.14, Flask 3.1, Flask-SQLAlchemy 3.1, SQLAlchemy 2.0 |
| **Database** | SQLite 3 (persisted at `instance/incident_panic.db` or in-memory for testing) |
| **Authentication & RBAC** | Session cookies, `Bearer <api_token>` headers, `X-API-Key` headers |
| **Reliability** | `Idempotency-Key` and `X-Idempotency-Key` caching and replay engine |
| **Frontend UI** | HTML5, CSS3 (NOC dark theme), Vanilla JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons |
| **Visualization** | Chart.js 4.4 (Severity Doughnut, Status Pie, Service Bar Charts) |
| **Audio Alerting** | Native HTML5 Web Audio API synthesizer (works 100% offline without external audio files) |
| **Testing** | Pytest 9.1 (52 passing automated test cases) |

---

## 📂 Project Directory Structure

```
incident panic button/
├── app.py                     # Flask application factory, error handlers, and route registration
├── config.py                  # Environment configurations (Dev, Test, Prod)
├── database.py                # SQLAlchemy DB instance & naive UTC timestamp helpers
├── exceptions.py              # Domain exceptions (ValidationError, AuthenticationError, etc.)
├── models.py                  # SQLAlchemy ORM models (Incident, AuditLog, NotificationLog, User, etc.)
├── run.py                     # Local application server entrypoint
├── seed_data.py               # Database seeder with realistic incidents and audit logs
├── requirements.txt           # Project dependencies
├── routes/
│   ├── __init__.py            # Blueprint exports
│   ├── api_auth.py            # Authentication, registration, and RBAC endpoints
│   ├── api_incidents.py       # Panic button and incident lifecycle endpoints
│   ├── api_notifications.py   # Multi-channel notification query and test dispatch endpoints
│   ├── api_audit.py           # System-wide immutable audit trail endpoints
│   ├── api_metrics.py         # Operational metrics, MTTA/MTTR, seed, and reset endpoints
│   └── web.py                 # Frontend HTML template views
├── services/
│   ├── audit_service.py       # Centralized immutable audit logging
│   ├── auth_service.py        # Authentication, password hashing, and role verification
│   ├── idempotency_service.py # Idempotency-Key caching and duplicate prevention
│   ├── incident_service.py    # Core incident state engine, panic trigger, and SLA calculations
│   └── notification_service.py# Multi-channel alert dispatcher (Pager, Slack, Email, NOC)
├── static/
│   ├── css/
│   │   └── style.css          # NOC dark theme, pulse animations, hazard stripes, KPI cards
│   └── js/
│       ├── api.js             # Async API client with token and idempotency injection
│       ├── app.js             # Main dashboard controller, auto-sync, and modals
│       ├── charts.js          # Chart.js visualization wrappers
│       └── sound.js           # Web Audio API emergency siren and chime synthesizer
├── templates/
│   ├── base.html              # Base layout with navbar, role switcher, sound toggle, and modals
│   ├── index.html             # NOC Dashboard with hero Panic Button and filterable feed
│   ├── incident_detail.html   # Incident War Room with 7-step stepper, timers, and audit logs
│   ├── analytics.html         # Operational analytics, SLA compliance, and Chart.js charts
│   ├── audit_logs.html        # Searchable global audit trail with JSON export
│   ├── notifications.html     # Notification broadcast log and manual test dispatch modal
│   ├── users.html             # User administration and RBAC role assignment
│   ├── login.html             # Authentication, registration, and API token viewer
│   └── 404.html               # Custom NOC 404 error page
└── tests/
    ├── conftest.py            # Shared Pytest fixtures and authentication helpers
    ├── test_api.py            # End-to-end integration test suite
    ├── test_auth.py           # Authentication, tokens, cookies, and registration tests
    ├── test_authorization.py  # Role-based access control (RBAC) tests
    ├── test_panic_p1.py       # Panic Button and P1 Critical priority tests
    ├── test_lifecycle.py      # Incident state transitions, MTTA/MTTR, and comments tests
    ├── test_idempotency.py    # Idempotency-Key deduplication tests
    ├── test_validation.py     # Schema validation and error handling tests
    ├── test_api_endpoints.py  # REST API endpoints, filters, and HTML view rendering tests
    └── test_e2e_live.py       # Live script validating 7 workflow phases against running server
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Pip package manager

### 2. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Run the Application
Start the local server:
```bash
python run.py
```
Or via the Flask CLI:
```bash
flask --app app:create_app run --port 5000
```

The application will be live at `http://127.0.0.1:5000/`.

---

## 👥 Default Accounts & Role-Based Access Control (RBAC)

The system automatically initializes three default operational accounts upon startup:

| Role | Username | Password | Privileges |
|---|---|---|---|
| **Admin** | `admin` | `admin123` | Full privileges: Close incidents, provision users, modify roles, seed/reset data |
| **Responder** | `responder` | `responder123` | Incident operations: Acknowledge incidents, resolve incidents, post timeline notes |
| **Reporter** | `reporter` | `reporter123` | Incident discovery: Trigger Panic Button, report incidents, view dashboards |

> **Role Hierarchy**: `Admin` inherits all permissions of `Responder` and `Reporter`. `Responder` inherits all permissions of `Reporter`. `Reporter` cannot acknowledge or resolve incidents (returns `403 Forbidden`).

---

## 🖥️ Web User Interface Guide

All major sections can be navigated directly via the top navigation bar:

1. **NOC Dashboard (`/`)**:
   - Prominent **Panic Button** hero with real-time hazard glow and sound synthesizer.
   - Emergency banner highlighting active unacknowledged P1 Critical incidents.
   - 4 high-level KPI cards: Active P1s, Total Open, Mean Time to Acknowledge (MTTA), and Mean Time to Resolve (MTTR).
   - Filterable, searchable incident feed with quick-action Acknowledge and Resolve buttons.
   - Manual Incident Creation modal for standard non-panic issues (P2–P4).

2. **Incident War Room (`/incidents/<id>`)**:
   - Visual 7-stage workflow stepper (`Panic Button → P1 Critical → Notification → Open → Acknowledged → Resolved → Audit History`).
   - Live elapsed MTTA and MTTR stopwatch timer.
   - Action controls: Acknowledge, Resolve (with mandatory root cause and remediation notes), Reopen, and Close / Archive.
   - Chronological investigation timeline comments feed.
   - Multi-channel notification dispatch log.
   - Per-incident immutable audit trail with state transition diffs.

3. **Analytics & Metrics (`/analytics`)**:
   - Interactive Chart.js charts: Severity Distribution, Status Breakdown, Incidents by Service.
   - SLA Compliance Progress indicators for MTTA (< 5 minutes) and MTTR (< 30 minutes).

4. **Notification Broadcast Center (`/notifications`)**:
   - Delivery logs across all channels (Pager/SMS, Slack, Email, NOC Broadcast, Webhooks).
   - Filter by channel and delivery status (`DELIVERED`, `SENT`, `FAILED`).
   - **Send Test Alert** modal to verify channel connectivity.

5. **Audit Trail Explorer (`/audit`)**:
   - System-wide immutable record of all operational actions and state transitions.
   - Filterable by search keyword, action type (`PANIC_TRIGGERED`, `ACKNOWLEDGED`, `RESOLVED`, etc.), and actor.
   - Single-click **Export JSON** button for compliance and post-mortem reviews.

6. **User Management & RBAC (`/users`)**:
   - Account registry displaying active users, roles, and API tokens.
   - Admin controls to provision new users, change roles, and delete accounts.

7. **Auth & Profile (`/login`)**:
   - Sign in and account registration.
   - API Bearer Token viewer with one-click clipboard copy.
   - Quick role demo switchers (`Admin`, `Responder`, `Reporter`) for rapid manual testing.

---

## 📡 REST API Reference

### 1. Authentication & Users
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | Public | Register new account (`username`, `email`, `password`, `role`) |
| `POST` | `/api/auth/login` | Public | Authenticate credentials and receive API token |
| `POST` | `/api/auth/logout` | Session | Clear session cookies |
| `GET` | `/api/auth/me` | Optional | Inspect authenticated profile or guest state |
| `GET` | `/api/auth/users` | Admin | List all registered user accounts and API tokens |
| `POST` | `/api/auth/users` | Admin | Provision a new user account |
| `PATCH` | `/api/auth/users/<id>/role` | Admin | Update user's RBAC role |
| `DELETE` | `/api/auth/users/<id>` | Admin | Delete a user account |
| `POST` | `/api/auth/switch-role` | Public | Switch current active session user for testing |

### 2. Panic Button & Incidents
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/panic` | Any | **Trigger Emergency Panic Button**: Declares P1 Critical incident, sends alerts, logs audit record |
| `GET` | `/api/incidents` | Any | List incidents with optional filters (`?status=OPEN&severity=P1_CRITICAL&q=db`) |
| `POST` | `/api/incidents` | Any | Manually create an incident with custom severity |
| `GET` | `/api/incidents/<id>` | Any | Get incident details, comments, notifications, and audit log |
| `POST` | `/api/incidents/<id>/acknowledge` | Responder+ | Transition incident from `OPEN` to `ACKNOWLEDGED`, captures MTTA |
| `POST` | `/api/incidents/<id>/resolve` | Responder+ | Transition to `RESOLVED` with `root_cause` & `resolution_notes`, captures MTTR |
| `POST` | `/api/incidents/<id>/reopen` | Responder+ | Reopen a `RESOLVED` incident back to `OPEN` |
| `POST` | `/api/incidents/<id>/close` | Admin+ | Close / archive a `RESOLVED` incident |
| `POST` | `/api/incidents/<id>/comments` | Responder+ | Add timeline investigation comment |
| `POST` | `/api/incidents/<id>/assign` | Responder+ | Reassign incident responder |
| `GET` | `/api/incidents/<id>/audit` | Any | Retrieve immutable audit records for specific incident |

### 3. Notifications & Audit
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/notifications` | Any | Query notification logs (`?channel=SLACK&status=DELIVERED`) |
| `POST` | `/api/notifications/test` | Any | Dispatch manual test notification alert |
| `GET` | `/api/audit-logs` | Any | Query global audit trail (`?action=PANIC_TRIGGERED&actor=Admin`) |
| `GET` | `/api/metrics` | Any | Retrieve MTTA/MTTR, active P1 count, and incident stats |
| `POST` | `/api/seed` | Admin | Seed database with sample demo incidents |
| `POST` | `/api/reset` | Admin | Reset and purge all incident and audit data |

---

## 🔒 Idempotency Safety

Network drops and retry policies can cause duplicate POST requests. The system prevents duplicate incident creation through idempotency caching:

```bash
curl -X POST http://127.0.0.1:5000/api/panic \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: e9a6c760-4961-4d32-9cb7-68b57732d8ff" \
  -d '{
    "title": "Database Outage",
    "service_name": "PostgreSQL Primary"
  }'
```

- When an `Idempotency-Key` (or `X-Idempotency-Key`) header is provided, the API caches the HTTP response code and response JSON in the `idempotency_records` table.
- Subsequent requests with the same key immediately return the cached response without creating duplicate incident records or re-dispatching alert storms.

---

## 🧪 Automated Testing Suite

The repository contains an automated test suite across 8 modules covering 52 test cases:

```powershell
python -m pytest -v
```

### Test Suite Breakdown:

| Test File | Test Count | Coverage Scope |
|---|---|---|
| [`tests/test_panic_p1.py`](file:///c:/Users/B.AKSHARA/OneDrive/Documents/incident%20panic%20button/tests/test_panic_p1.py) | 4 | Panic Button trigger, P1 Critical priority, multi-channel alerting, audit log generation |
| [`tests/test_lifecycle.py`](file:///c:/Users/B.AKSHARA/OneDrive/Documents/incident%20panic%20button/tests/test_lifecycle.py) | 5 | State transitions (`OPEN → ACKNOWLEDGED → RESOLVED → CLOSED`), MTTA/MTTR, reopening, comments |
| [`tests/test_idempotency.py`](file:///c:/Users/B.AKSHARA/OneDrive/Documents/incident%20panic%20button/tests/test_idempotency.py) | 3 | Deduplication via `Idempotency-Key` and `X-Idempotency-Key`, replay caching |
| [`tests/test_auth.py`](file:///c:/Users/B.AKSHARA/OneDrive/Documents/incident%20panic%20button/tests/test_auth.py) | 11 | Login, password hashing, registration, duplicate checks, Bearer token, X-API-Key, logout |
| [`tests/test_authorization.py`](file:///c:/Users/B.AKSHARA/OneDrive/Documents/incident%20panic%20button/tests/test_authorization.py) | 7 | RBAC permission matrix: Reporter forbidden from ack/resolve; Responder/Admin permitted |
| [`tests/test_validation.py`](file:///c:/Users/B.AKSHARA/OneDrive/Documents/incident%20panic%20button/tests/test_validation.py) | 10 | Input lengths, required title/service, root cause requirement, invalid roles, 404 handling |
| [`tests/test_api_endpoints.py`](file:///c:/Users/B.AKSHARA/OneDrive/Documents/incident%20panic%20button/tests/test_api_endpoints.py) | 7 | Incident filters, notification query, test alert, audit filters, metrics, seed/reset, web views |
| [`tests/test_api.py`](file:///c:/Users/B.AKSHARA/OneDrive/Documents/incident%20panic%20button/tests/test_api.py) | 6 | End-to-end integration and workflow regression suite |
| **Total** | **52 Passing** | **100% Test Success Rate** |

### Live Server Workflow Validation:
Run the live integration script against the active server:
```powershell
python tests/test_e2e_live.py
```
This script exercises all 7 phases against the running Flask application:
1. Authenticates session as Admin
2. Activates Panic Button (`POST /api/panic`)
3. Verifies multi-channel notifications (Pager/SMS, Slack, Email, NOC Broadcast)
4. Acknowledges incident and records MTTA
5. Posts timeline investigation comment
6. Resolves incident with root cause and records MTTR
7. Validates chronological immutable audit records
