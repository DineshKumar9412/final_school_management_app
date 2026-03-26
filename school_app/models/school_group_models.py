# models/school_group_models.py
from sqlalchemy import String, Integer, Date, Text, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base
from datetime import datetime, date
from typing import Optional
import enum


class SchoolGroupStatus(str, enum.Enum):
    active   = "active"
    inactive = "inactive"
    expired  = "expired"


class SchoolGroup(Base):
    __tablename__ = "school_group"

    school_group_id: Mapped[int]                      = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id:       Mapped[int]                      = mapped_column(Integer, ForeignKey("school.school_id", ondelete="CASCADE"), nullable=False)
    group_name:      Mapped[str]                      = mapped_column(String(255), nullable=False)
    description:     Mapped[Optional[str]]            = mapped_column(Text, nullable=True)
    start_date:      Mapped[Optional[date]]           = mapped_column(Date, nullable=True)
    end_date:        Mapped[Optional[date]]           = mapped_column(Date, nullable=True)
    validity_days:   Mapped[Optional[int]]            = mapped_column(Integer, nullable=True)
    status:          Mapped[SchoolGroupStatus]        = mapped_column(
        Enum(SchoolGroupStatus), default=SchoolGroupStatus.active, nullable=False
    )
    created_at:      Mapped[datetime]                 = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:      Mapped[datetime]                 = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SchoolGroup id={self.school_group_id} name={self.group_name!r} school_id={self.school_id}>"
