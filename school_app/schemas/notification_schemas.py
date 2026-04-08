# schemas/notification_schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class NotificationCreate(BaseModel):
    title:   str            = Field(..., max_length=100)
    message: Optional[str]  = Field(None, max_length=10000)
    role_id: Optional[int]  = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title":   "School Closed",
                "message": "School will remain closed tomorrow due to a public holiday.",
                "role_id": 1,
            }
        }
    }


class NotificationUpdate(BaseModel):
    title:   Optional[str] = Field(None, max_length=100)
    message: Optional[str] = Field(None, max_length=10000)
    role_id: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title":   "Updated: School Closed",
                "message": "School will remain closed for two days.",
            }
        }
    }


class NotificationResponse(BaseModel):
    id:         int
    title:      str
    message:    Optional[str]
    role_id:    Optional[int]
    role_name:  Optional[str]
    has_image:  bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id":         1,
                "title":      "School Closed",
                "message":    "School will remain closed tomorrow.",
                "role_id":    1,
                "role_name":  "Teacher",
                "has_image":  False,
                "created_at": "2024-01-01T10:00:00",
                "updated_at": "2024-01-01T10:00:00",
            }
        }
    }
