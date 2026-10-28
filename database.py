from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utcnow():
    """Returns offset-naive UTC datetime for seamless SQLite storage and arithmetic."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def ensure_naive_utc(dt):
    """Ensures datetime is offset-naive UTC so subtractions never fail."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

