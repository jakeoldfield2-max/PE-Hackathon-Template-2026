from dotenv import load_dotenv
from flask import Flask, jsonify

from app.database import db, init_db
from app.routes import register_routes


def create_app():
    load_dotenv()

    app = Flask(__name__)

    init_db(app)

    from app import models  # noqa: F401 - registers models with Peewee

    register_routes(app)

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
