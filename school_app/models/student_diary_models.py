# models/student_diary_models.py
from sqlalchemy import String, BigInteger, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import datetime, date
from typing import Optional


class StudentDiary(Base):
    __tablename__ = "student_diary"

    id:         Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int]           = mapped_column(BigInteger, ForeignKey("student.student_id", ondelete="CASCADE"), nullable=False)
    class_id:   Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id", ondelete="SET NULL"), nullable=True)
    section_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("school_stream_class_section.section_id", ondelete="SET NULL"), nullable=True)
    subject_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("school_stream_subject.subject_id", ondelete="SET NULL"), nullable=True)
    task_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dairy_date: Mapped[Optional[date]]= mapped_column(Date, nullable=True)
    status:     Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<StudentDiary id={self.id} student_id={self.student_id} date={self.dairy_date}>"
