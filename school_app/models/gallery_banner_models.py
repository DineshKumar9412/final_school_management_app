# models/gallery_banner_models.py
from sqlalchemy import BigInteger, String, DateTime, SmallInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import datetime


class SchoolGallery(Base):
    __tablename__ = "school_gallery"

    id:         Mapped[int]      = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_id:  Mapped[int]      = mapped_column(BigInteger, nullable=True)
    bannerlink: Mapped[str]      = mapped_column(String(500), nullable=False)
    status:     Mapped[int]      = mapped_column(SmallInteger, nullable=False, default=1)  # 1=active, 0=inactive
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )


class SchoolBanner(Base):
    __tablename__ = "school_banner"

    id:         Mapped[int]      = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_id:  Mapped[int]      = mapped_column(BigInteger, nullable=True)
    bannerlink: Mapped[str]      = mapped_column(String(500), nullable=False)
    status:     Mapped[int]      = mapped_column(SmallInteger, nullable=False, default=1)  # 1=active, 0=inactive
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )
