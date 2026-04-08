# models/holiday_models.py
from sqlalchemy import String, BigInteger, Date, func
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import datetime, date
from typing import Optional


class Holiday(Base):
    __tablename__ = "holiday"

    id:           Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    holiday_date: Mapped[date]          = mapped_column(Date, nullable=False)
    title:        Mapped[str]           = mapped_column(String(100), nullable=False)
    description:  Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at:   Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:   Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Holiday id={self.id} title={self.title!r} date={self.holiday_date}>"
