# api/custom_alarm.py
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from models.auth_models import Session
from models.custom_alarm_models import CustomAlarm
from response.result import Result
from schemas.custom_alarm_schemas import CustomAlarmCreate, CustomAlarmUpdate
from security.valid_session import valid_session

custom_alarm_router = APIRouter(tags=["ANDROID APIS"])


def _alarm_to_dict(alarm: CustomAlarm) -> dict:
    return {
        "id":         alarm.id,
        "stream_id":  alarm.stream_id,
        "class_id":   alarm.class_id,
        "message":    alarm.message,
        "alarm_date": str(alarm.alarm_date),
        "slot_time":  alarm.slot_time,
        "created_at": alarm.created_at.isoformat(),
        "updated_at": alarm.updated_at.isoformat(),
    }


# ── GET list ───────────────────────────────────────────────────────────────────

@custom_alarm_router.get("/")
async def list_alarms(
    stream_id:  Optional[int]  = None,
    class_id:   Optional[int]  = None,
    alarm_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    stmt = select(CustomAlarm)
    if stream_id is not None:
        stmt = stmt.where(CustomAlarm.stream_id == stream_id)
    if class_id is not None:
        stmt = stmt.where(CustomAlarm.class_id == class_id)
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
        stream_id  = payload.stream_id,
        class_id   = payload.class_id,
        message    = payload.message,
        alarm_date = payload.alarm_date,
        slot_time  = payload.slot_time,
    )
    db.add(alarm)
    await db.commit()

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
