import os

from dotenv import load_dotenv
from flask import Flask, jsonify

from app.database import db, init_db
from app.logging_config import attach_request_id_handlers, configure_json_logging
from app.observability import (
    after_request_metrics,
    before_request_metrics,
    metrics_response,
)
from app.routes import register_routes


def create_app():
    load_dotenv()
    configure_json_logging()

    app = Flask(__name__)

    # Skip PostgreSQL init in test mode - tests use SQLite via conftest.py
    if not os.environ.get("TESTING"):
        init_db(app)

        from app.models.user import User
        from app.models.url import Url
        from app.models.event import Event

        # Create tables if they don't exist
        # Wrapped in try/except so app can start even without DB (for /health checks)
        try:
            db.create_tables([User, Url, Event], safe=True)
        except Exception as e:
            print(f"Warning: Could not create tables (DB may be unavailable): {e}")

    attach_request_id_handlers(app)
    app.before_request(before_request_metrics)
    app.after_request(after_request_metrics)

    register_routes(app)

    @app.route("/metrics")
    def metrics():
        return metrics_response()

    # --- Standardized JSON error handlers ---
    # WHY: Without these, Flask returns HTML error pages for unhandled errors.
    # Consistent JSON format is required for Reliability Silver evidence.
    # Reference: API.md error format, FEATURES.md reliability mapping.

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error="Bad request", status=400), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Not found", status=404), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify(error="Method not allowed", status=405), 405

    @app.errorhandler(409)
    def conflict(e):
        return jsonify(error="Conflict", status=409), 409

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify(error="Unprocessable entity", status=422), 422

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify(error="Internal server error", status=500), 500

    # --- Health & Readiness ---

    @app.route("/health")
    def health():
        """Liveness check — is the process alive?"""
        return jsonify(status="ok")

    @app.route("/ready")
    def ready():
        """Readiness check — can the app serve traffic?
        Returns 200 if DB is reachable, 503 otherwise.
        WHY: Differentiates 'app is alive' from 'app can serve traffic'.
        During chaos testing (kill DB), /health=200 but /ready=503.
        Reference: FAILURE_MODES.md scenario 2, chaos.sh --db mode.
        """
        try:
            db.execute_sql("SELECT 1")
            return jsonify(status="ready", database="connected"), 200
        except Exception:
            return jsonify(status="not ready", database="disconnected"), 503

    return app
