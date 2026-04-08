# schemas/timetable_schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import date, time


class TimeTableCreate(BaseModel):
    class_id:          int
    section_id:        int
    school_id:         int
    school_group_id:   int
    subject_id:        int
    school_table_name: Optional[str] = None
    type:              Optional[str] = None   # W = weekly, D = daily
    date:              Optional[date]= None
    start_time:        time
    start_ampm:        str
    end_time:          time
    end_ampm:          str
    duration:          int
    day:               Optional[str] = None   # Mon, Tue, Wed...

    model_config = {
        "json_schema_extra": {
            "example": {
                "class_id": 1, "section_id": 1, "school_id": 1,
                "school_group_id": 1, "subject_id": 1,
                "school_table_name": "2024-25 Timetable",
                "type": "W", "date": None,
                "start_time": "09:00:00", "start_ampm": "AM",
                "end_time": "10:00:00", "end_ampm": "AM",
                "duration": 60, "day": "Mon",
            }
        }
    }


class TimeTableUpdate(BaseModel):
    class_id:          Optional[int]  = None
    section_id:        Optional[int]  = None
    school_id:         Optional[int]  = None
    school_group_id:   Optional[int]  = None
    subject_id:        Optional[int]  = None
    school_table_name: Optional[str]  = None
    type:              Optional[str]  = None
    date:              Optional[date] = None
    start_time:        Optional[time] = None
    start_ampm:        Optional[str]  = None
    end_time:          Optional[time] = None
    end_ampm:          Optional[str]  = None
    duration:          Optional[int]  = None
    day:               Optional[str]  = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "start_time": "10:00:00", "start_ampm": "AM",
                "end_time": "11:00:00", "end_ampm": "AM",
                "duration": 60,
            }
        }
    }
