# schemas/student_diary_schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


class StudentDiaryCreate(BaseModel):
    student_id: int
    class_id:   Optional[int]  = None
    section_id: Optional[int]  = None
    subject_id: Optional[int]  = None
    task_title: Optional[str]  = Field(None, max_length=100)
    dairy_date: Optional[date] = None
    status:     Optional[str]  = Field(None, max_length=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "student_id": 1,
                "class_id":   1,
                "section_id": 1,
                "subject_id": 1,
                "task_title": "Math Homework",
                "dairy_date": "2024-08-15",
                "status":     "P",
            }
        }
    }


class StudentDiaryUpdate(BaseModel):
    student_id: Optional[int]  = None
    class_id:   Optional[int]  = None
    section_id: Optional[int]  = None
    subject_id: Optional[int]  = None
    task_title: Optional[str]  = Field(None, max_length=100)
    dairy_date: Optional[date] = None
    status:     Optional[str]  = Field(None, max_length=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_title": "Science Project",
                "status":     "C",
            }
        }
    }


class StudentDiaryResponse(BaseModel):
    id:           int
    student_id:   int
    student_name: Optional[str]
    class_id:     Optional[int]
    class_code:   Optional[str]
    section_id:   Optional[int]
    section_name: Optional[str]
    subject_id:   Optional[int]
    subject_name: Optional[str]
    task_title:   Optional[str]
    dairy_date:   Optional[date]
    status:       Optional[str]
    created_at:   datetime
    updated_at:   datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id":           1,
                "student_id":   1,
                "student_name": "John Doe",
                "class_id":     1,
                "class_code":   "10",
                "section_id":   1,
                "section_name": "Rose",
                "subject_id":   1,
                "subject_name": "Mathematics",
                "task_title":   "Math Homework",
                "dairy_date":   "2024-08-15",
                "status":       "P",
                "created_at":   "2024-01-01T10:00:00",
                "updated_at":   "2024-01-01T10:00:00",
            }
        }
    }
