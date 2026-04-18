# schemas/announcement_schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AnnouncementCreate(BaseModel):
    class_id:         Optional[int] = None
    section_id:       Optional[int] = None
    school_stream_id: Optional[int] = None
    title:            Optional[str] = Field(None, max_length=100)
    description:      Optional[str] = Field(None, max_length=1000)
    url:              Optional[str] = Field(None, max_length=1000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "class_id":         1,
                "section_id":       1,
                "school_stream_id": 1,
                "title":            "Parent-Teacher Meeting",
                "description":      "PTM scheduled for all students of Class 10.",
                "url":              None,
            }
        }
    }


class AnnouncementUpdate(BaseModel):
    class_id:         Optional[int] = None
    section_id:       Optional[int] = None
    school_stream_id: Optional[int] = None
    title:            Optional[str] = Field(None, max_length=100)
    description:      Optional[str] = Field(None, max_length=1000)
    url:              Optional[str] = Field(None, max_length=1000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "title":       "PTM Rescheduled",
                "description": "PTM has been rescheduled to next Monday.",
            }
        }
    }


class AnnouncementResponse(BaseModel):
    id:           int
    class_id:     Optional[int]
    class_code:   Optional[str]
    section_id:   Optional[int]
    section_name: Optional[str]
    title:        Optional[str]
    description:  Optional[str]
    has_file:     bool
    url:          Optional[str]
    created_at:   datetime
    updated_at:   datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id":           1,
                "class_id":     1,
                "class_code":   "10",
                "section_id":   1,
                "section_name": "Rose",
                "title":        "Parent-Teacher Meeting",
                "description":  "PTM scheduled for all students of Class 10.",
                "has_file":     False,
                "url":          None,
                "created_at":   "2024-01-01T10:00:00",
                "updated_at":   "2024-01-01T10:00:00",
            }
        }
    }
