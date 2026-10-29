import os
from flask import Flask, jsonify, render_template

from config import Config
from database import db
from exceptions import AppException

from routes.web import web_bp
from routes.api_incidents import api_incidents_bp
from routes.api_audit import api_audit_bp
from routes.api_notifications import api_notifications_bp
from routes.api_metrics import api_metrics_bp
from routes.api_auth import api_auth_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure instance directory exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Initialize database
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(web_bp)
    app.register_blueprint(api_auth_bp)
    app.register_blueprint(api_incidents_bp)
    app.register_blueprint(api_audit_bp)
    app.register_blueprint(api_notifications_bp)
    app.register_blueprint(api_metrics_bp)

    # Global exception handlers
    @app.errorhandler(AppException)
    def handle_app_exception(e):
        return jsonify(e.to_dict()), e.status_code

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            "success": False,
            "error": "Internal Server Error",
            "code": "INTERNAL_ERROR"
        }), 500

    # Initialize database tables and default users
    with app.app_context():
        import models
        db.create_all()

        from services.auth_service import AuthService
        AuthService.ensure_default_users()

    return app


# Vercel requires a top-level Flask application object
app = create_app()


# Run locally
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)