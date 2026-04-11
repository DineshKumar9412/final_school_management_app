# models/custom_alarm_models.py
from sqlalchemy import BigInteger, Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import date, datetime
from typing import Optional


class CustomAlarm(Base):
    __tablename__ = "custom_alarm"

    id:         Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    section_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    class_id:   Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    message:    Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    alarm_date: Mapped[date]          = mapped_column(Date, nullable=False)
    slot_time:  Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CustomAlarm id={self.id} alarm_date={self.alarm_date}>"
