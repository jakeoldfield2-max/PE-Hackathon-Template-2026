import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone

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


def _log_startup_event(level, message, **extra):
    """Log a structured JSON message during startup (before Flask logging is ready)."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "logger": "app.startup",
        "message": message,
        "phase": "startup",
        **extra
    }
    print(json.dumps(log_entry), file=sys.stderr, flush=True)


def create_app():
    load_dotenv()

    _log_startup_event("INFO", "Application starting",
                       python_version=sys.version,
                       testing_mode=bool(os.environ.get("TESTING")))

    configure_json_logging()
    logger = logging.getLogger(__name__)

    app = Flask(__name__)

    # Skip PostgreSQL init in test mode - tests use SQLite via conftest.py
    # Entire DB setup is wrapped in try-except so app can start for /health checks
    if not os.environ.get("TESTING"):
        db_host = os.environ.get("DATABASE_HOST", "localhost")
        db_name = os.environ.get("DATABASE_NAME", "hackathon_db")
        db_port = os.environ.get("DATABASE_PORT", "5432")
        db_user = os.environ.get("DATABASE_USER", "postgres")

        _log_startup_event("INFO", "Initializing database connection",
                           db_host=db_host,
                           db_name=db_name,
                           db_port=db_port,
                           db_user=db_user,
                           db_password_set=bool(os.environ.get("DATABASE_PASSWORD")))

        try:
            init_db(app)
            _log_startup_event("INFO", "Database proxy initialized successfully")

            from app.models.user import User
            from app.models.url import Url
            from app.models.event import Event

            # Create tables if they don't exist
            db.create_tables([User, Url, Event], safe=True)
            _log_startup_event("INFO", "Database tables created/verified successfully")
        except Exception as e:
            _log_startup_event("WARNING", "Database initialization failed - app will start without DB",
                               error_type=type(e).__name__,
                               error_message=str(e),
                               traceback=traceback.format_exc(),
                               note="App will continue - /health will work, /ready will return 503")

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

    # --- Chaos testing endpoint ---
    @app.route("/chaos/error")
    def chaos_error():
        """Returns 500 on purpose — used by chaos.sh error-flood to trigger HighErrorRate alert."""
        return jsonify(error="Intentional chaos error", status=500), 500

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

    _log_startup_event("INFO", "Application startup complete",
                       routes_registered=len(app.url_map._rules),
                       testing_mode=bool(os.environ.get("TESTING")))

    return app
