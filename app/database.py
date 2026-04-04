import os

from peewee import DatabaseProxy, Model, PostgresqlDatabase

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


def init_db(app):
    host = os.environ.get("DATABASE_HOST", "localhost")

    # Use SSL for remote connections (e.g., Supabase)
    ssl_mode = "require" if host != "localhost" else None

    database = PostgresqlDatabase(
        os.environ.get("DATABASE_NAME", "hackathon_db"),
        host=host,
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        user=os.environ.get("DATABASE_USER", "postgres"),
        password=os.environ.get("DATABASE_PASSWORD"),
        sslmode=ssl_mode,
    )
    db.initialize(database)

    @app.before_request
    def _db_connect():
        # Skip DB connection for health checks - they should work without DB
        from flask import request
        if request.path == "/health":
            return
        try:
            db.connect(reuse_if_open=True)
        except Exception:
            # Let request proceed - route handlers will fail gracefully if they need DB
            pass

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()
