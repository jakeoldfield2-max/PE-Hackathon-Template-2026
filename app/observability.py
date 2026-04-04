import time
from typing import Dict

from flask import Response, g, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    ProcessCollector,
    generate_latest,
)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
)

# Registers process_resident_memory_bytes and related process metrics.
PROCESS_COLLECTOR = ProcessCollector()
ACTIVE_URLS_GAUGE = Gauge("urlpulse_active_urls", "Number of active short URLs")
ACTIVE_USERS_GAUGE = Gauge("urlpulse_active_users", "Number of active users")


def _endpoint_label() -> str:
    if request.url_rule and request.url_rule.rule:
        return request.url_rule.rule
    return "unknown"


def before_request_metrics() -> None:
    g.request_start_time = time.perf_counter()


def after_request_metrics(response: Response) -> Response:
    start_time = getattr(g, "request_start_time", None)
    if start_time is None:
        return response

    duration = time.perf_counter() - start_time
    labels: Dict[str, str] = {
        "method": request.method,
        "endpoint": _endpoint_label(),
    }

    REQUEST_DURATION.labels(**labels).observe(duration)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=_endpoint_label(),
        status=str(response.status_code),
    ).inc()
    return response


def metrics_response() -> Response:
    payload = generate_latest()
    return Response(payload, mimetype=CONTENT_TYPE_LATEST)


def update_business_metrics(active_urls: int, active_users: int) -> None:
    ACTIVE_URLS_GAUGE.set(active_urls)
    ACTIVE_USERS_GAUGE.set(active_users)
