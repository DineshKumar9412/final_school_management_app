# api/auth.py
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from database.session import get_db
from database.redis_cache import cache
from models.user_models import DeviceRegistration, Session
from schemas.user_schemas import DeviceRegisterRequest, DeviceRegisterResponse
from security.dependencies import validate_session
from response.result import Result

auth_router = APIRouter(tags=["AUTH"])

SESSION_TTL_DAYS = 30
CACHE_TTL = 300  # 5 minutes


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
    """
    Device Registration & Session Flow
    ────────────────────────────────────
    1. Upsert device record.
    2. Check for an existing active session on this device.
    3. If session exists:
       a. FCM token unchanged → return existing client_key.
       b. FCM token changed   → update FCM token, return same client_key.
    4. If no session → create a new anonymous session, return new client_key.
    5. Web clients: client_key is also set as an HttpOnly cookie.
    """

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
                user_id=None,                          # anonymous until login
                role=None,
                client_key=client_key,
                valid_till=now + timedelta(days=SESSION_TTL_DAYS),
            )
            db.add(new_session)
            is_new = True

    # ── Step 5: Cache the client_key → device_id mapping ──────
    await cache.set(
        f"session:{client_key}",
        {"device_id": device.device_id, "user_id": None},
        expire=CACHE_TTL,
    )

    # ── Web clients: set HttpOnly cookie ───────────────────────
    if payload.os.lower() == "web":
        response.set_cookie(
            key="client_key",
            value=client_key,
            httponly=True,
            samesite="lax",
            max_age=SESSION_TTL_DAYS * 86400,
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
    response: Response,
    session: dict = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    client_key = session["client_key"]

    async with db.begin():
        await db.execute(
            update(Session)
            .where(Session.client_key == client_key)
            .values(user_id=None, role=None, device_id=None)
        )

    await cache.delete(f"session:{client_key}")

    # Clear web cookie
    response.delete_cookie("client_key")

    return Result(code=200, message="Logged out successfully.", extra={}).http_response()
