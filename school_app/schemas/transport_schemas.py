# schemas/transport_schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, time
from decimal import Decimal


# ══════════════════════════════════════════════
# VehicleDetails
# ══════════════════════════════════════════════

class VehicleDetailsCreate(BaseModel):
    vehicle_no:       Optional[str] = Field(None, max_length=15)
    vehicle_capacity: Optional[int] = None
    vehicle_reg_no:   Optional[str] = Field(None, max_length=15)
    status:           Optional[str] = Field(None, max_length=1)
    driver_mob_no:    str           = Field(..., max_length=15)
    helper_mob_no:    str           = Field(..., max_length=15)

    model_config = {
        "json_schema_extra": {
            "example": {
                "vehicle_no": "TN01AB1234", "vehicle_capacity": 40,
                "vehicle_reg_no": "REG001", "status": "A",
                "driver_mob_no": "9876543210", "helper_mob_no": "9876543211",
            }
        }
    }


class VehicleDetailsUpdate(BaseModel):
    vehicle_no:       Optional[str] = Field(None, max_length=15)
    vehicle_capacity: Optional[int] = None
    vehicle_reg_no:   Optional[str] = Field(None, max_length=15)
    status:           Optional[str] = Field(None, max_length=1)
    driver_mob_no:    Optional[str] = Field(None, max_length=15)
    helper_mob_no:    Optional[str] = Field(None, max_length=15)

    model_config = {
        "json_schema_extra": {
            "example": {"vehicle_capacity": 45, "status": "I"}
        }
    }


class VehicleDetailsResponse(BaseModel):
    id:               int
    vehicle_no:       Optional[str]
    vehicle_capacity: Optional[int]
    vehicle_reg_no:   Optional[str]
    status:           Optional[str]
    driver_mob_no:    str
    helper_mob_no:    str
    created_at:       datetime
    updated_at:       datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════
# Routes
# ══════════════════════════════════════════════

class RoutesCreate(BaseModel):
    name:            str            = Field(..., max_length=100)
    vehicle_no:      Optional[str]  = Field(None, max_length=15)
    distance:        Optional[int]  = None
    status:          Optional[str]  = Field(None, max_length=1)
    pick_start_time: time
    pick_end_time:   time
    drop_start_time: time
    drop_end_time:   time

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Route A", "vehicle_no": "TN01AB1234",
                "distance": 15, "status": "A",
                "pick_start_time": "07:00:00", "pick_end_time": "08:00:00",
                "drop_start_time": "15:00:00", "drop_end_time": "16:00:00",
            }
        }
    }


class RoutesUpdate(BaseModel):
    name:            Optional[str]  = Field(None, max_length=100)
    vehicle_no:      Optional[str]  = Field(None, max_length=15)
    distance:        Optional[int]  = None
    status:          Optional[str]  = Field(None, max_length=1)
    pick_start_time: Optional[time] = None
    pick_end_time:   Optional[time] = None
    drop_start_time: Optional[time] = None
    drop_end_time:   Optional[time] = None

    model_config = {
        "json_schema_extra": {
            "example": {"name": "Route B", "distance": 20}
        }
    }


class RoutesResponse(BaseModel):
    id:               int
    name:             str
    vehicle_no:       Optional[str]
    distance:         Optional[int]
    status:           Optional[str]
    pick_start_time:  time
    pick_end_time:    time
    drop_start_time:  time
    drop_end_time:    time
    created_at:       datetime
    updated_at:       datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════
# VehicleRoutesMap
# ══════════════════════════════════════════════

class VehicleRoutesMapCreate(BaseModel):
    route_id:      Optional[int] = None
    vehicle_id:    Optional[int] = None
    driver_name:   str           = Field(..., max_length=50)
    helper_name:   str           = Field(..., max_length=50)
    driver_mob_no: Optional[str] = Field(None, max_length=15)
    helper_mob_no: Optional[str] = Field(None, max_length=15)

    model_config = {
        "json_schema_extra": {
            "example": {
                "route_id": 1, "vehicle_id": 1,
                "driver_name": "Rajan", "helper_name": "Kumar",
                "driver_mob_no": "9876543210", "helper_mob_no": "9876543211",
            }
        }
    }


class VehicleRoutesMapUpdate(BaseModel):
    route_id:      Optional[int] = None
    vehicle_id:    Optional[int] = None
    driver_name:   Optional[str] = Field(None, max_length=50)
    helper_name:   Optional[str] = Field(None, max_length=50)
    driver_mob_no: Optional[str] = Field(None, max_length=15)
    helper_mob_no: Optional[str] = Field(None, max_length=15)

    model_config = {
        "json_schema_extra": {
            "example": {"driver_name": "Suresh", "driver_mob_no": "9123456789"}
        }
    }


class VehicleRoutesMapResponse(BaseModel):
    id:            int
    route_id:      Optional[int]
    route_name:    Optional[str]
    vehicle_id:    Optional[int]
    vehicle_no:    Optional[str]
    driver_name:   str
    helper_name:   str
    driver_mob_no: Optional[str]
    helper_mob_no: Optional[str]
    created_at:    datetime
    updated_at:    datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════
# TransportationStudent
# ══════════════════════════════════════════════

class TransportationStudentCreate(BaseModel):
    vehicle_id: Optional[int] = None
    class_id:   Optional[int] = None
    section_id: Optional[int] = None
    student_id: Optional[int] = None
    group_id:   Optional[int] = None
    session_yr: Optional[str] = Field(None, max_length=10)

    model_config = {
        "json_schema_extra": {
            "example": {
                "vehicle_id": 1, "class_id": 1, "section_id": 1,
                "student_id": 1, "group_id": 1, "session_yr": "2024-25",
            }
        }
    }


class TransportationStudentUpdate(BaseModel):
    vehicle_id: Optional[int] = None
    class_id:   Optional[int] = None
    section_id: Optional[int] = None
    student_id: Optional[int] = None
    group_id:   Optional[int] = None
    session_yr: Optional[str] = Field(None, max_length=10)

    model_config = {
        "json_schema_extra": {
            "example": {"vehicle_id": 2, "session_yr": "2025-26"}
        }
    }


class TransportationStudentResponse(BaseModel):
    id:           int
    vehicle_id:   Optional[int]
    vehicle_no:   Optional[str]
    class_id:     Optional[int]
    class_code:   Optional[str]
    section_id:   Optional[int]
    section_name: Optional[str]
    student_id:   Optional[int]
    student_name: Optional[str]
    group_id:     Optional[int]
    group_name:   Optional[str]
    session_yr:   Optional[str]
    created_at:   datetime
    updated_at:   datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════
# VehicleExpenses
# ══════════════════════════════════════════════

class VehicleExpensesCreate(BaseModel):
    vehicle_id:  Optional[int]     = None
    session_yr:  Optional[str]     = Field(None, max_length=10)
    amount:      Optional[Decimal] = None
    date:        Optional[datetime]= None
    description: Optional[str]     = Field(None, max_length=100)

    model_config = {
        "json_schema_extra": {
            "example": {
                "vehicle_id": 1, "session_yr": "2024-25",
                "amount": "1500.00", "date": "2024-08-15T00:00:00",
                "description": "Fuel expense",
            }
        }
    }


class VehicleExpensesUpdate(BaseModel):
    vehicle_id:  Optional[int]     = None
    session_yr:  Optional[str]     = Field(None, max_length=10)
    amount:      Optional[Decimal] = None
    date:        Optional[datetime]= None
    description: Optional[str]     = Field(None, max_length=100)

    model_config = {
        "json_schema_extra": {
            "example": {"amount": "2000.00", "description": "Tyre replacement"}
        }
    }


class VehicleExpensesResponse(BaseModel):
    id:          int
    vehicle_id:  Optional[int]
    vehicle_no:  Optional[str]
    session_yr:  Optional[str]
    amount:      Optional[Decimal]
    date:        Optional[datetime]
    has_image:   bool
    description: Optional[str]
    created_at:  datetime
    updated_at:  datetime

    model_config = {"from_attributes": True}
