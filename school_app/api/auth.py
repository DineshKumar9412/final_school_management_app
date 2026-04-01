# api/auth.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from models.auth_models import DeviceRegistration
from response.result import Result
from schemas.auth_schemas import RegisterDeviceRequest

auth_router = APIRouter(tags=["SCHOOL AUTH"])

# ── register device ────────────────────────────────────────────────────────────

@auth_router.post("/register-device")
async def register_device(
    payload: RegisterDeviceRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DeviceRegistration).where(DeviceRegistration.device_id == payload.device_id)
    )
    device = result.scalar_one_or_none()

    is_new = device is None

    if is_new:
        device = DeviceRegistration(
            device_id=payload.device_id,
            os=payload.os,
            os_version=payload.os_version,
            make=payload.make,
            model=payload.model,
            app_version=payload.app_version,
            fcm_token=payload.fcm_token,
        )
        db.add(device)
    else:
        device.os = payload.os
        device.os_version = payload.os_version
        device.make = payload.make
        device.model = payload.model
        device.app_version = payload.app_version
        device.fcm_token = payload.fcm_token
        device.is_active = True

    await db.commit()

    message = "Device registered successfully" if is_new else "Device updated successfully"
    return Result(
        code=201 if is_new else 200,
        message=message,
        extra={"device_id": device.device_id, "is_new": is_new},
    ).http_response()

