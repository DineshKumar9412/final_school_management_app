# schemas/emp_leave_request_schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum


class LeaveTypeEnum(str, Enum):
    full        = "Full"
    first_half  = "First Half"
    second_half = "Second Half"


class LeaveStatusEnum(str, Enum):
    approved = "Approved"
    rejected = "Rejected"
    pending  = "Pending"


class EmpLeaveRequestCreate(BaseModel):
    emp_id:  Optional[int]            = None
    reason:  str                      = Field(..., max_length=1000)
    from_dt: date
    to_date: date
    type:    Optional[LeaveTypeEnum]  = None
    status:  Optional[LeaveStatusEnum]= LeaveStatusEnum.pending

    model_config = {
        "json_schema_extra": {
            "example": {
                "emp_id":  1,
                "reason":  "Family function",
                "from_dt": "2024-08-15",
                "to_date": "2024-08-16",
                "type":    "Full",
                "status":  "Pending",
            }
        }
    }


class EmpLeaveRequestUpdate(BaseModel):
    emp_id:  Optional[int]             = None
    reason:  Optional[str]             = Field(None, max_length=1000)
    from_dt: Optional[date]            = None
    to_date: Optional[date]            = None
    type:    Optional[LeaveTypeEnum]   = None
    status:  Optional[LeaveStatusEnum] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "Approved",
            }
        }
    }


class EmpLeaveRequestResponse(BaseModel):
    id:           int
    emp_id:       Optional[int]
    emp_name:     Optional[str]
    reason:       str
    from_dt:      date
    to_date:      date
    type:         Optional[LeaveTypeEnum]
    status:       Optional[LeaveStatusEnum]
    has_attachment: bool
    created_at:   datetime
    updated_at:   datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id":             1,
                "emp_id":         1,
                "emp_name":       "John Doe",
                "reason":         "Family function",
                "from_dt":        "2024-08-15",
                "to_date":        "2024-08-16",
                "type":           "Full",
                "status":         "Pending",
                "has_attachment": False,
                "created_at":     "2024-01-01T10:00:00",
                "updated_at":     "2024-01-01T10:00:00",
            }
        }
    }
