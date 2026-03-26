# middleware/monitoring.py
import time
import logging
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from logging_loki import LokiHandler
from pythonjsonlogger import jsonlogger

# -----------------------
# Prometheus Metrics
# -----------------------
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request latency in seconds",
    ["path"]
)

ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP 5xx errors",
    ["path", "status"]
)

# -----------------------
# Loki Logger
# -----------------------
def get_loki_logger():
    handler = LokiHandler(
        url="http://loki:3100/loki/api/v1/push",
        tags={"app": "fastapi"},
        version="1",
    )
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s %(path)s %(method)s'
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger("fastapi_loki")
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)
    return logger

loki_logger = get_loki_logger()

# -----------------------
# Prometheus Middleware
# -----------------------
class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.time()
        status = 200
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        except Exception:
            status = 500
            raise
        finally:
            duration = time.time() - start
            REQUEST_LATENCY.labels(path=request.url.path).observe(duration)
            REQUEST_COUNT.labels(
                method=request.method,
                path=request.url.path,
                status=status
            ).inc()
            if status >= 500:
                ERROR_COUNT.labels(path=request.url.path, status=status).inc()

# -----------------------
# Metrics Endpoint
# -----------------------
def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
