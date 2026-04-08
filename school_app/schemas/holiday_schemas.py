# schemas/holiday_schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


class HolidayCreate(BaseModel):
    holiday_date: date
    title:        str           = Field(..., max_length=100)
    description:  Optional[str] = Field(None, max_length=1000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "holiday_date": "2024-08-15",
                "title":        "Independence Day",
                "description":  "National holiday celebrating independence.",
            }
        }
    }


class HolidayUpdate(BaseModel):
    holiday_date: Optional[date] = None
    title:        Optional[str]  = Field(None, max_length=100)
    description:  Optional[str]  = Field(None, max_length=1000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "title":       "Independence Day (Updated)",
                "description": "Updated description.",
            }
        }
    }


class HolidayResponse(BaseModel):
    id:           int
    holiday_date: date
    title:        str
    description:  Optional[str]
    created_at:   datetime
    updated_at:   datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id":           1,
                "holiday_date": "2024-08-15",
                "title":        "Independence Day",
                "description":  "National holiday celebrating independence.",
                "created_at":   "2024-01-01T10:00:00",
                "updated_at":   "2024-01-01T10:00:00",
            }
        }
    }
