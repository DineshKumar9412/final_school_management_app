# models/user_models.py
from sqlalchemy import String, Integer, BigInteger, Boolean, Date, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base
from datetime import date, datetime
from typing import Optional


class School(Base):
    __tablename__ = "school"

    school_id:    Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_name:  Mapped[str]           = mapped_column(String(200), nullable=False)
    code:         Mapped[Optional[str]] = mapped_column(String(50),  unique=True, nullable=True)
    email:        Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    phone:        Mapped[Optional[str]] = mapped_column(String(30),  nullable=True)
    website:      Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line1: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    city:         Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state:        Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country:      Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code:  Mapped[Optional[str]] = mapped_column(String(20),  nullable=True)
    status:       Mapped[Optional[str]] = mapped_column(Enum("active", "inactive"), default="active", nullable=True)
    created_at:   Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:   Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    groups: Mapped[list["SchoolGroup"]] = relationship(
        "SchoolGroup",
        back_populates="school",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<School school_id={self.school_id} school_name={self.school_name!r}>"


class SchoolGroup(Base):
    __tablename__ = "school_group"

    school_group_id: Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_id:       Mapped[int]           = mapped_column(
        BigInteger,
        ForeignKey("school.school_id", ondelete="CASCADE"),
        nullable=False,
    )
    group_name:    Mapped[str]           = mapped_column(String(200), nullable=False)
    description:   Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date:    Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date:      Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    validity_days: Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    status:        Mapped[Optional[str]]  = mapped_column(
        Enum("draft", "active", "inactive", "archived"), default="draft", nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    school: Mapped["School"] = relationship("School", back_populates="groups")

    def __repr__(self) -> str:
        return f"<SchoolGroup school_group_id={self.school_group_id} group_name={self.group_name!r}>"


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
    device_id:   Mapped[int]           = mapped_column(
        Integer,
        ForeignKey("device_registration.id", ondelete="CASCADE"),
        nullable=False,
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
