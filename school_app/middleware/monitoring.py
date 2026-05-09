# middleware/monitoring.py
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
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
# Logger Factory
# -----------------------
def _build_logger() -> logging.Logger:
    use_loki = os.getenv("LOKI", "False").strip().lower() == "true"
    logger   = logging.getLogger("app_logger")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:          # avoid duplicate handlers on reload
        return logger

    fmt = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # ── INFO handler — always local logs/app.log ──────────────────────────────
    info_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,   # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    info_handler.setLevel(logging.INFO)
    info_handler.addFilter(lambda r: r.levelno < logging.ERROR)   # INFO only, not ERROR
    info_handler.setFormatter(fmt)
    logger.addHandler(info_handler)

    # ── ERROR handler — Loki if LOKI=True, else local logs/error.log ─────────
    if use_loki:
        from logging_loki import LokiHandler
        error_handler = LokiHandler(
            url="http://loki:3100/loki/api/v1/push",
            tags={"app": "fastapi"},
            version="1",
        )
    else:
        error_handler = RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )

    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(fmt)
    logger.addHandler(error_handler)

    return logger


# Single shared logger — import this everywhere
app_logger  = _build_logger()
loki_logger = app_logger          # alias so existing imports don't break


# -----------------------
# Monitoring Middleware
# Handles Prometheus metrics + logs 500 exceptions only
# -----------------------
_SKIP_PATHS = {"/metrics", "/docs", "/redoc", "/openapi.json"}

class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start  = time.time()
        status = 200
        try:
            response = await call_next(request)
            status   = response.status_code
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
                status=status,
            ).inc()
            if status >= 500:
                ERROR_COUNT.labels(path=request.url.path, status=status).inc()


# -----------------------
# Metrics Endpoint
# -----------------------
def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
