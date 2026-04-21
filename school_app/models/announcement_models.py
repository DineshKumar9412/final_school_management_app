# models/announcement_models.py
from sqlalchemy import String, BigInteger, ForeignKey, func, LargeBinary, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base
from datetime import datetime
from typing import Optional


class Announcement(Base):
    __tablename__ = "announcement"

    id:               Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_id:         Mapped[Optional[int]]  = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id",           ondelete="SET NULL"), nullable=True)
    section_id:       Mapped[Optional[int]]  = mapped_column(BigInteger, ForeignKey("school_stream_class_section.section_id", ondelete="SET NULL"), nullable=True)
    school_stream_id: Mapped[Optional[int]]  = mapped_column(BigInteger, ForeignKey("school_stream.school_stream_id",          ondelete="SET NULL", name="fk_announce_stream"), nullable=True)
    school_group_id:  Mapped[Optional[int]]  = mapped_column(BigInteger, ForeignKey("school_group.school_group_id",            ondelete="SET NULL", name="fk_announce_group"),  nullable=True)
    title:            Mapped[Optional[str]]  = mapped_column(String(100),  nullable=True)
    description:      Mapped[Optional[str]]  = mapped_column(String(1000), nullable=True)
    file:             Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    url:              Mapped[Optional[str]]  = mapped_column(String(1000), nullable=True)
    category:         Mapped[Optional[str]]  = mapped_column(Enum("EXAMS", "EVENTS", "CAMPUS", "GENERAL"), nullable=True)
    created_at:  Mapped[datetime]       = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:  Mapped[datetime]       = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Announcement id={self.id} title={self.title!r}>"
