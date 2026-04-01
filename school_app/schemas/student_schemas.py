# schemas/student_schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum


class GenderEnum(str, Enum):
    male   = "male"
    female = "female"
    other  = "other"


class StudentStatusEnum(str, Enum):
    active   = "active"
    inactive = "inactive"


# ══════════════════════════════════════════════
# StudentAdmissionInquiry
# ══════════════════════════════════════════════

class StudentInquiryCreate(BaseModel):
    student_name:        str
    gender:              Optional[GenderEnum] = None
    age:                 Optional[int]        = None
    class_id:            Optional[int]        = None
    guardian_name:       Optional[str]        = None
    guardian_phone:      Optional[str]        = None
    guardian_occupation: Optional[str]        = None
    guardian_gender:     Optional[GenderEnum] = None


class StudentInquiryUpdate(BaseModel):
    student_name:        Optional[str]        = None
    gender:              Optional[GenderEnum] = None
    age:                 Optional[int]        = None
    class_id:            Optional[int]        = None
    guardian_name:       Optional[str]        = None
    guardian_phone:      Optional[str]        = None
    guardian_occupation: Optional[str]        = None
    guardian_gender:     Optional[GenderEnum] = None


class StudentInquiryResponse(BaseModel):
    student_inq_id:      int
    student_name:        str
    gender:              Optional[GenderEnum]
    age:                 Optional[int]
    class_id:            Optional[int]
    guardian_name:       Optional[str]
    guardian_phone:      Optional[str]
    guardian_occupation: Optional[str]
    guardian_gender:     Optional[GenderEnum]
    created_at:          datetime
    updated_at:          datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════
# Student
# ══════════════════════════════════════════════

class StudentCreate(BaseModel):
    school_id:           int
    class_id:            int
    section_id:          int
    student_inq_id:      Optional[int]      = None
    student_roll_id:     Optional[str]      = None
    first_name:          str
    last_name:           Optional[str]      = None
    gender:              Optional[str]      = None
    dob:                 Optional[date]     = None
    age:                 Optional[int]      = None
    email:               Optional[str]      = None
    phone:               Optional[str]      = None
    address_line1:       Optional[str]      = None
    address_line2:       Optional[str]      = None
    city:                Optional[str]      = None
    state:               Optional[str]      = None
    country:             Optional[str]      = None
    postal_code:         Optional[str]      = None
    blood_group:         Optional[str]      = None
    emergency_contact:   Optional[str]      = None
    guardian_first_name: Optional[str]      = None
    guardian_last_name:  Optional[str]      = None
    guardian_phone:      str
    guardian_email:      Optional[str]      = None
    guardian_gender:     Optional[str]      = None
    enroll_date:         Optional[date]     = None
    status:              Optional[str]      = "active"


class StudentUpdate(BaseModel):
    class_id:            Optional[int]      = None
    section_id:          Optional[int]      = None
    student_inq_id:      Optional[int]      = None
    student_roll_id:     Optional[str]      = None
    first_name:          Optional[str]      = None
    last_name:           Optional[str]      = None
    gender:              Optional[str]      = None
    dob:                 Optional[date]     = None
    age:                 Optional[int]      = None
    email:               Optional[str]      = None
    phone:               Optional[str]      = None
    address_line1:       Optional[str]      = None
    address_line2:       Optional[str]      = None
    city:                Optional[str]      = None
    state:               Optional[str]      = None
    country:             Optional[str]      = None
    postal_code:         Optional[str]      = None
    blood_group:         Optional[str]      = None
    emergency_contact:   Optional[str]      = None
    guardian_first_name: Optional[str]      = None
    guardian_last_name:  Optional[str]      = None
    guardian_phone:      Optional[str]      = None
    guardian_email:      Optional[str]      = None
    guardian_gender:     Optional[str]      = None
    enroll_date:         Optional[date]     = None
    status:              Optional[str]      = None


class StudentMappingUpdate(BaseModel):
    class_id:        Optional[int]  = None
    section_id:      Optional[int]  = None
    enroll_date:     Optional[date] = None
    valid_from_date: Optional[date] = None
    valid_to_date:   Optional[date] = None
    status:          Optional[str]  = None
    is_active:       Optional[bool] = None
