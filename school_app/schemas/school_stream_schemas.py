# schemas/school_stream_schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum


class SchoolGroupStatus(str, Enum):
    active   = "active"
    inactive = "inactive"
    expired  = "expired"


# ══════════════════════════════════════════════
# SchoolGroup
# ══════════════════════════════════════════════

class SchoolGroupCreateRequest(BaseModel):
    school_id:  int
    group_name: str = Field(..., max_length=255)
    status:     SchoolGroupStatus = Field(SchoolGroupStatus.active)

    model_config = {
        "json_schema_extra": {
            "example": {
                "school_id":  1,
                "group_name": "Primary",
                "status":     "active"
            }
        }
    }


class SchoolGroupUpdateRequest(BaseModel):
    group_name: Optional[str]               = Field(None, max_length=255)
    status:     Optional[SchoolGroupStatus] = Field(None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "group_name": "Higher Secondary",
                "status":     "inactive"
            }
        }
    }


class SchoolGroupResponse(BaseModel):
    school_group_id: int
    school_id:       int
    group_name:      str
    status:          SchoolGroupStatus

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "school_group_id": 1,
                "school_id":       1,
                "group_name":      "Primary",
                "status":          "active"
            }
        }
    }


# ══════════════════════════════════════════════
# Shared Status
# ══════════════════════════════════════════════

class StatusEnum(str, Enum):
    draft    = "draft"
    active   = "active"
    inactive = "inactive"
    archived = "archived"


# ══════════════════════════════════════════════
# SchoolStream
# ══════════════════════════════════════════════

class SchoolStreamCreate(BaseModel):
    school_id:       int
    school_group_id: int
    stream_name:     str
    stream_code:     Optional[str]        = None
    status:          Optional[StatusEnum] = StatusEnum.active

    model_config = {
        "json_schema_extra": {
            "example": {
                "school_id":       1,
                "school_group_id": 1,
                "stream_name":     "Science",
                "stream_code":     "SCI",
                "status":          "active"
            }
        }
    }


class SchoolStreamUpdate(BaseModel):
    school_group_id: Optional[int]        = None
    stream_name:     Optional[str]        = None
    status:          Optional[StatusEnum] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "stream_name": "Commerce",
                "status":      "active"
            }
        }
    }


class SchoolStreamResponse(BaseModel):
    school_stream_id: int
    school_id:        int
    school_group_id:  int
    stream_name:      str
    stream_code:      Optional[str]
    status:           StatusEnum

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "school_stream_id": 1,
                "school_id":        1,
                "school_group_id":  1,
                "stream_name":      "Science",
                "stream_code":      "SCI",
                "status":           "active"
            }
        }
    }


# ══════════════════════════════════════════════
# SchoolStreamClass
# ══════════════════════════════════════════════

class SchoolStreamClassCreate(BaseModel):
    school_id:        int
    school_group_id:  int
    school_stream_id: Optional[int] = None
    class_name:       Optional[str] = None
    class_code:       str
    status:           Optional[StatusEnum] = StatusEnum.active

    model_config = {
        "json_schema_extra": {
            "example": {
                "school_id":        1,
                "school_group_id":  1,
                "school_stream_id": 1,
                "class_name":       "Class 10",
                "class_code":       "10",
                "status":           "active"
            }
        }
    }


class SchoolStreamClassUpdate(BaseModel):
    school_group_id:  Optional[int]        = None
    school_stream_id: Optional[int]        = None
    class_name:       Optional[str]        = None
    class_code:       Optional[str]        = None
    description:      Optional[str]        = None
    status:           Optional[StatusEnum] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "class_name": "Class 11",
                "class_code": "11",
                "status":     "active"
            }
        }
    }


class SchoolStreamClassResponse(BaseModel):
    class_id:         int
    school_id:        int
    school_group_id:  int
    school_stream_id: Optional[int]
    class_name:       Optional[str]
    class_code:       Optional[str]
    status:           StatusEnum

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "class_id":         1,
                "school_id":        1,
                "school_group_id":  1,
                "school_stream_id": 1,
                "class_name":       "Class 10",
                "class_code":       "10",
                "status":           "active"
            }
        }
    }


# ══════════════════════════════════════════════
# SchoolStreamClassSection
# ══════════════════════════════════════════════

class SchoolStreamClassSectionCreate(BaseModel):
    school_id:        int
    class_id:         int
    school_stream_id: Optional[int] = None
    section_code:     str = Field(..., max_length=10)
    section_name:     str = Field(..., max_length=200)
    status:           Optional[StatusEnum] = StatusEnum.active

    model_config = {
        "json_schema_extra": {
            "example": {
                "school_id":        1,
                "class_id":         1,
                "school_stream_id": None,
                "section_code":     "A",
                "section_name":     "Rose",
                "status":           "active"
            }
        }
    }


class SchoolStreamClassSectionUpdate(BaseModel):
    class_id:         Optional[int]        = None
    school_stream_id: Optional[int]        = None
    section_code:     Optional[str]        = Field(None, max_length=10)
    section_name:     Optional[str]        = Field(None, max_length=200)
    description:      Optional[str]        = None
    status:           Optional[StatusEnum] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "section_code": "B",
                "section_name": "Lily",
                "status":       "active"
            }
        }
    }


class SchoolStreamClassSectionResponse(BaseModel):
    section_id:       int
    school_id:        int
    class_id:         int
    school_stream_id: Optional[int]
    section_code:     str
    section_name:     str
    status:           StatusEnum

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "section_id":       1,
                "school_id":        1,
                "class_id":         1,
                "school_stream_id": None,
                "section_code":     "A",
                "section_name":     "Rose",
                "status":           "active"
            }
        }
    }


# ══════════════════════════════════════════════
# SchoolStreamSubject
# ══════════════════════════════════════════════

class SchoolStreamSubjectCreate(BaseModel):
    school_id:    int
    class_id:     int
    subject_name: str
    description:  Optional[str] = None
    status:       Optional[StatusEnum] = StatusEnum.active

    model_config = {
        "json_schema_extra": {
            "example": {
                "school_id":    1,
                "class_id":     1,
                "subject_name": "Mathematics",
                "description":  None,
                "status":       "active"
            }
        }
    }


class SchoolStreamSubjectUpdate(BaseModel):
    class_id:     Optional[int]        = None
    subject_name: Optional[str]        = None
    description:  Optional[str]        = None
    status:       Optional[StatusEnum] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "subject_name": "Physics",
                "status":       "active"
            }
        }
    }


class SchoolStreamSubjectResponse(BaseModel):
    subject_id:   int
    school_id:    int
    class_id:     int
    subject_name: str
    status:       StatusEnum

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "subject_id":   1,
                "school_id":    1,
                "class_id":     1,
                "subject_name": "Mathematics",
                "status":       "active"
            }
        }
    }


# ══════════════════════════════════════════════
# Shared
# ══════════════════════════════════════════════

class DropdownItem(BaseModel):
    id:   int
    name: str

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    total: int
    page:  int
    limit: int
    data:  list
