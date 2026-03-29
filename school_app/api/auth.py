# api/auth.py
import uuid
from datetime import datetime, timedelta
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Response, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from database.session import get_db
from database.redis_cache import cache
from models.user_models import DeviceRegistration, Session
from schemas.user_schemas import DeviceRegisterRequest, DeviceRegisterResponse
from security.dependencies import validate_session
from response.result import Result

auth_router = APIRouter(tags=["AUTH"])

SESSION_ADMIN_TTL_DAYS = 10
SESSION_TTL_DAYS = 30
CACHE_TTL = 300  


# ─────────────────────────────────────────────
# Helper: get or create device record
# ─────────────────────────────────────────────
async def _upsert_device(db: AsyncSession, data: DeviceRegisterRequest) -> DeviceRegistration:
    """Insert device if new, otherwise update its fields. Returns the ORM object."""
    result = await db.execute(
        select(DeviceRegistration).where(DeviceRegistration.device_id == data.device_id)
    )
    device = result.scalar_one_or_none()

    if device is None:
        # New device
        device = DeviceRegistration(
            device_id=data.device_id,
            os=data.os,
            os_version=data.os_version,
            make=data.make,
            model=data.model,
            app_version=data.app_version,
            fcm_token=data.fcm_token,
        )
        db.add(device)
        await db.flush()   # get device.id without committing
    else:
        # Update mutable fields
        device.os         = data.os
        device.os_version = data.os_version
        device.make       = data.make
        device.model      = data.model
        device.app_version = data.app_version
        # fcm_token is handled separately in the flow

    return device


# ─────────────────────────────────────────────
# POST /api/auth/device/register
# ─────────────────────────────────────────────
@auth_router.post("/device/register", summary="Register or re-register a device")
async def device_register(
    payload: DeviceRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    
    async with db.begin():
        # ── Step 1: Upsert device ─────────────────────────────
        device = await _upsert_device(db, payload)

        # ── Step 2: Check existing active session ─────────────
        now = datetime.utcnow()
        sess_result = await db.execute(
            select(Session).where(
                Session.device_id == device.id,
                Session.valid_till > now,
            )
        )
        existing_session: Session | None = sess_result.scalar_one_or_none()

        if existing_session:
            # ── Step 3: Session exists ────────────────────────
            if payload.fcm_token and device.fcm_token != payload.fcm_token:
                # Step 3b: FCM token changed — update device row
                device.fcm_token = payload.fcm_token

            client_key = existing_session.client_key
            is_new = False
        else:
            # ── Step 4: No active session — create one ────────
            if payload.fcm_token:
                device.fcm_token = payload.fcm_token

            client_key = str(uuid.uuid4())
            new_session = Session(
                device_id=device.id,
                user_id=None,                      
                role=None,
                client_key=client_key,
                valid_till=now + timedelta(days=SESSION_ADMIN_TTL_DAYS),
            )
            db.add(new_session)
            is_new = True

    # ── Web clients: set HttpOnly cookie ───────────────────────
    if payload.os.lower() == "web":
        response.set_cookie(
            key="client_key",
            value=client_key,
            httponly=True,
            samesite="lax",
            max_age=SESSION_ADMIN_TTL_DAYS * 86400,
        )

    return Result(
        code=200,
        message="Device registered successfully." if is_new else "Session resumed.",
        extra=DeviceRegisterResponse(client_key=client_key, is_new=is_new).model_dump(),
    ).http_response()


# ─────────────────────────────────────────────
# POST /api/auth/logout
# ─────────────────────────────────────────────

@auth_router.post("/logout", summary="Logout — clears session user_id, role, device_id")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    client_key: Annotated[
        Optional[str],
        Header(description="Client key from device registration (Android/TV). Web clients send it automatically via cookie.")
    ] = None,
    platform: Optional[str] = None
):
    client_key = client_key or request.cookies.get("client_key")

    if not client_key:
        return Result(code=401, message="client_key required.", extra={}).http_response()

    result = await db.execute(
        select(Session).where(Session.client_key == client_key)
    )
    session = result.scalar_one_or_none()

    if session is None:
        return Result(code=401, message="Invalid session.", extra={}).http_response()

    await db.execute(
        update(Session)
        .where(Session.client_key == client_key)
        .values(user_id=None, role=None)
    )
    await db.commit()
    await cache.delete(f"session:{client_key}")

    if platform == "web":
        response.delete_cookie("client_key")

    return Result(code=200, message="Logged out successfully.", extra={}).http_response()
