import os
import tempfile

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

if os.environ.get("VERCEL"):
    DATABASE_PATH = os.path.join(tempfile.gettempdir(), "incident_panic.db")
else:
    DATABASE_PATH = os.path.join(BASE_DIR, "instance", "incident_panic.db")

DATABASE_URL = f"sqlite:///{DATABASE_PATH.replace(os.sep, '/')}"

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "panic-button-super-secret-key-2026")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        DATABASE_URL
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    NOTIFICATION_WEBHOOK_URL = os.environ.get("NOTIFICATION_WEBHOOK_URL", "")
    ON_CALL_ROSTER = [
        {"name": "Sarah Connor", "role": "Primary Incident Commander", "phone": "+1-555-0199", "email": "s.connor@ops.internal"},
        {"name": "Alex Murphy", "role": "Lead DevOps SRE", "phone": "+1-555-0144", "email": "a.murphy@ops.internal"},
        {"name": "Neo Anderson", "role": "Database Architect", "phone": "+1-555-0177", "email": "n.anderson@ops.internal"},
        {"name": "Ellen Ripley", "role": "Security Response Lead", "phone": "+1-555-0122", "email": "e.ripley@ops.internal"}
    ]

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

