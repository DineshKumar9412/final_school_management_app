# models/chapter_models.py
from sqlalchemy import BigInteger, String, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import datetime
from typing import Optional


class Chapter(Base):
    __tablename__ = "chapter"

    id:          Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subject_id:  Mapped[int]           = mapped_column(BigInteger, ForeignKey("school_stream_subject.subject_id", ondelete="CASCADE"), nullable=False)
    class_id:    Mapped[int]           = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id",     ondelete="CASCADE"), nullable=False)
    title:       Mapped[str]           = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order:       Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at:  Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:  Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
