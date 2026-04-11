# api/custom_alarm.py
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from models.auth_models import FcmToken, Session
from models.custom_alarm_models import CustomAlarm
from response.result import Result
from schemas.custom_alarm_schemas import CustomAlarmCreate, CustomAlarmUpdate
from security.valid_session import valid_session

custom_alarm_router = APIRouter(tags=["ANDROID APIS"])


def _alarm_to_dict(alarm: CustomAlarm) -> dict:
    return {
        "id":         alarm.id,
        "class_id":   alarm.class_id,
        "section_id": alarm.section_id,
        "message":    alarm.message,
        "alarm_date": str(alarm.alarm_date),
        "slot_time":  alarm.slot_time,
        "created_at": alarm.created_at.isoformat(),
        "updated_at": alarm.updated_at.isoformat(),
    }


# ── GET list ───────────────────────────────────────────────────────────────────

@custom_alarm_router.get("/")
async def list_alarms(
    class_id:   Optional[int]  = None,
    section_id: Optional[int]  = None,
    alarm_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    stmt = select(CustomAlarm)
    if class_id is not None:
        stmt = stmt.where(CustomAlarm.class_id == class_id)
    if section_id is not None:
        stmt = stmt.where(CustomAlarm.section_id == section_id)
    if alarm_date is not None:
        stmt = stmt.where(CustomAlarm.alarm_date == alarm_date)

    result = await db.execute(stmt)
    alarms = result.scalars().all()

    return Result(
        code=200,
        message="Alarms fetched.",
        extra={"alarms": [_alarm_to_dict(a) for a in alarms]},
    ).http_response()


# ── GET single ─────────────────────────────────────────────────────────────────

@custom_alarm_router.get("/{alarm_id}")
async def get_alarm(
    alarm_id: int,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    result = await db.execute(
        select(CustomAlarm).where(CustomAlarm.id == alarm_id)
    )
    alarm = result.scalar_one_or_none()

    if alarm is None:
        return Result(code=404, message="Alarm not found.").http_response()

    return Result(code=200, message="Alarm fetched.", extra=_alarm_to_dict(alarm)).http_response()


# ── POST create ────────────────────────────────────────────────────────────────

@custom_alarm_router.post("/")
async def create_alarm(
    payload: CustomAlarmCreate,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    alarm = CustomAlarm(
        class_id   = payload.class_id,
        section_id = payload.section_id,
        message    = payload.message,
        alarm_date = payload.alarm_date,
        slot_time  = payload.slot_time,
    )
    db.add(alarm)
    await db.commit()
    await db.refresh(alarm)

    return Result(code=201, message="Alarm created.", extra=_alarm_to_dict(alarm)).http_response()


# ── PUT update ─────────────────────────────────────────────────────────────────

@custom_alarm_router.put("/{alarm_id}")
async def update_alarm(
    alarm_id: int,
    payload: CustomAlarmUpdate,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    result = await db.execute(
        select(CustomAlarm).where(CustomAlarm.id == alarm_id)
    )
    alarm = result.scalar_one_or_none()

    if alarm is None:
        return Result(code=404, message="Alarm not found.").http_response()

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alarm, field, value)

    await db.commit()
    await db.refresh(alarm)

    return Result(code=200, message="Alarm updated.", extra=_alarm_to_dict(alarm)).http_response()


# ── DELETE ─────────────────────────────────────────────────────────────────────

@custom_alarm_router.delete("/{alarm_id}")
async def delete_alarm(
    alarm_id: int,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    result = await db.execute(
        select(CustomAlarm).where(CustomAlarm.id == alarm_id)
    )
    alarm = result.scalar_one_or_none()

    if alarm is None:
        return Result(code=404, message="Alarm not found.").http_response()

    await db.delete(alarm)
    await db.commit()

    return Result(code=200, message="Alarm deleted.").http_response()


# ── POST stop-alarm ────────────────────────────────────────────────────────────

@custom_alarm_router.post("/stop-alarm")
async def stop_alarm(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """Mark the current user's alarm as stopped (status=1). Uses user_id from session."""
    user_id = int(session.user_id) if session.user_id else None

    if not user_id:
        return Result(code=401, message="Not logged in.").http_response()

    result = await db.execute(
        update(FcmToken)
        .where(FcmToken.user_id == user_id)
        .values(status=1)
    )
    await db.commit()

    if result.rowcount == 0:
        return Result(code=404, message="No FCM token found for this user.").http_response()

    return Result(code=200, message="Alarm stopped.").http_response()

## Test Alarm Working
from scheduler.alarm_scheduler import fire_alarm_slot, reset_alarm_status

@custom_alarm_router.post("/test-alarm-slot")
async def test_alarm_slot(slot_time: str = "8.00"):
    await fire_alarm_slot(slot_time)
    return Result(code=200, message=f"Slot {slot_time} fired.").http_response()

@custom_alarm_router.post("/test-reset-status")
async def test_reset_status():
    await reset_alarm_status()
    return Result(code=200, message="Status reset done.").http_response()
