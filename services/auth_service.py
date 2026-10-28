from functools import wraps
from flask import request, session, g
from database import db, utcnow
from models import User, UserRole
from exceptions import AuthenticationError, AuthorizationError, ValidationError, ConflictError

class AuthService:
    ROLE_HIERARCHY = {
        UserRole.ADMIN: [UserRole.ADMIN, UserRole.RESPONDER, UserRole.REPORTER],
        UserRole.RESPONDER: [UserRole.RESPONDER, UserRole.REPORTER],
        UserRole.REPORTER: [UserRole.REPORTER]
    }

    @classmethod
    def register_user(cls, username, email, password, role=UserRole.REPORTER):
        """Creates a new user account with hashed password and API token."""
        username = (username or "").strip()
        email = (email or "").strip().lower()

        if not username or len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
        if not email or "@" not in email:
            raise ValidationError("A valid email address is required.")
        if not password or len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long.")
        if role and role not in UserRole.ALL:
            raise ValidationError(f"Invalid role '{role}'. Must be one of: {UserRole.ALL}")
        if not role:
            role = UserRole.REPORTER

        if User.query.filter((User.username == username) | (User.email == email)).first():
            raise ConflictError("A user with this username or email already exists.")

        user = User(
            username=username,
            email=email,
            role=role,
            created_at=utcnow()
        )
        user.set_password(password)
        user.generate_token()

        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def authenticate(cls, username_or_email, password):
        """Validates credentials and returns authenticated User."""
        identifier = (username_or_email or "").strip()
        if not identifier or not password:
            raise AuthenticationError("Username/email and password are required.")

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if not user or not user.check_password(password):
            raise AuthenticationError("Invalid username or password.")

        if not user.api_token:
            user.generate_token()
            db.session.commit()

        return user

    @classmethod
    def get_user_from_request(cls):
        """
        Extracts current authenticated user from:
        1. Bearer Token (Authorization: Bearer <token>)
        2. X-API-Key Header (X-API-Key: <token>)
        3. Flask Session (session['user_id'])
        """
        # 1. Bearer Token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            user = User.query.filter_by(api_token=token).first()
            if user:
                return user

        # 2. X-API-Key
        api_key = request.headers.get("X-API-Key", "").strip()
        if api_key:
            user = User.query.filter_by(api_token=api_key).first()
            if user:
                return user

        # 3. Session cookie
        user_id = session.get("user_id")
        if user_id:
            user = db.session.get(User, user_id)
            if user:
                return user

        return None

    @classmethod
    def user_has_role(cls, user_role, target_role):
        """Checks role hierarchy."""
        allowed = cls.ROLE_HIERARCHY.get(user_role, [])
        return target_role in allowed

    @classmethod
    def ensure_default_users(cls):
        """Seeds default Admin, Responder, and Reporter users if database is empty."""
        defaults = [
            ("admin", "admin@ops.internal", "admin123", UserRole.ADMIN),
            ("responder", "responder@ops.internal", "responder123", UserRole.RESPONDER),
            ("reporter", "reporter@ops.internal", "reporter123", UserRole.REPORTER),
        ]
        created = []
        for uname, email, pwd, role in defaults:
            existing = User.query.filter_by(username=uname).first()
            if not existing:
                u = User(username=uname, email=email, role=role, created_at=utcnow())
                u.set_password(pwd)
                u.generate_token()
                db.session.add(u)
                created.append(u)
        if created:
            db.session.commit()
        return created


def auth_required(f):
    """Decorator requiring a valid authenticated user."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = AuthService.get_user_from_request()
        if not user:
            raise AuthenticationError("Authentication required. Provide Bearer token or log in.")
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def role_required(*allowed_roles):
    """Decorator requiring one of the allowed roles (respecting hierarchy)."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = AuthService.get_user_from_request()
            if not user:
                raise AuthenticationError("Authentication required.")
            
            # Check if user has any of the allowed roles
            has_permission = any(AuthService.user_has_role(user.role, r) for r in allowed_roles)
            if not has_permission:
                allowed_str = ", ".join(allowed_roles)
                raise AuthorizationError(f"Access denied. Required role: '{allowed_str}'. Your role: '{user.role}'.")
            
            g.current_user = user
            return f(*args, **kwargs)
        return decorated
    return decorator


def optional_auth(f):
    """Populates g.current_user if token/session is present, but doesn't block."""
    @wraps(f)
    def decorated(*args, **kwargs):
        g.current_user = AuthService.get_user_from_request()
        return f(*args, **kwargs)
    return decorated

