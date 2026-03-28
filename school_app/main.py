# main.py
from fastapi import FastAPI, Request
from sqladmin import Admin
from database.session import engine
from middleware.cors import setup_cors
from middleware.decryption import DecryptionMiddleware
from middleware.encryption import EncryptionMiddleware
from middleware.monitoring import MonitoringMiddleware, metrics_endpoint, loki_logger
from security.dependencies import SessionAuthError
from response.result import Result
# routers.py
from api.routers import ROUTERS

app = FastAPI(title="FastAPI Production App")

# API Routers
for router, prefix in ROUTERS:
    app.include_router(router, prefix=prefix)

# ── Exception handler for session auth errors ──────────────
@app.exception_handler(SessionAuthError)
async def session_auth_error_handler(request: Request, exc: SessionAuthError):
    return Result(code=exc.code, message=exc.message, extra={}).http_response()

# Middleware Setup
# 1️⃣ CORS
setup_cors(app)

# 2️⃣ Decrypt incoming requests (only selected paths)
app.add_middleware(DecryptionMiddleware)

# 3️⃣ Logging middleware for request/response metadata
app.add_middleware(MonitoringMiddleware)

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


###
# Admin Panel
# admin = Admin(app, engine)
# admin.add_view(UserAdmin)

@app.get("/metrics", include_in_schema=False)
def metrics():
    return metrics_endpoint()
