# schemas/attendance_schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
import enum


class AttendanceStatusEnum(str, enum.Enum):
    P = "P"  # Present
    A = "A"  # Absent


# ══════════════════════════════════════════════
# Employee Attendance
# ══════════════════════════════════════════════

class EmpAttendanceItem(BaseModel):
    emp_id: int
    status: AttendanceStatusEnum

    model_config = {
        "json_schema_extra": {"example": {"emp_id": 1, "status": "P"}}
    }


class EmpAttendanceBulkCreate(BaseModel):
    school_group_id: int
    attendance_dt:   date
    employees:       List[EmpAttendanceItem]

    model_config = {
        "json_schema_extra": {
            "example": {
                "school_group_id": 1,
                "attendance_dt": "2024-06-01",
                "employees": [
                    {"emp_id": 1, "status": "P"},
                    {"emp_id": 2, "status": "A"},
                ]
            }
        }
    }


class EmpAttendanceUpdate(BaseModel):
    status: AttendanceStatusEnum

    model_config = {
        "json_schema_extra": {"example": {"status": "P"}}
    }


# ══════════════════════════════════════════════
# Student Attendance
# ══════════════════════════════════════════════

class StudentAttendanceItem(BaseModel):
    student_id: int
    status:     AttendanceStatusEnum

    model_config = {
        "json_schema_extra": {"example": {"student_id": 1, "status": "P"}}
    }


class StudentAttendanceBulkCreate(BaseModel):
    class_id:        int
    section_id:      int
    school_group_id: int
    attendance_dt:   date
    students:        List[StudentAttendanceItem]

    model_config = {
        "json_schema_extra": {
            "example": {
                "class_id": 1,
                "section_id": 1,
                "school_group_id": 1,
                "attendance_dt": "2024-06-01",
                "students": [
                    {"student_id": 1, "status": "P"},
                    {"student_id": 2, "status": "A"},
                ]
            }
        }
    }


class StudentAttendanceUpdate(BaseModel):
    status: AttendanceStatusEnum

    model_config = {
        "json_schema_extra": {"example": {"status": "A"}}
    }
