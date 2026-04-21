# models/notification_models.py
from sqlalchemy import String, Integer, ForeignKey, BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import datetime
from typing import Optional


class Notification(Base):
    __tablename__ = "notification"

    id:         Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title:      Mapped[str]           = mapped_column(String(100), nullable=False)
    message:    Mapped[Optional[str]] = mapped_column(String(10000), nullable=True)
    role_id:    Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("role_creation.role_id", ondelete="SET NULL"), nullable=True)
    image:      Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # stores image URL
    created_at: Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} title={self.title!r}>"
