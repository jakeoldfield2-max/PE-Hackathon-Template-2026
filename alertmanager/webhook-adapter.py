#!/usr/bin/env python3
"""Webhook adapter that converts Alertmanager format to Discord and tracks alerts in PostgreSQL."""
import json
import os
import re
import sys
import threading
import time
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")
print(f"Discord webhook configured: {DISCORD_WEBHOOK[:50]}...", flush=True)

# Situation Update interval in seconds
SITUATION_UPDATE_INTERVAL = 60

# Database configuration - supports both local PostgreSQL and Supabase
# If DATABASE_URL is set (Supabase style), use that. Otherwise build from individual vars.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    DB_HOST = os.environ.get("DB_HOST", "postgres")
    DB_PORT = os.environ.get("DB_PORT", "5432")
    DB_NAME = os.environ.get("DB_NAME", os.environ.get("POSTGRES_DB", "hackathon_db"))
    DB_USER = os.environ.get("DB_USER", os.environ.get("POSTGRES_USER", "postgres"))
    DB_PASS = os.environ.get("DB_PASS", os.environ.get("POSTGRES_PASSWORD", ""))
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Try to import psycopg2, will be None if not installed
db_conn = None
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_AVAILABLE = True
    print("PostgreSQL support enabled", flush=True)
except ImportError:
    DB_AVAILABLE = False
    print("PostgreSQL support disabled (psycopg2 not installed)", flush=True)


def get_db_connection():
    """Get database connection, creating tables if needed."""
    global db_conn
    if not DB_AVAILABLE:
        return None

    try:
        if db_conn is None or db_conn.closed:
            db_conn = psycopg2.connect(DATABASE_URL)
            db_conn.autocommit = True
            # Create tables if they don't exist
            with db_conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS alert_logs (
                        id SERIAL PRIMARY KEY,
                        fingerprint VARCHAR(64) UNIQUE NOT NULL,
                        alertname VARCHAR(255) NOT NULL,
                        instance VARCHAR(255),
                        severity VARCHAR(50),
                        status VARCHAR(50) NOT NULL,
                        summary TEXT,
                        description TEXT,
                        first_fired_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        last_updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        resolved_at TIMESTAMP WITH TIME ZONE,
                        notes TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        -- Fields for tracking situation updates
                        last_notified_at TIMESTAMP WITH TIME ZONE,
                        last_notified_notes TEXT,
                        last_notified_description TEXT
                    )
                """)
                # Add new columns if they don't exist (for existing tables)
                cur.execute("""
                    DO $$
                    BEGIN
                        ALTER TABLE alert_logs ADD COLUMN IF NOT EXISTS last_notified_at TIMESTAMP WITH TIME ZONE;
                        ALTER TABLE alert_logs ADD COLUMN IF NOT EXISTS last_notified_notes TEXT;
                        ALTER TABLE alert_logs ADD COLUMN IF NOT EXISTS last_notified_description TEXT;
                    EXCEPTION WHEN OTHERS THEN NULL;
                    END $$;
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_alert_logs_status ON alert_logs(status)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_alert_logs_alertname ON alert_logs(alertname)")
            print("Database connected and tables ready", flush=True)
        return db_conn
    except Exception as e:
        print(f"Database connection error: {e}", flush=True)
        return None


def send_to_discord(content):
    """Send a message to Discord."""
    try:
        discord_payload = json.dumps({"content": content}).encode()
        req = urllib.request.Request(
            DISCORD_WEBHOOK,
            data=discord_payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "URLPulse-Alertmanager/1.0"
            }
        )
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        print(f"Error sending to Discord: {e}", flush=True)
        return False


def log_alert_to_db(alert, group_status):
    """Log an alert to the database."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        fingerprint = alert.get("fingerprint", "")
        status = alert.get("status", group_status).lower()

        now = datetime.now(timezone.utc)
        starts_at = alert.get("startsAt", now.isoformat())

        with conn.cursor() as cur:
            if status == "firing":
                # Insert or update firing alert
                cur.execute("""
                    INSERT INTO alert_logs (fingerprint, alertname, instance, severity, status,
                                           summary, description, first_fired_at, last_updated_at,
                                           last_notified_at, last_notified_notes, last_notified_description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (fingerprint) DO UPDATE SET
                        status = EXCLUDED.status,
                        description = EXCLUDED.description,
                        last_updated_at = EXCLUDED.last_updated_at,
                        resolved_at = NULL
                """, (
                    fingerprint,
                    labels.get("alertname", "Unknown"),
                    labels.get("instance", ""),
                    labels.get("severity", "unknown"),
                    status,
                    annotations.get("summary", ""),
                    annotations.get("description", ""),
                    starts_at,
                    now,
                    now,  # last_notified_at - set on first fire
                    None,  # last_notified_notes
                    annotations.get("description", "")  # last_notified_description
                ))
            else:
                # Update to resolved
                cur.execute("""
                    UPDATE alert_logs
                    SET status = %s, last_updated_at = %s, resolved_at = %s
                    WHERE fingerprint = %s
                """, (status, now, now, fingerprint))

        print(f"Logged alert {fingerprint[:8]}... status={status}", flush=True)
    except Exception as e:
        print(f"Error logging alert to DB: {e}", flush=True)


def get_alerts_from_db(status_filter=None):
    """Get alerts from the database."""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if status_filter:
                cur.execute("""
                    SELECT * FROM alert_logs
                    WHERE status = %s
                    ORDER BY last_updated_at DESC
                """, (status_filter,))
            else:
                cur.execute("SELECT * FROM alert_logs ORDER BY last_updated_at DESC")
            return cur.fetchall()
    except Exception as e:
        print(f"Error fetching alerts: {e}", flush=True)
        return []


def update_alert_notes(fingerprint, notes):
    """Update notes for an alert."""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE alert_logs SET notes = %s, last_updated_at = %s
                WHERE fingerprint = %s
            """, (notes, datetime.now(timezone.utc), fingerprint))
            return cur.rowcount > 0
    except Exception as e:
        print(f"Error updating notes: {e}", flush=True)
        return False


def check_and_send_situation_updates():
    """Check for firing alerts and send situation updates if there are changes."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all firing alerts
            cur.execute("""
                SELECT * FROM alert_logs
                WHERE status = 'firing'
                ORDER BY first_fired_at ASC
            """)
            firing_alerts = cur.fetchall()

        if not firing_alerts:
            return

        now = datetime.now(timezone.utc)
        updates = []

        for alert in firing_alerts:
            fingerprint = alert['fingerprint']
            changes = []

            # Check for note changes
            current_notes = alert.get('notes') or ''
            last_notified_notes = alert.get('last_notified_notes') or ''
            if current_notes != last_notified_notes and current_notes:
                changes.append(f"**Note:** {current_notes}")

            # Check for description changes
            current_desc = alert.get('description') or ''
            last_notified_desc = alert.get('last_notified_description') or ''
            if current_desc != last_notified_desc and current_desc:
                changes.append(f"**Updated:** {current_desc}")

            # Calculate duration
            first_fired = alert.get('first_fired_at')
            if first_fired:
                if isinstance(first_fired, str):
                    first_fired = datetime.fromisoformat(first_fired.replace('Z', '+00:00'))
                duration = now - first_fired
                duration_mins = int(duration.total_seconds() // 60)
                duration_str = f"{duration_mins}m" if duration_mins < 60 else f"{duration_mins // 60}h {duration_mins % 60}m"
            else:
                duration_str = "unknown"

            # Build update message
            short_id = fingerprint[:8]
            msg = f"📋 **Situation Update** | ID: `{short_id}` | Duration: {duration_str}"

            if changes:
                msg += "\n" + "\n".join(changes)
            else:
                msg += "\n_No changes - still ongoing_"

            updates.append((fingerprint, msg, current_notes, current_desc))

        # Send combined update to Discord
        if updates:
            content = "═══════════════════════════════\n"
            content += "\n\n".join([u[1] for u in updates])
            content += "\n═══════════════════════════════"

            if send_to_discord(content):
                print(f"Sent situation update for {len(updates)} alert(s)", flush=True)

                # Update last_notified fields
                with conn.cursor() as cur:
                    for fingerprint, _, notes, desc in updates:
                        cur.execute("""
                            UPDATE alert_logs
                            SET last_notified_at = %s,
                                last_notified_notes = %s,
                                last_notified_description = %s
                            WHERE fingerprint = %s
                        """, (now, notes, desc, fingerprint))

    except Exception as e:
        print(f"Error in situation update: {e}", flush=True)
        import traceback
        traceback.print_exc()


def situation_update_loop():
    """Background thread that sends periodic situation updates."""
    print(f"Situation update thread started (interval: {SITUATION_UPDATE_INTERVAL}s)", flush=True)
    while True:
        time.sleep(SITUATION_UPDATE_INTERVAL)
        try:
            check_and_send_situation_updates()
        except Exception as e:
            print(f"Error in situation update loop: {e}", flush=True)


class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests for alert API."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/alerts":
            # List alerts
            status_filter = query.get("status", [None])[0]
            alerts = get_alerts_from_db(status_filter)

            # Convert datetime objects to strings
            for alert in alerts:
                for key, value in alert.items():
                    if isinstance(value, datetime):
                        alert[key] = value.isoformat()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(alerts, indent=2).encode())

        elif path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        """Handle POST requests for Alertmanager webhooks and notes API."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # API endpoint for adding notes
        if path.startswith("/alerts/") and path.endswith("/notes"):
            fingerprint = path.split("/")[2]
            try:
                data = json.loads(body)
                notes = data.get("notes", "")
                if update_alert_notes(fingerprint, notes):
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'{"status": "updated"}')
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'{"error": "Alert not found"}')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        # Alertmanager webhook
        try:
            data = json.loads(body)
            print(f"Full Alertmanager payload: {json.dumps(data, indent=2)}", flush=True)
            status = data.get("status", "unknown").upper()
            alerts = data.get("alerts", [])

            messages = []
            status_display = "Ongoing" if status == "FIRING" else "Resolved"

            for alert in alerts:
                # Log to database
                log_alert_to_db(alert, status.lower())

                labels = alert.get("labels", {})
                annotations = alert.get("annotations", {})
                fingerprint = alert.get("fingerprint", "")[:8]

                name = labels.get("alertname", "Unknown")
                severity = labels.get("severity", "unknown")
                instance = labels.get("instance", "")

                summary = annotations.get("summary", "")
                desc = annotations.get("description", "No description")
                impact = annotations.get("impact", "")
                runbook = annotations.get("runbook", "")
                action = annotations.get("action", "")

                severity_icon = "🚨" if severity == "critical" else "⚠️"

                msg = f"═══════════════════════════════\n"
                msg += f"**{status_display}** {severity_icon} **{name}**\n"
                msg += f"ID: `{fingerprint}`\n"
                if summary:
                    msg += f"{summary}\n"
                msg += f"{desc}\n"
                if instance:
                    msg += f"**Instance:** `{instance}`\n"
                if impact:
                    msg += f"**Impact:** {impact}\n"
                if action and status == "FIRING":
                    # Format numbered steps as a clean list
                    # Split on numbered patterns (1., 2., 3., etc.)
                    parts = re.split(r'(\d+\.)', action)
                    steps = []
                    for i in range(1, len(parts), 2):
                        if i + 1 < len(parts):
                            steps.append(f"{parts[i]} {parts[i+1].strip()}")
                    if steps:
                        msg += "**Action:**\n"
                        for step in steps:
                            msg += f"{step}\n"
                    else:
                        # Fallback if no numbered pattern found
                        msg += f"**Action:** {action}\n"
                if runbook:
                    msg += f"**Runbook:** `{runbook}`\n"
                msg += f"═══════════════════════════════"
                messages.append(msg)

            content = "\n\n".join(messages) if messages else f"Alert status: {status}"

            # Send to Discord
            print(f"Sending to Discord: {content[:100]}...", flush=True)
            send_to_discord(content)
            print("Sent successfully!", flush=True)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            import traceback
            print(f"Error: {e}", flush=True)
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, format, *args):
        print(f"[webhook-adapter] {args[0]}")


if __name__ == "__main__":
    # Try to connect to DB on startup
    get_db_connection()

    # Start situation update background thread
    update_thread = threading.Thread(target=situation_update_loop, daemon=True)
    update_thread.start()

    server = HTTPServer(("0.0.0.0", 9095), WebhookHandler)
    print("Webhook adapter listening on :9095")
    print("API endpoints:")
    print("  GET  /alerts          - List all alerts")
    print("  GET  /alerts?status=firing  - List firing alerts")
    print("  POST /alerts/{fingerprint}/notes - Add notes to alert")
    print(f"Situation updates every {SITUATION_UPDATE_INTERVAL}s for firing alerts")
    server.serve_forever()
