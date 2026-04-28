# schemas/android_teacher_schemas.py
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class AttendanceEntry(BaseModel):
    student_id: int
    status: str  # "P" / "A" / "L"

class BulkAttendanceRequest(BaseModel):
    class_id:   int
    section_id: int
    date:       date
    records:    List[AttendanceEntry]

class DiaryCreateRequest(BaseModel):
    class_id:    int
    section_id:  int
    subject_id:  Optional[int]  = None
    task_title:  Optional[str]  = None
    description: Optional[str]  = None
    diary_date:  Optional[date] = None

class DiaryUpdateRequest(BaseModel):
    task_title:  Optional[str]  = None
    description: Optional[str]  = None
    subject_id:  Optional[int]  = None
    diary_date:  Optional[date] = None

class AnnouncementCreateRequest(BaseModel):
    class_id:    Optional[int] = None
    section_id:  Optional[int] = None
    title:       Optional[str] = None
    description: Optional[str] = None
    url:         Optional[str] = None
    category:    Optional[str] = None  # EXAMS / EVENTS / CAMPUS / GENERAL

class AnnouncementUpdateRequest(BaseModel):
    class_id:    Optional[int] = None
    section_id:  Optional[int] = None
    title:       Optional[str] = None
    description: Optional[str] = None
    url:         Optional[str] = None
    category:    Optional[str] = None

class DailyTaskCreateRequest(BaseModel):
    class_id:    Optional[int]  = None
    section_id:  Optional[int]  = None
    title:       Optional[str]  = None    # stored as prefix in message
    message:     Optional[str]  = None    # notification body
    alarm_date:  date
    slot_time:   Optional[str]  = None    # e.g. "09:34"

class MarkEntry(BaseModel):
    student_id: int
    mark:       float

class BulkMarksSubmitRequest(BaseModel):
    timetable_id: int
    records:      List[MarkEntry]

class LeaveApplyRequest(BaseModel):
    reason:  str
    from_dt: date
    to_date: date
    type:    Optional[str] = None  # "Full" / "First Half" / "Second Half"

class SendMessageRequest(BaseModel):
    message: str

class MicroScheduleCreateRequest(BaseModel):
    class_id:    Optional[int]  = None
    section_id:  Optional[int]  = None
    subject_id:  Optional[int]  = None
    title:       Optional[str]  = None
    description: Optional[str]  = None
    schedule_dt: date

class MicroScheduleUpdateRequest(BaseModel):
    class_id:    Optional[int]  = None
    section_id:  Optional[int]  = None
    subject_id:  Optional[int]  = None
    title:       Optional[str]  = None
    description: Optional[str]  = None
    schedule_dt: Optional[date] = None

class AssignmentCreateRequest(BaseModel):
    title:       Optional[str]  = None
    description: Optional[str]  = None
    class_id:    int
    section_id:  int
    subject_id:  Optional[int]  = None
    group_name:  Optional[str]  = None
    due_date:    Optional[date] = None

class AssignmentUpdateRequest(BaseModel):
    title:       Optional[str]  = None
    description: Optional[str]  = None
    class_id:    Optional[int]  = None
    section_id:  Optional[int]  = None
    subject_id:  Optional[int]  = None
    group_name:  Optional[str]  = None
    due_date:    Optional[date] = None
    status:      Optional[int]  = None
