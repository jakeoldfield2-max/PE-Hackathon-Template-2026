import json
import logging
import uuid
from datetime import datetime, timezone

from flask import g, has_request_context, request


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = "-"
        path = "-"
        method = "-"

        if has_request_context():
            request_id = getattr(g, "request_id", "-")
            path = request.path
            method = request.method

        record.request_id = request_id
        record.path = path
        record.method = method
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "method": getattr(record, "method", "-"),
            "path": getattr(record, "path", "-"),
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


def configure_json_logging() -> None:
    root = logging.getLogger()

    if not root.handlers:
        handler = logging.StreamHandler()
        root.addHandler(handler)

    formatter = JsonFormatter()
    context_filter = RequestContextFilter()

    for handler in root.handlers:
        handler.setFormatter(formatter)
        if not any(isinstance(f, RequestContextFilter) for f in handler.filters):
            handler.addFilter(context_filter)

    root.setLevel(logging.INFO)


def attach_request_id_handlers(app) -> None:
    @app.before_request
    def bind_request_id() -> None:
        incoming = request.headers.get("X-Request-ID")
        g.request_id = incoming.strip() if incoming else str(uuid.uuid4())

    @app.after_request
    def expose_request_id(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "-")
        return response
