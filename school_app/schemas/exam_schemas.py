# schemas/exam_schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, time


# ══════════════════════════════════════════════
# Grade
# ══════════════════════════════════════════════

class GradeCreate(BaseModel):
    start_range: float
    end_range:   float
    grade:       Optional[str] = Field(None, max_length=10)

    model_config = {
        "json_schema_extra": {
            "example": {"start_range": 90.0, "end_range": 100.0, "grade": "A+"}
        }
    }


# ══════════════════════════════════════════════
# Exam
# ══════════════════════════════════════════════

class ExamCreate(BaseModel):
    exam_name:        str
    school_stream_id: int
    session_yr:       str
    exam_description: str
    is_active:        Optional[bool] = True

    model_config = {
        "json_schema_extra": {
            "example": {
                "exam_name": "Mid Term 2024", "school_stream_id": 1,
                "session_yr": "2024-25", "exam_description": "Mid term exam", "is_active": True
            }
        }
    }


class ExamUpdate(BaseModel):
    exam_name:        Optional[str]  = None
    school_stream_id: Optional[int]  = None
    session_yr:       Optional[str]  = None
    exam_description: Optional[str]  = None
    is_active:        Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "example": {"exam_name": "Final Term 2024", "is_active": True}
        }
    }


# ══════════════════════════════════════════════
# ExamTimetable
# ══════════════════════════════════════════════

class ExamTimetableCreate(BaseModel):
    exam_id:          int
    school_stream_id: int
    school_group_id:  int
    subject_id:       int
    total_marks:      float
    pass_mark:        float
    exam_start_date:  datetime
    exam_end_date:    Optional[datetime] = None
    start_time:       time
    start_ampm:       str
    end_time:         time
    end_ampm:         str
    is_active:        Optional[bool] = True

    model_config = {
        "json_schema_extra": {
            "example": {
                "exam_id": 1, "school_stream_id": 1, "school_group_id": 1,
                "subject_id": 1, "total_marks": 100.0, "pass_mark": 35.0,
                "exam_start_date": "2024-11-01T09:00:00",
                "exam_end_date": "2024-11-01T12:00:00",
                "start_time": "09:00:00", "start_ampm": "AM",
                "end_time": "12:00:00", "end_ampm": "PM", "is_active": True
            }
        }
    }


class ExamTimetableUpdate(BaseModel):
    exam_id:          Optional[int]      = None
    school_stream_id: Optional[int]      = None
    school_group_id:  Optional[int]      = None
    subject_id:       Optional[int]      = None
    total_marks:      Optional[float]    = None
    pass_mark:        Optional[float]    = None
    exam_start_date:  Optional[datetime] = None
    exam_end_date:    Optional[datetime] = None
    start_time:       Optional[time]     = None
    start_ampm:       Optional[str]      = None
    end_time:         Optional[time]     = None
    end_ampm:         Optional[str]      = None
    is_active:        Optional[bool]     = None

    model_config = {
        "json_schema_extra": {
            "example": {"total_marks": 150.0, "pass_mark": 50.0}
        }
    }


# ══════════════════════════════════════════════
# StudentMarks
# ══════════════════════════════════════════════

class SubjectMark(BaseModel):
    subject_id: int
    mark:       float


class StudentMarksCreate(BaseModel):
    student_id: int
    class_id:   int
    subjects:   List[SubjectMark]

    model_config = {
        "json_schema_extra": {
            "example": {
                "student_id": 1, "class_id": 1,
                "subjects": [
                    {"subject_id": 1, "mark": 85.0},
                    {"subject_id": 2, "mark": 90.0}
                ]
            }
        }
    }


# ══════════════════════════════════════════════
# OnlineExam
# ══════════════════════════════════════════════

class OnlineExamCreate(BaseModel):
    class_id:   int
    subject_id: int
    title:      Optional[str] = None
    exam_code:  Optional[str] = None
    url:        Optional[str] = None
    duration:   Optional[str] = None
    start_date: date
    end_date:   date

    model_config = {
        "json_schema_extra": {
            "example": {
                "class_id": 1, "subject_id": 1, "title": "Math Online Exam",
                "exam_code": "MATH001", "url": "https://exam.school.com/math",
                "duration": "60", "start_date": "2024-11-01", "end_date": "2024-11-01"
            }
        }
    }


class OnlineExamUpdate(BaseModel):
    class_id:   Optional[int]  = None
    subject_id: Optional[int]  = None
    title:      Optional[str]  = None
    exam_code:  Optional[str]  = None
    url:        Optional[str]  = None
    duration:   Optional[str]  = None
    start_date: Optional[date] = None
    end_date:   Optional[date] = None

    model_config = {
        "json_schema_extra": {
            "example": {"url": "https://exam.school.com/updated", "duration": "90"}
        }
    }


# ══════════════════════════════════════════════
# OnlineClass
# ══════════════════════════════════════════════

class OnlineClassCreate(BaseModel):
    class_id:   int
    subject_id: int
    title:      Optional[str] = None
    url:        Optional[str] = None
    duration:   Optional[str] = None
    start_date: date
    end_date:   date

    model_config = {
        "json_schema_extra": {
            "example": {
                "class_id": 1, "subject_id": 1, "title": "Math Live Class",
                "url": "https://meet.school.com/math",
                "duration": "60", "start_date": "2024-11-01", "end_date": "2024-11-01"
            }
        }
    }


class OnlineClassUpdate(BaseModel):
    class_id:   Optional[int]  = None
    subject_id: Optional[int]  = None
    title:      Optional[str]  = None
    url:        Optional[str]  = None
    duration:   Optional[str]  = None
    start_date: Optional[date] = None
    end_date:   Optional[date] = None

    model_config = {
        "json_schema_extra": {
            "example": {"url": "https://meet.school.com/updated", "duration": "90"}
        }
    }
