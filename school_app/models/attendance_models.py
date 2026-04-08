# models/attendance_models.py
from sqlalchemy import BigInteger, Date, Enum, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import datetime, date
from typing import Optional
import enum


class AttendanceStatus(str, enum.Enum):
    P = "P"  # Present
    A = "A"  # Absent


class EmployeeAttendance(Base):
    __tablename__ = "emp_attendance"

    att_id:          Mapped[int]                      = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_group_id: Mapped[Optional[int]]            = mapped_column(BigInteger, ForeignKey("school_group.school_group_id", ondelete="SET NULL"), nullable=True)
    emp_id:          Mapped[Optional[int]]            = mapped_column(BigInteger, ForeignKey("employee.id", ondelete="SET NULL"), nullable=True)
    attendance_dt:   Mapped[date]                     = mapped_column(Date, nullable=False)
    status:          Mapped[Optional[AttendanceStatus]] = mapped_column(Enum(AttendanceStatus), nullable=True)
    created_at:      Mapped[datetime]                 = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at:      Mapped[datetime]                 = mapped_column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)


class StudentAttendance(Base):
    __tablename__ = "student_attendance"

    att_id:          Mapped[int]                      = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_id:        Mapped[Optional[int]]            = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id", ondelete="SET NULL"), nullable=True)
    section_id:      Mapped[Optional[int]]            = mapped_column(BigInteger, ForeignKey("school_stream_class_section.section_id", ondelete="SET NULL"), nullable=True)
    school_group_id: Mapped[Optional[int]]            = mapped_column(BigInteger, ForeignKey("school_group.school_group_id", ondelete="SET NULL"), nullable=True)
    student_id:      Mapped[Optional[int]]            = mapped_column(BigInteger, ForeignKey("student.student_id", ondelete="SET NULL"), nullable=True)
    attendance_dt:   Mapped[date]                     = mapped_column(Date, nullable=False)
    status:          Mapped[Optional[AttendanceStatus]] = mapped_column(Enum(AttendanceStatus), nullable=True)
    created_at:      Mapped[datetime]                 = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at:      Mapped[datetime]                 = mapped_column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)
