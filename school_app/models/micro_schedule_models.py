# models/micro_schedule_models.py
from sqlalchemy import BigInteger, Date, String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import date, datetime
from typing import Optional


class MicroSchedule(Base):
    __tablename__ = "micro_schedule"

    id:          Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    emp_id:      Mapped[int]           = mapped_column(BigInteger, ForeignKey("employee.id", ondelete="CASCADE"), nullable=False)
    class_id:    Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    section_id:  Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    subject_id:  Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    title:       Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    schedule_dt: Mapped[date]          = mapped_column(Date, nullable=False)
    created_at:  Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:  Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<MicroSchedule id={self.id} emp_id={self.emp_id} date={self.schedule_dt}>"
