# models/assignment_models.py
from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Assignment(Base):
    """Teacher creates one assignment per class/section/subject."""
    __tablename__ = "assignment"

    id:          Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title:       Mapped[Optional[str]]  = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    class_id:    Mapped[Optional[int]]  = mapped_column(BigInteger, nullable=True)
    section_id:  Mapped[Optional[int]]  = mapped_column(BigInteger, nullable=True)
    subject_id:  Mapped[Optional[int]]  = mapped_column(BigInteger, nullable=True)
    group_name:  Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)
    emp_id:      Mapped[int]            = mapped_column(
                                            BigInteger,
                                            ForeignKey("employee.id", ondelete="CASCADE"),
                                            nullable=False,
                                        )
    due_date:    Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status:      Mapped[int]            = mapped_column(SmallInteger, default=1, nullable=False)
    created_at:  Mapped[datetime]       = mapped_column(
                                            DateTime,
                                            server_default=func.current_timestamp(),
                                            nullable=False,
                                        )
    updated_at:  Mapped[datetime]       = mapped_column(
                                            DateTime,
                                            server_default=func.current_timestamp(),
                                            onupdate=func.current_timestamp(),
                                            nullable=False,
                                        )


class AssignmentSubmission(Base):
    """Student submits an assignment (one row per student per assignment)."""
    __tablename__ = "assignment_submission"

    id:            Mapped[int]               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int]               = mapped_column(
                                                BigInteger,
                                                ForeignKey("assignment.id", ondelete="CASCADE"),
                                                nullable=False,
                                             )
    student_id:    Mapped[int]               = mapped_column(
                                                BigInteger,
                                                ForeignKey("student.student_id", ondelete="CASCADE"),
                                                nullable=False,
                                             )
    description:   Mapped[Optional[str]]     = mapped_column(Text, nullable=True)
    image_url:     Mapped[Optional[str]]     = mapped_column(String(500), nullable=True)
    status:        Mapped[str]               = mapped_column(
                                                Enum("assigned", "submitted"),
                                                default="assigned",
                                                nullable=False,
                                             )
    submitted_at:  Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at:    Mapped[datetime]           = mapped_column(
                                                DateTime,
                                                server_default=func.current_timestamp(),
                                                nullable=False,
                                               )
    updated_at:    Mapped[datetime]           = mapped_column(
                                                DateTime,
                                                server_default=func.current_timestamp(),
                                                onupdate=func.current_timestamp(),
                                                nullable=False,
                                               )
