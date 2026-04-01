# schemas/employee_schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum


class GenderEnum(str, Enum):
    male   = "male"
    female = "female"
    other  = "other"


class EmployeeStatusEnum(str, Enum):
    teaching     = "teaching"
    non_teaching = "non teaching"


# ══════════════════════════════════════════════
# Role
# ══════════════════════════════════════════════

class RoleCreate(BaseModel):
    role_name: str
    is_active: Optional[bool] = True


class RoleUpdate(BaseModel):
    role_name: Optional[str]  = None
    is_active: Optional[bool] = None


class RoleResponse(BaseModel):
    role_id:   int
    role_name: Optional[str]
    is_active: Optional[bool]

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════
# Employee
# ══════════════════════════════════════════════

class EmployeeCreate(BaseModel):
    emp_id:        Optional[int]                    = None
    role_id:       Optional[int]                    = None
    first_name:    str
    last_name:     str
    DOB:           Optional[date]                   = None
    gender:        Optional[GenderEnum]             = None
    qualification: Optional[str]                    = None
    mobile:        Optional[str]                    = None
    address:       Optional[str]                    = None
    email:         Optional[EmailStr]               = None
    salary:        Optional[float]                  = None
    session_yr:    Optional[str]                    = None
    joining_dt:    Optional[date]                   = None
    status:        Optional[EmployeeStatusEnum]     = None
    is_active:     Optional[bool]                   = True


class EmployeeUpdate(BaseModel):
    role_id:       Optional[int]                    = None
    first_name:    Optional[str]                    = None
    last_name:     Optional[str]                    = None
    DOB:           Optional[date]                   = None
    gender:        Optional[GenderEnum]             = None
    qualification: Optional[str]                    = None
    mobile:        Optional[str]                    = None
    address:       Optional[str]                    = None
    email:         Optional[EmailStr]               = None
    salary:        Optional[float]                  = None
    session_yr:    Optional[str]                    = None
    joining_dt:    Optional[date]                   = None
    status:        Optional[EmployeeStatusEnum]     = None
    is_active:     Optional[bool]                   = None


# ══════════════════════════════════════════════
# Employee Class Mapping
# ══════════════════════════════════════════════

class EmployeeMappingCreate(BaseModel):
    emp_id:     int
    class_id:   int
    subject_id: int


class EmployeeMappingUpdate(BaseModel):
    class_id:   Optional[int] = None
    subject_id: Optional[int] = None
