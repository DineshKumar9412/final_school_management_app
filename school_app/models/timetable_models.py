# models/timetable_models.py
from sqlalchemy import BigInteger, String, Integer, Date, Time, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import datetime
from typing import Optional
import datetime as dt


class TimeTable(Base):
    __tablename__ = "time_table"

    id:                Mapped[int]                    = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_id:          Mapped[Optional[int]]          = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id",          ondelete="SET NULL"), nullable=True)
    section_id:        Mapped[Optional[int]]          = mapped_column(BigInteger, ForeignKey("school_stream_class_section.section_id", ondelete="SET NULL"), nullable=True)
    school_id:         Mapped[Optional[int]]          = mapped_column(BigInteger, ForeignKey("school.school_id",                      ondelete="SET NULL"), nullable=True)
    school_table_name: Mapped[Optional[str]]          = mapped_column(String(100), nullable=True)
    school_group_id:   Mapped[Optional[int]]          = mapped_column(BigInteger, ForeignKey("school_group.school_group_id",          ondelete="SET NULL"), nullable=True)
    subject_id:        Mapped[Optional[int]]          = mapped_column(BigInteger, ForeignKey("school_stream_subject.subject_id",      ondelete="SET NULL"), nullable=True)
    type:              Mapped[Optional[str]]          = mapped_column(String(1),   nullable=True)
    date:              Mapped[Optional[dt.date]]      = mapped_column(Date,        nullable=True)
    start_time:        Mapped[dt.time]                = mapped_column(Time,        nullable=False)
    start_ampm:        Mapped[str]                    = mapped_column(String(2),   nullable=False)
    end_time:          Mapped[dt.time]                = mapped_column(Time,        nullable=False)
    end_ampm:          Mapped[str]                    = mapped_column(String(2),   nullable=False)
    duration:          Mapped[int]                    = mapped_column(Integer,     nullable=False)
    day:               Mapped[Optional[str]]          = mapped_column(String(10),  nullable=True)
    created_at:        Mapped[datetime]               = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at:        Mapped[datetime]               = mapped_column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)
