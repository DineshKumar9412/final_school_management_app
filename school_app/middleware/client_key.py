# middleware/client_key.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from datetime import datetime

from database.redis_cache import cache

SESSION_CACHE_TTL = 300  # seconds

# Path prefixes that bypass client_key validation
EXCLUDED_PREFIXES = (
    "/api/auth/device/register",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/metrics",
)


def _unauthorized(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"code": 401, "message": message, "result": {}},
    )


async def _build_session_info(session, db) -> dict:
    """Build enriched session dict with device and user info."""
    from models.user_models import DeviceRegistration, Employee, Student

    # ── Device info (id + fcm_token only) ─────────────────────
    device_info = None
    if session.device_id is not None:
        dev_result = await db.execute(
            select(DeviceRegistration).where(DeviceRegistration.id == session.device_id)
        )
        device = dev_result.scalar_one_or_none()
        if device:
            device_info = {"id": device.id, "fcm_token": device.fcm_token}

    # ── User info (full, based on role) ───────────────────────
    user_info = None
    if session.user_id and session.role:
        role = session.role.lower()
        if role == "student":
            stu_result = await db.execute(
                select(Student).where(Student.student_id == int(session.user_id))
            )
            student = stu_result.scalar_one_or_none()
            if student:
                user_info = {
                    "id": student.student_id,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "phone": student.phone,
                }
        else:
            emp_result = await db.execute(
                select(Employee).where(Employee.id == int(session.user_id))
            )
            employee = emp_result.scalar_one_or_none()
            if employee:
                user_info = {
                    "id": employee.id,
                    "first_name": employee.first_name,
                    "last_name": employee.last_name,
                    "email": employee.email,
                    "mobile": employee.mobile,
                }

    return {
        "client_key": session.client_key,
        "role": session.role,
        "valid_till": session.valid_till.isoformat(),
        "device_id": device_info,
        "user_id": user_info,
    }


class ClientKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(EXCLUDED_PREFIXES):
            return await call_next(request)

        # Web → cookie | Android/TV → X-Client-Key header
        client_key = (
            request.cookies.get("client_key")
            or request.headers.get("X-Client-Key")
        )

        if not client_key:
            return _unauthorized("client_key required.")

        # ── Cache hit ──────────────────────────────────────────
        cached = await cache.get(f"session:{client_key}")
        if cached:
            request.state.session = cached
            return await call_next(request)

        # ── Cache miss: validate from DB ───────────────────────
        from database.session import AsyncSessionLocal
        from models.user_models import Session as SessionModel

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SessionModel).where(SessionModel.client_key == client_key)
            )
            session = result.scalar_one_or_none()

            if session is None:
                return _unauthorized("Invalid session.")

            if session.valid_till < datetime.utcnow():
                # Clean up expired session
                async with db.begin():
                    await db.execute(
                        update(SessionModel)
                        .where(SessionModel.id == session.id)
                        .values(user_id=None, role=None, device_id=None)
                    )
                await cache.delete(f"session:{client_key}")
                return _unauthorized("Session expired.")

            session_info = await _build_session_info(session, db)

        await cache.set(f"session:{client_key}", session_info, expire=SESSION_CACHE_TTL)
        request.state.session = session_info
        return await call_next(request)
