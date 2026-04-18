# models/student_models.py
from sqlalchemy import String, Integer, Text, Enum, ForeignKey, BigInteger, Date, DateTime, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base
from datetime import datetime, date
from typing import Optional
import enum


class GenderEnum(str, enum.Enum):
    male   = "male"
    female = "female"
    other  = "other"


class StudentStatusEnum(str, enum.Enum):
    active   = "active"
    inactive = "inactive"


# ─────────────────────────────────────────────
# StudentAdmissionInquiry
# ─────────────────────────────────────────────

class StudentAdmissionInquiry(Base):
    __tablename__ = "student_admission_inquiry"

    student_inq_id:      Mapped[int]                  = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_name:        Mapped[str]                  = mapped_column(String(100), nullable=False)
    gender:              Mapped[Optional[GenderEnum]] = mapped_column(Enum(GenderEnum), nullable=True)
    age:                 Mapped[Optional[int]]        = mapped_column(Integer, nullable=True)
    class_id:            Mapped[Optional[int]]        = mapped_column(Integer, nullable=True)
    guardian_name:       Mapped[Optional[str]]        = mapped_column(String(150), nullable=True)
    guardian_phone:      Mapped[Optional[str]]        = mapped_column(String(30), nullable=True)
    guardian_occupation: Mapped[Optional[str]]        = mapped_column(String(150), nullable=True)
    guardian_gender:     Mapped[Optional[GenderEnum]] = mapped_column(Enum(GenderEnum), nullable=True)
    created_at:          Mapped[datetime]             = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:          Mapped[datetime]             = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<StudentAdmissionInquiry id={self.student_inq_id} name={self.student_name!r}>"


# ─────────────────────────────────────────────
# Student
# ─────────────────────────────────────────────

class Student(Base):
    __tablename__ = "student"

    student_id:          Mapped[int]                   = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_id:           Mapped[int]                   = mapped_column(BigInteger, ForeignKey("school.school_id", ondelete="CASCADE"), nullable=False)
    student_roll_id:     Mapped[Optional[str]]         = mapped_column(String(50), nullable=True)
    student_inq_id:      Mapped[Optional[int]]         = mapped_column(BigInteger, ForeignKey("student_admission_inquiry.student_inq_id", ondelete="SET NULL"), nullable=True)
    first_name:          Mapped[str]                   = mapped_column(String(100), nullable=False)
    last_name:           Mapped[Optional[str]]         = mapped_column(String(100), nullable=True)
    gender:              Mapped[Optional[GenderEnum]]  = mapped_column(Enum(GenderEnum), nullable=True)
    dob:                 Mapped[Optional[date]]        = mapped_column(Date, nullable=True)
    age:                 Mapped[Optional[int]]         = mapped_column(Integer, nullable=True)
    email:               Mapped[Optional[str]]         = mapped_column(String(150), nullable=True)
    phone:               Mapped[Optional[str]]         = mapped_column(String(30), nullable=True)
    address_line1:       Mapped[Optional[str]]         = mapped_column(String(200), nullable=True)
    address_line2:       Mapped[Optional[str]]         = mapped_column(String(200), nullable=True)
    city:                Mapped[Optional[str]]         = mapped_column(String(100), nullable=True)
    state:               Mapped[Optional[str]]         = mapped_column(String(100), nullable=True)
    country:             Mapped[Optional[str]]         = mapped_column(String(100), nullable=True)
    postal_code:         Mapped[Optional[str]]         = mapped_column(String(20), nullable=True)
    blood_group:         Mapped[Optional[str]]         = mapped_column(String(10), nullable=True)
    emergency_contact:   Mapped[Optional[str]]         = mapped_column(String(30), nullable=True)
    guardian_first_name: Mapped[Optional[str]]         = mapped_column(String(150), nullable=True)
    guardian_last_name:  Mapped[Optional[str]]         = mapped_column(String(150), nullable=True)
    guardian_phone:      Mapped[str]                   = mapped_column(String(30), nullable=False)
    guardian_email:      Mapped[Optional[str]]         = mapped_column(String(150), nullable=True)
    guardian_gender:     Mapped[Optional[GenderEnum]]  = mapped_column(Enum(GenderEnum), nullable=True)
    status:              Mapped[StudentStatusEnum]     = mapped_column(Enum(StudentStatusEnum), default=StudentStatusEnum.active, nullable=True)
    created_at:          Mapped[datetime]              = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:          Mapped[datetime]              = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    mappings: Mapped[list["StudentClassMapping"]] = relationship(
        "StudentClassMapping", back_populates="student", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Student id={self.student_id} name={self.first_name!r}>"


# ─────────────────────────────────────────────
# StudentClassMapping
# ─────────────────────────────────────────────

class StudentClassMapping(Base):
    __tablename__ = "school_class_student_mapping"

    id:              Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id:      Mapped[int]            = mapped_column(BigInteger, ForeignKey("student.student_id", ondelete="CASCADE"), nullable=False)
    class_id:        Mapped[int]            = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id", ondelete="CASCADE"), nullable=False)
    section_id:      Mapped[Optional[int]]  = mapped_column(BigInteger, ForeignKey("school_stream_class_section.section_id", ondelete="SET NULL"), nullable=True)
    stream_id:       Mapped[Optional[int]]  = mapped_column(BigInteger, ForeignKey("school_stream.school_stream_id", ondelete="SET NULL"), nullable=True)
    enroll_date:     Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_from_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_to_date:   Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status:          Mapped[Optional[str]]  = mapped_column(String(20), default="active", nullable=True)
    is_active:       Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)
    created_at:      Mapped[datetime]       = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:      Mapped[datetime]       = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    student: Mapped["Student"] = relationship("Student", back_populates="mappings")

    def __repr__(self) -> str:
        return f"<StudentClassMapping id={self.id} student_id={self.student_id} class_id={self.class_id}>"


# ─────────────────────────────────────────────
# ClassPromotionMap
# ─────────────────────────────────────────────

class ClassPromotionMap(Base):
    __tablename__ = "class_promotion_map"

    id:           Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    from_class_id: Mapped[int]          = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id", ondelete="CASCADE"), nullable=False)
    to_class_id:  Mapped[int]           = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id", ondelete="CASCADE"), nullable=False)
    created_at:   Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:   Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ClassPromotionMap id={self.id} from={self.from_class_id} to={self.to_class_id}>"