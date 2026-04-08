# models/employee_models.py
from sqlalchemy import String, Integer, BigInteger, Boolean, Date, Enum, ForeignKey, Text, func, Numeric, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base
from datetime import date, datetime
from typing import Optional
import enum


class GenderEnum(str, enum.Enum):
    male   = "male"
    female = "female"
    other  = "other"


class EmployeeStatusEnum(str, enum.Enum):
    teaching     = "teaching"
    non_teaching = "non teaching"


# ─────────────────────────────────────────────
# Role
# ─────────────────────────────────────────────

class Role(Base):
    __tablename__ = "role_creation"

    role_id:    Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_name:  Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)
    is_active:  Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)
    created_at: Mapped[datetime]       = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime]       = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Role id={self.role_id} name={self.role_name!r}>"


# ─────────────────────────────────────────────
# Employee
# ─────────────────────────────────────────────

class Employee(Base):
    __tablename__ = "employee"

    id:            Mapped[int]                          = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    emp_id:        Mapped[Optional[int]]                = mapped_column(Integer, nullable=True)
    role_id:       Mapped[Optional[int]]                = mapped_column(Integer, ForeignKey("role_creation.role_id", ondelete="SET NULL"), nullable=True)
    first_name:    Mapped[str]                          = mapped_column(String(100), nullable=False)
    last_name:     Mapped[str]                          = mapped_column(String(100), nullable=False)
    DOB:           Mapped[Optional[date]]               = mapped_column(Date, nullable=True)
    gender:        Mapped[Optional[GenderEnum]]         = mapped_column(Enum(GenderEnum), nullable=True)
    qualification: Mapped[Optional[str]]                = mapped_column(String(50), nullable=True)
    mobile:        Mapped[Optional[str]]                = mapped_column(String(30), nullable=True)
    address:       Mapped[Optional[str]]                = mapped_column(String(100), nullable=True)
    email:         Mapped[Optional[str]]                = mapped_column(String(100), nullable=True)
    password:      Mapped[Optional[str]]                = mapped_column(String(255), nullable=True)
    salary:        Mapped[Optional[float]]              = mapped_column(Numeric(18, 3), nullable=True)
    session_yr:    Mapped[Optional[str]]                = mapped_column(String(20), nullable=True)
    joining_dt:    Mapped[Optional[date]]               = mapped_column(Date, nullable=True)
    status:        Mapped[Optional[EmployeeStatusEnum]] = mapped_column(Enum(EmployeeStatusEnum), nullable=True)
    is_active:     Mapped[Optional[bool]]               = mapped_column(Boolean, default=True, nullable=True)
    created_at:    Mapped[datetime]                     = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:    Mapped[datetime]                     = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    role:     Mapped[Optional["Role"]]          = relationship("Role")
    mappings: Mapped[list["EmployeeClassMapping"]] = relationship("EmployeeClassMapping", back_populates="employee", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Employee id={self.id} emp_id={self.emp_id} name={self.first_name!r}>"


# ─────────────────────────────────────────────
# EmployeeClassMapping
# ─────────────────────────────────────────────

class EmployeeClassMapping(Base):
    __tablename__ = "school_class_emp_mapping"

    map_id:          Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    emp_id:          Mapped[int]            = mapped_column(BigInteger, ForeignKey("employee.id", ondelete="CASCADE"), nullable=False)
    class_id:        Mapped[int]            = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id", ondelete="CASCADE"), nullable=False)
    section_id:      Mapped[Optional[int]]  = mapped_column(BigInteger, ForeignKey("school_stream_class_section.section_id", ondelete="SET NULL"), nullable=True)
    school_group_id: Mapped[Optional[int]]  = mapped_column(Integer, ForeignKey("school_group.school_group_id", ondelete="SET NULL"), nullable=True)
    subject_id:      Mapped[int]            = mapped_column(BigInteger, ForeignKey("school_stream_subject.subject_id", ondelete="CASCADE"), nullable=False)
    is_class_teacher: Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    created_at:      Mapped[datetime]       = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:      Mapped[datetime]       = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    employee: Mapped["Employee"] = relationship("Employee", back_populates="mappings")

    def __repr__(self) -> str:
        return f"<EmployeeClassMapping map_id={self.map_id} emp_id={self.emp_id}>"
