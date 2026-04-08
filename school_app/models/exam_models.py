# models/exam_models.py
from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Date, Boolean, Integer, DECIMAL, Time
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from database.base import Base
from datetime import datetime, date, time


class Grade(Base):
    __tablename__ = "grade"

    grade_id:    Mapped[int]        = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    start_range: Mapped[float]      = mapped_column(DECIMAL(18, 2), nullable=False)
    end_range:   Mapped[float]      = mapped_column(DECIMAL(18, 2), nullable=False)
    grade:       Mapped[str | None] = mapped_column(String(10))
    is_active:   Mapped[bool]       = mapped_column(Boolean, default=True)
    created_at:  Mapped[datetime]   = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at:  Mapped[datetime]   = mapped_column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class Exam(Base):
    __tablename__ = "exams"

    exam_id:          Mapped[int]        = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    exam_name:        Mapped[str]        = mapped_column(String(100), nullable=False)
    school_stream_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("school_stream.school_stream_id"))
    session_yr:       Mapped[str | None] = mapped_column(String(10))
    exam_description: Mapped[str | None] = mapped_column(String(100))
    is_active:        Mapped[bool]       = mapped_column(Boolean, default=True)
    created_at:       Mapped[datetime]   = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at:       Mapped[datetime]   = mapped_column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class ExamTimetable(Base):
    __tablename__ = "exam_timetable"

    timetable_id:     Mapped[int]             = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    exam_id:          Mapped[int | None]      = mapped_column(BigInteger, ForeignKey("exams.exam_id"))
    school_stream_id: Mapped[int | None]      = mapped_column(Integer, ForeignKey("school_stream.school_stream_id"))
    school_group_id:  Mapped[int | None]      = mapped_column(Integer, ForeignKey("school_group.school_group_id"))
    subject_id:       Mapped[int | None]      = mapped_column(Integer, ForeignKey("school_stream_subject.subject_id"))
    total_marks:      Mapped[float | None]    = mapped_column(DECIMAL(18, 2))
    pass_mark:        Mapped[float | None]    = mapped_column(DECIMAL(18, 2))
    exam_start_date:  Mapped[datetime | None] = mapped_column(DateTime)
    exam_end_date:    Mapped[datetime | None] = mapped_column(DateTime)
    start_time:       Mapped[time]            = mapped_column(Time, nullable=False)
    start_ampm:       Mapped[str]             = mapped_column(String(2), nullable=False, comment="AM / PM")
    end_time:         Mapped[time]            = mapped_column(Time, nullable=False)
    end_ampm:         Mapped[str]             = mapped_column(String(2), nullable=False, comment="AM / PM")
    is_active:        Mapped[bool]            = mapped_column(Boolean, default=True)
    created_at:       Mapped[datetime]        = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at:       Mapped[datetime]        = mapped_column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class StudentMarks(Base):
    __tablename__ = "student_marks"

    id:         Mapped[int]          = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int]          = mapped_column(BigInteger, ForeignKey("student.student_id", name="fk_mark_stu_id"), nullable=False)
    class_id:   Mapped[int]          = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id", name="fk_mark_class"), nullable=False)
    subject_id: Mapped[int]          = mapped_column(BigInteger, ForeignKey("school_stream_subject.subject_id", name="fk_mark_sub_id"), nullable=False)
    mark:       Mapped[float | None] = mapped_column(DECIMAL(18, 2))
    created_at: Mapped[datetime]     = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime]     = mapped_column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)


class OnlineExam(Base):
    __tablename__ = "on_exam"

    id:         Mapped[int]          = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title:      Mapped[str | None]   = mapped_column(String(250))
    class_id:   Mapped[int]          = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id", name="fk_on_exam_class"), nullable=False)
    subject_id: Mapped[int]          = mapped_column(BigInteger, ForeignKey("school_stream_subject.subject_id", name="fk_on_exam_sub"), nullable=False)
    exam_code:  Mapped[str | None]   = mapped_column(String(50))
    url:        Mapped[str | None]   = mapped_column(String(100))
    duration:   Mapped[str | None]   = mapped_column(String(10))
    start_date: Mapped[date]         = mapped_column(Date, nullable=False)
    end_date:   Mapped[date]         = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime]     = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime]     = mapped_column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)


class OnlineClass(Base):
    __tablename__ = "on_class"

    id:         Mapped[int]        = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title:      Mapped[str | None] = mapped_column(String(250))
    class_id:   Mapped[int]        = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id", name="fk_on_cls_class"), nullable=False)
    subject_id: Mapped[int]        = mapped_column(BigInteger, ForeignKey("school_stream_subject.subject_id", name="fk_on_cls_sub"), nullable=False)
    url:        Mapped[str | None] = mapped_column(String(100))
    duration:   Mapped[str | None] = mapped_column(String(10))
    start_date: Mapped[date]       = mapped_column(Date, nullable=False)
    end_date:   Mapped[date]       = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime]   = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime]   = mapped_column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)
