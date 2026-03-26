# schemas/school_group_schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum


class SchoolGroupStatus(str, Enum):
    active   = "active"
    inactive = "inactive"
    expired  = "expired"


# ─────────────────────────────────────────────
# Create
# ─────────────────────────────────────────────

class SchoolGroupCreateRequest(BaseModel):
    """Payload to create a new school group."""
    school_id:     int                       = Field(..., description="ID of the parent school")
    group_name:    str                       = Field(..., max_length=255, description="Name of the group")
    description:   Optional[str]            = Field(None, description="Optional description")
    start_date:    Optional[date]           = Field(None, description="Group start date")
    end_date:      Optional[date]           = Field(None, description="Group end date")
    validity_days: Optional[int]            = Field(None, ge=1, description="Validity in days")
    status:        SchoolGroupStatus        = Field(SchoolGroupStatus.active, description="Group status")

    model_config = {
        "json_schema_extra": {
            "example": {
                "school_id":     1,
                "group_name":    "Grade 10 - Section A",
                "description":   "Main group for grade 10 section A students",
                "start_date":    "2025-06-01",
                "end_date":      "2026-03-31",
                "validity_days": 365,
                "status":        "active"
            }
        }
    }


# ─────────────────────────────────────────────
# Update
# ─────────────────────────────────────────────

class SchoolGroupUpdateRequest(BaseModel):
    """All fields are optional — only provided fields will be updated."""
    group_name:    Optional[str]            = Field(None, max_length=255)
    description:   Optional[str]           = Field(None)
    start_date:    Optional[date]          = Field(None)
    end_date:      Optional[date]          = Field(None)
    validity_days: Optional[int]           = Field(None, ge=1)
    status:        Optional[SchoolGroupStatus] = Field(None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "group_name": "Grade 10 - Section B",
                "status":     "inactive"
            }
        }
    }


# ─────────────────────────────────────────────
# Response
# ─────────────────────────────────────────────

class SchoolGroupResponse(BaseModel):
    """Full representation of a school group row."""
    school_group_id: int
    school_id:       int
    group_name:      str
    description:     Optional[str]
    start_date:      Optional[date]
    end_date:        Optional[date]
    validity_days:   Optional[int]
    status:          SchoolGroupStatus
    created_at:      datetime
    updated_at:      datetime

    model_config = {"from_attributes": True}
