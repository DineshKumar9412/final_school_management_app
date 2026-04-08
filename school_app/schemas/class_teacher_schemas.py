# schemas/class_teacher_schemas.py
from pydantic import BaseModel
from typing import Optional


class ClassSectionTeacherCreate(BaseModel):
    emp_id:    int
    class_id:  int
    subject_id: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "emp_id":    1,
                "class_id":  1,
                "subject_id": 2,
            }
        }
    }


class ClassSectionTeacherUpdate(BaseModel):
    emp_id:    Optional[int] = None
    class_id:  Optional[int] = None
    subject_id: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "emp_id": 2,
                "subject_id": 3,
            }
        }
    }
