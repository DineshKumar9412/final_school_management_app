# models/user_models.py
from sqlalchemy import String, Integer, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base
from datetime import datetime
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
