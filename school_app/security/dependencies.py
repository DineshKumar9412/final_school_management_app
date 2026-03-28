# security/dependencies.py
from typing import Annotated, Optional
from datetime import datetime

from fastapi import Header, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from database.session import get_db
from database.redis_cache import cache
from models.user_models import Session as SessionModel, DeviceRegistration, Employee, Student

SESSION_CACHE_TTL = 300  # seconds


# ─────────────────────────────────────────────
# Custom auth exception (handled in main.py)
# ─────────────────────────────────────────────

class SessionAuthError(Exception):
    def __init__(self, code: int, message: str):
        self.code    = code
        self.message = message


# ─────────────────────────────────────────────
# Build enriched session dict
# ─────────────────────────────────────────────

async def _build_session_info(session: SessionModel, db: AsyncSession) -> dict:
    """Returns enriched session:
    {
        client_key, role, valid_till,
        device_id: {id, fcm_token} | None,
        user_id:   full user info  | None
    }
    """
    # ── Device (id + fcm_token only) ──────────────────────────
    device_info = None
    if session.device_id is not None:
        dev_result = await db.execute(
            select(DeviceRegistration).where(DeviceRegistration.id == session.device_id)
        )
        device = dev_result.scalar_one_or_none()
        if device:
            device_info = {"id": device.id, "fcm_token": device.fcm_token}

    # ── User (full info based on role) ────────────────────────
    user_info = None
    if session.user_id and session.role:
        role = session.role.lower()
        if role == "student":
            stu = (await db.execute(
                select(Student).where(Student.student_id == int(session.user_id))
            )).scalar_one_or_none()
            if stu:
                user_info = {
                    "id":         stu.student_id,
                    "first_name": stu.first_name,
                    "last_name":  stu.last_name,
                    "phone":      stu.phone,
                }
        else:
            emp = (await db.execute(
                select(Employee).where(Employee.id == int(session.user_id))
            )).scalar_one_or_none()
            if emp:
                user_info = {
                    "id":         emp.id,
                    "first_name": emp.first_name,
                    "last_name":  emp.last_name,
                    "email":      emp.email,
                    "mobile":     emp.mobile,
                }

    return {
        "client_key": session.client_key,
        "role":       session.role,
        "valid_till": session.valid_till.isoformat(),
        "device_id":  device_info,
        "user_id":    user_info,
    }


# ─────────────────────────────────────────────
# validate_session dependency
# ─────────────────────────────────────────────

async def validate_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    client_key: Annotated[Optional[str], Header(alias="client_key", description="Client key from device registration (Android/TV). Web clients send it automatically via cookie.")] = None,
) -> dict:
    """
    Validates client_key from:
      - Header `client_key`  (Android / TV)
      - Cookie `client_key`  (Web — set automatically after device/register)

    Returns enriched session dict. Raises SessionAuthError on failure.
    """
    client_key = client_key or request.cookies.get("client_key")

    if not client_key:
        raise SessionAuthError(401, "client_key required.")

    cache_key = f"session:{client_key}"

    # ── 1. Cache hit ───────────────────────────────────────────
    cached = await cache.get(cache_key)
    if cached:
        valid_till = datetime.fromisoformat(cached["valid_till"])
        if valid_till >= datetime.utcnow():
            return cached
        # stale cache entry — fall through to DB check

    # ── 2. DB lookup ───────────────────────────────────────────
    result = await db.execute(
        select(SessionModel).where(SessionModel.client_key == client_key)
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise SessionAuthError(401, "Invalid session.")

    if session.valid_till < datetime.utcnow():
        # Clean up expired session
        await db.execute(
            update(SessionModel)
            .where(SessionModel.id == session.id)
            .values(user_id=None, role=None, device_id=None)
        )
        await db.commit()
        await cache.delete(cache_key)
        raise SessionAuthError(401, "Session expired.")

    # ── 3. Build, cache, return ────────────────────────────────
    session_info = await _build_session_info(session, db)
    await cache.set(cache_key, session_info, expire=SESSION_CACHE_TTL)
    return session_info

