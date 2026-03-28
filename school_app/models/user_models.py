# models/user_models.py
from sqlalchemy import String, Integer, BigInteger, Boolean, Date, Enum, ForeignKey, Text, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base
from datetime import date, datetime
from typing import Optional


class DeviceRegistration(Base):
    __tablename__ = "device_registration"

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id:     Mapped[str]           = mapped_column(String(128), unique=True, nullable=False)
    os:            Mapped[str]           = mapped_column(String(20),  nullable=False)
    os_version:    Mapped[Optional[str]] = mapped_column(String(20),  nullable=True)
    make:          Mapped[Optional[str]] = mapped_column(String(50),  nullable=True)
    model:         Mapped[Optional[str]] = mapped_column(String(50),  nullable=True)
    app_version:   Mapped[Optional[str]] = mapped_column(String(20),  nullable=True)
    fcm_token:     Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active:     Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    registered_at: Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:    Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="device",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DeviceRegistration id={self.id} device_id={self.device_id!r} os={self.os!r}>"


class Session(Base):
    __tablename__ = "session"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id:   Mapped[Optional[int]]  = mapped_column(
        Integer,
        ForeignKey("device_registration.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id:     Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    role:        Mapped[Optional[str]] = mapped_column(String(20),  nullable=True)
    client_key:  Mapped[str]           = mapped_column(String(255), unique=True, nullable=False)
    valid_till:  Mapped[datetime]      = mapped_column(nullable=False)
    created_on:  Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    modified_on: Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    device: Mapped["DeviceRegistration"] = relationship(
        "DeviceRegistration",
        back_populates="sessions",
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} client_key={self.client_key!r} user_id={self.user_id}>"


class RoleCreation(Base):
    __tablename__ = "role_creation"

    role_id:    Mapped[int]           = mapped_column(Integer, primary_key=True)
    role_name:  Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active:  Mapped[Optional[bool]]= mapped_column(Boolean, default=True, nullable=True)
    created_at: Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<RoleCreation role_id={self.role_id} role_name={self.role_name!r}>"


class Employee(Base):
    __tablename__ = "employee"

    id:         Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    emp_id:     Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    role_id:    Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("role_creation.role_id"), nullable=True)
    first_name: Mapped[str]           = mapped_column(String(100), nullable=False)
    last_name:  Mapped[str]           = mapped_column(String(100), nullable=False)
    mobile:     Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email:      Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    password:   Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active:  Mapped[Optional[bool]]= mapped_column(Boolean, default=True, nullable=True)
    created_at: Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    role: Mapped[Optional["RoleCreation"]] = relationship("RoleCreation", lazy="joined")

    def __repr__(self) -> str:
        return f"<Employee id={self.id} mobile={self.mobile!r}>"


class Student(Base):
    __tablename__ = "student"

    student_id:       Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_id:        Mapped[int]           = mapped_column(BigInteger, nullable=False)
    student_roll_id:  Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    first_name:       Mapped[str]           = mapped_column(String(100), nullable=False)
    last_name:        Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone:            Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    status:           Mapped[Optional[str]] = mapped_column(Enum("active", "inactive"), default="active", nullable=True)
    created_at:  Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:  Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Student student_id={self.student_id} phone={self.phone!r}>"


class OtpVerification(Base):
    __tablename__ = "otp_verification"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    identifier: Mapped[str]      = mapped_column(String(50), nullable=False, index=True)
    otp:        Mapped[str]      = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    is_used:    Mapped[bool]     = mapped_column(Boolean, default=False, nullable=False)
    attempts:   Mapped[int]      = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), nullable=False)

    def __repr__(self) -> str:
        return f"<OtpVerification id={self.id} identifier={self.identifier!r} is_used={self.is_used}>"
