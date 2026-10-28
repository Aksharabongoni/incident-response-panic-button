import json
from flask import request
from database import db, utcnow
from models import IdempotencyRecord

class IdempotencyService:
    @staticmethod
    def extract_key_from_request():
        """Extracts idempotency key from headers (Idempotency-Key or X-Idempotency-Key) or JSON body."""
        return (
            request.headers.get("Idempotency-Key") or
            request.headers.get("X-Idempotency-Key") or
            (request.get_json(silent=True) or {}).get("idempotency_key")
        )

    @staticmethod
    def get_cached_response(key, endpoint):
        """
        Retrieves a previously stored response for an idempotency key and endpoint.
        Returns (status_code, json_dict) or None if not found.
        """
        if not key:
            return None
        record = IdempotencyRecord.query.filter_by(key=str(key), endpoint=str(endpoint)).first()
        if record:
            try:
                body = json.loads(record.response_json)
            except Exception:
                body = {"message": record.response_json}
            return record.status_code, body
        return None

    @staticmethod
    def record_response(key, endpoint, status_code, response_data, user_id=None):
        """
        Saves the response payload and status code for future duplicate requests.
        """
        if not key:
            return None
        # Check if already saved
        existing = IdempotencyRecord.query.filter_by(key=str(key), endpoint=str(endpoint)).first()
        if existing:
            return existing

        record = IdempotencyRecord(
            key=str(key),
            endpoint=str(endpoint),
            status_code=status_code,
            response_json=json.dumps(response_data),
            user_id=user_id,
            created_at=utcnow()
        )
        try:
            db.session.add(record)
            db.session.commit()
            return record
        except Exception:
            db.session.rollback()
            return None

