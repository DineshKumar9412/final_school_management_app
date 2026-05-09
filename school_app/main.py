# main.py
from fastapi import FastAPI, Request
from sqladmin import Admin
from admin.db_admin import ALL_VIEWS, authentication_backend
from database.session import engine
from starlette.middleware.sessions import SessionMiddleware
from middleware.cors import setup_cors
from middleware.decryption import DecryptionMiddleware
from middleware.encryption import EncryptionMiddleware
from middleware.monitoring import MonitoringMiddleware, metrics_endpoint, loki_logger
from response.result import Result
from security.valid_session import SessionAuthError
from scheduler.alarm_scheduler import create_scheduler
from api.routers import ROUTERS

app = FastAPI(title="FastAPI Production App")

@app.exception_handler(SessionAuthError)
async def session_auth_error_handler(request: Request, exc: SessionAuthError):
    return Result(code=exc.code, message=exc.message, extra={}).http_response()

_scheduler = create_scheduler()

@app.on_event("startup")
async def start_scheduler():
    _scheduler.start()

@app.on_event("shutdown")
async def stop_scheduler():
    _scheduler.shutdown(wait=False)

# API Routers
for router, prefix in ROUTERS:
    app.include_router(router, prefix=prefix)

# Middleware Setup
# 1️⃣ Session (required for db_admin login)
app.add_middleware(SessionMiddleware, secret_key="db_admin_secret_key_school_2026")

# 2️⃣ CORS
setup_cors(app)

# 2️⃣ Decrypt incoming requests (only selected paths)
app.add_middleware(DecryptionMiddleware)

# 3️⃣ Logging middleware for request/response metadata
# app.add_middleware(MonitoringMiddleware)

# 4️⃣ Encrypt outgoing responses (only selected paths)
app.add_middleware(EncryptionMiddleware)

# 5️⃣ Catch all unhandled exceptions and log
# @app.middleware("http")
# async def catch_exceptions_middleware(request: Request, call_next):
#     try:
#         return await call_next(request)
#     except Exception as e:
#         loki_logger.error(
#             "Unhandled exception occurred",
#             extra={
#                 "path": request.url.path,
#                 "method": request.method,
#                 "error": str(e)
#             }
#         )
#         return JSONResponse(
#             status_code=500,
#             content={"detail": "Internal Server Error"}
#         )


# DB Admin Panel — http://69.62.77.182:8005/db_admin
db_admin = Admin(app, engine, base_url="/db_admin", authentication_backend=authentication_backend)
for view in ALL_VIEWS:
    db_admin.add_view(view)


@app.get("/metrics", include_in_schema=False)
def metrics():
    return metrics_endpoint()
