# schemas/custom_alarm_schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import date


class CustomAlarmCreate(BaseModel):
    class_id:   Optional[int] = None
    section_id: Optional[int] = None
    message:    Optional[str] = None
    alarm_date: date
    slot_time:  Optional[str] = None


class CustomAlarmUpdate(BaseModel):
    class_id:   Optional[int]  = None
    section_id: Optional[int]  = None
    message:    Optional[str]  = None
    alarm_date: Optional[date] = None
    slot_time:  Optional[str]  = None
