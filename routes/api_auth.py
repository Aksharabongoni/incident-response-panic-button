from flask import Blueprint, request, jsonify, session, g
from database import db
from services.auth_service import AuthService, auth_required, role_required, optional_auth
from models import User, UserRole
from exceptions import ValidationError, NotFoundError, ConflictError

api_auth_bp = Blueprint("api_auth", __name__, url_prefix="/api/auth")

@api_auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account."""
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", UserRole.REPORTER)

    user = AuthService.register_user(username, email, password, role)
    session["user_id"] = user.id

    return jsonify({
        "success": True,
        "message": f"User '{user.username}' successfully registered with role '{user.role}'.",
        "user": user.to_dict(include_token=True)
    }), 201


@api_auth_bp.route("/login", methods=["POST"])
def login():
    """Log in with username or email and password."""
    data = request.get_json(silent=True) or {}
    username = data.get("username") or data.get("email")
    password = data.get("password")

    user = AuthService.authenticate(username, password)
    session["user_id"] = user.id

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user.username}.",
        "user": user.to_dict(include_token=True)
    })


@api_auth_bp.route("/logout", methods=["POST"])
def logout():
    """Log out current user."""
    session.pop("user_id", None)
    return jsonify({"success": True, "message": "Successfully logged out."})


@api_auth_bp.route("/me", methods=["GET"])
@optional_auth
def get_me():
    """Returns currently authenticated user profile."""
    if not g.current_user:
        return jsonify({
            "success": True,
            "authenticated": False,
            "user": {
                "username": "Anonymous Guest",
                "role": UserRole.REPORTER,
                "is_guest": True
            }
        })

    return jsonify({
        "success": True,
        "authenticated": True,
        "user": g.current_user.to_dict(include_token=True)
    })


@api_auth_bp.route("/users", methods=["GET"])
@role_required(UserRole.ADMIN)
def list_users():
    """List all registered users (Admin only)."""
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({
        "success": True,
        "users": [u.to_dict(include_token=True) for u in users]
    })


@api_auth_bp.route("/users", methods=["POST"])
@role_required(UserRole.ADMIN)
def create_user():
    """Create a new user directly (Admin only)."""
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password") or "password123"
    role = data.get("role", UserRole.REPORTER)

    user = AuthService.register_user(username, email, password, role)
    return jsonify({
        "success": True,
        "message": f"User '{user.username}' created with role '{user.role}'.",
        "user": user.to_dict(include_token=True)
    }), 201


@api_auth_bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@role_required(UserRole.ADMIN)
def update_user_role(user_id):
    """Change a user's role (Admin only)."""
    data = request.get_json(silent=True) or {}
    new_role = data.get("role")
    if new_role not in UserRole.ALL:
        raise ValidationError(f"Invalid role '{new_role}'. Must be one of: {UserRole.ALL}")

    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError("User not found.")

    user.role = new_role
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Updated role for '{user.username}' to '{user.role}'.",
        "user": user.to_dict()
    })


@api_auth_bp.route("/users/<int:user_id>", methods=["DELETE"])
@role_required(UserRole.ADMIN)
def delete_user(user_id):
    """Delete a user (Admin only)."""
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError("User not found.")

    if g.current_user and g.current_user.id == user.id:
        raise ValidationError("Cannot delete your own active user account.")

    username = user.username
    db.session.delete(user)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"User '{username}' was deleted."
    })


@api_auth_bp.route("/switch-role", methods=["POST"])
def switch_demo_role():
    """
    Convenience endpoint for local testing:
    Switches active session to default Admin, Responder, or Reporter user.
    """
    data = request.get_json(silent=True) or {}
    target_role = data.get("role", UserRole.ADMIN)
    if target_role not in UserRole.ALL:
        raise ValidationError(f"Invalid role '{target_role}'. Must be one of: {UserRole.ALL}")

    AuthService.ensure_default_users()
    user = User.query.filter_by(role=target_role).first()
    if not user:
        user = AuthService.register_user(
            username=target_role.lower(),
            email=f"{target_role.lower()}@ops.internal",
            password=f"{target_role.lower()}123",
            role=target_role
        )

    session["user_id"] = user.id

    return jsonify({
        "success": True,
        "message": f"Switched to user '{user.username}' with role '{user.role}'.",
        "user": user.to_dict(include_token=True)
    })

