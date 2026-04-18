# schemas/class_teacher_schemas.py
from pydantic import BaseModel
from typing import Optional


# ── Assign a CLASS TEACHER (role_id required, subject optional) ──────────────
class ClassTeacherCreate(BaseModel):
    emp_id:     int
    role_id:    int
    class_id:   int
    section_id: int
    subject_id: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "emp_id":     8,
                "role_id":    2,
                "class_id":   1,
                "section_id": 1,
            }
        }
    }


# ── Assign a SUBJECT TEACHER (subject_id required, no role_id) ───────────────
class SubjectTeacherCreate(BaseModel):
    emp_id:     int
    class_id:   int
    section_id: int
    subject_id: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "emp_id":     2026003,
                "class_id":   1,
                "section_id": 1,
                "subject_id": 2,
            }
        }
    }


# ── kept for backward compat (used by update endpoint) ───────────────────────
class ClassSectionTeacherCreate(BaseModel):
    emp_id:     int
    role_id:    Optional[int] = None
    class_id:   int
    section_id: int
    subject_id: Optional[int] = None


class ClassSectionTeacherUpdate(BaseModel):
    emp_id:     Optional[int] = None
    role_id:    Optional[int] = None
    class_id:   Optional[int] = None
    section_id: Optional[int] = None
    subject_id: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "emp_id":     2,
                "subject_id": 3,
            }
        }
    }
