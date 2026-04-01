# models/school_stream_models.py
from sqlalchemy import String, Integer, Text, Enum, ForeignKey, BigInteger, Date, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base
from datetime import datetime, date
from typing import Optional
import enum


class School(Base):
    __tablename__ = "school"

    school_id:     Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_name:   Mapped[str]           = mapped_column(String(200), nullable=False)
    code:          Mapped[Optional[str]] = mapped_column(String(50),  unique=True, nullable=True)
    email:         Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    phone:         Mapped[Optional[str]] = mapped_column(String(30),  nullable=True)
    website:       Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line1: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    city:          Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state:         Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country:       Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code:   Mapped[Optional[str]] = mapped_column(String(20),  nullable=True)
    status:        Mapped[Optional[str]] = mapped_column(Enum("active", "inactive"), default="active", nullable=True)
    created_at:    Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:    Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    groups: Mapped[list["SchoolGroup"]] = relationship(
        "SchoolGroup", back_populates="school", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<School school_id={self.school_id} school_name={self.school_name!r}>"


class SchoolGroupStatus(str, enum.Enum):
    active   = "active"
    inactive = "inactive"
    expired  = "expired"


class SchoolGroup(Base):
    __tablename__ = "school_group"

    school_group_id: Mapped[int]               = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id:       Mapped[int]               = mapped_column(Integer, ForeignKey("school.school_id", ondelete="CASCADE"), nullable=False)
    group_name:      Mapped[str]               = mapped_column(String(255), nullable=False)
    description:     Mapped[Optional[str]]     = mapped_column(Text, nullable=True)
    start_date:      Mapped[Optional[date]]    = mapped_column(Date, nullable=True)
    end_date:        Mapped[Optional[date]]    = mapped_column(Date, nullable=True)
    validity_days:   Mapped[Optional[int]]     = mapped_column(Integer, nullable=True)
    status:          Mapped[SchoolGroupStatus] = mapped_column(
        Enum(SchoolGroupStatus), default=SchoolGroupStatus.active, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    school:   Mapped["School"]             = relationship("School", back_populates="groups")
    streams:  Mapped[list["SchoolStream"]] = relationship("SchoolStream",      back_populates="group")
    classes:  Mapped[list["SchoolStreamClass"]] = relationship("SchoolStreamClass", back_populates="group")

    def __repr__(self) -> str:
        return f"<SchoolGroup id={self.school_group_id} name={self.group_name!r} school_id={self.school_id}>"


class StatusEnum(str, enum.Enum):
    draft    = "draft"
    active   = "active"
    inactive = "inactive"
    archived = "archived"


# ─────────────────────────────────────────────
# SchoolStream
# ─────────────────────────────────────────────

class SchoolStream(Base):
    __tablename__ = "school_stream"

    __table_args__ = (
        Index("ix_school_stream_school_id",       "school_id"),
        Index("ix_school_stream_school_group_id", "school_group_id"),
    )

    school_stream_id: Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_id:        Mapped[int]            = mapped_column(BigInteger, ForeignKey("school.school_id", ondelete="CASCADE"), nullable=False)
    school_group_id:  Mapped[int]            = mapped_column(BigInteger, ForeignKey("school_group.school_group_id", ondelete="CASCADE"), nullable=False)
    stream_name:      Mapped[str]            = mapped_column(String(200), nullable=False)
    stream_code:      Mapped[Optional[str]]  = mapped_column(String(50),  nullable=True)
    description:      Mapped[Optional[str]]  = mapped_column(Text,        nullable=True)
    start_date:       Mapped[Optional[date]] = mapped_column(Date,        nullable=True)
    end_date:         Mapped[Optional[date]] = mapped_column(Date,        nullable=True)
    validity_days:    Mapped[Optional[int]]  = mapped_column(Integer,     nullable=True)
    max_students:     Mapped[Optional[int]]  = mapped_column(Integer,     nullable=True)
    status:           Mapped[StatusEnum]     = mapped_column(Enum(StatusEnum), default=StatusEnum.active, nullable=False)
    created_at:       Mapped[datetime]       = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:       Mapped[datetime]       = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    group:   Mapped["SchoolGroup"]             = relationship("SchoolGroup", back_populates="streams")
    classes: Mapped[list["SchoolStreamClass"]] = relationship(
        "SchoolStreamClass", back_populates="stream", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SchoolStream id={self.school_stream_id} name={self.stream_name!r}>"


# ─────────────────────────────────────────────
# SchoolStreamClass
# ─────────────────────────────────────────────

class SchoolStreamClass(Base):
    __tablename__ = "school_stream_class"

    __table_args__ = (
        Index("ix_school_stream_class_school_id",       "school_id"),
        Index("ix_school_stream_class_school_group_id", "school_group_id"),
        Index("ix_school_stream_class_stream_id",       "school_stream_id"),
    )

    class_id:         Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_id:        Mapped[int]           = mapped_column(BigInteger, ForeignKey("school.school_id",               ondelete="CASCADE"), nullable=False)
    school_group_id:  Mapped[int]           = mapped_column(BigInteger, ForeignKey("school_group.school_group_id",   ondelete="CASCADE"), nullable=False)
    school_stream_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("school_stream.school_stream_id", ondelete="SET NULL"), nullable=True)
    class_name:       Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    class_code:       Mapped[str]           = mapped_column(String(50),  nullable=True)
    description:      Mapped[Optional[str]] = mapped_column(Text,        nullable=True)
    start_date:       Mapped[Optional[date]]= mapped_column(Date,        nullable=True)
    end_date:         Mapped[Optional[date]]= mapped_column(Date,        nullable=True)
    validity_days:    Mapped[Optional[int]] = mapped_column(Integer,     nullable=True)
    schedule_info:    Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status:           Mapped[StatusEnum]    = mapped_column(Enum(StatusEnum), default=StatusEnum.active, nullable=False)
    created_at:       Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:       Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    group:    Mapped["SchoolGroup"]                    = relationship("SchoolGroup",  back_populates="classes")
    stream:   Mapped[Optional["SchoolStream"]]         = relationship("SchoolStream", back_populates="classes")
    sections: Mapped[list["SchoolStreamClassSection"]] = relationship("SchoolStreamClassSection", back_populates="class_", cascade="all, delete-orphan")
    subjects: Mapped[list["SchoolStreamSubject"]]      = relationship("SchoolStreamSubject",      back_populates="class_", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SchoolStreamClass id={self.class_id} name={self.class_name!r}>"


# ─────────────────────────────────────────────
# SchoolStreamClassSection
# ─────────────────────────────────────────────

class SchoolStreamClassSection(Base):
    __tablename__ = "school_stream_class_section"

    __table_args__ = (
        Index("ix_ssc_section_school_id", "school_id"),
        Index("ix_ssc_section_class_id",  "class_id"),
    )

    section_id:       Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_id:        Mapped[int]           = mapped_column(BigInteger, ForeignKey("school.school_id",               ondelete="CASCADE"), nullable=False)
    class_id:         Mapped[int]           = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id",   ondelete="CASCADE"), nullable=False)
    school_stream_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("school_stream.school_stream_id", ondelete="SET NULL"), nullable=True)
    section_code:     Mapped[str]           = mapped_column(String(10),  nullable=False)
    section_name:     Mapped[str]           = mapped_column(String(200), nullable=False)
    description:      Mapped[Optional[str]] = mapped_column(Text,        nullable=True)
    start_date:       Mapped[Optional[date]]= mapped_column(Date,        nullable=True)
    end_date:         Mapped[Optional[date]]= mapped_column(Date,        nullable=True)
    validity_days:    Mapped[Optional[int]] = mapped_column(Integer,     nullable=True)
    schedule_info:    Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status:           Mapped[StatusEnum]    = mapped_column(Enum(StatusEnum), default=StatusEnum.active, nullable=False)
    created_at:       Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:       Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    class_: Mapped["SchoolStreamClass"] = relationship("SchoolStreamClass", back_populates="sections")

    def __repr__(self) -> str:
        return f"<SchoolStreamClassSection id={self.section_id} name={self.section_name!r}>"


# ─────────────────────────────────────────────
# SchoolStreamSubject
# ─────────────────────────────────────────────

class SchoolStreamSubject(Base):
    __tablename__ = "school_stream_subject"

    __table_args__ = (
        Index("ix_school_stream_subject_school_id", "school_id"),
        Index("ix_school_stream_subject_class_id",  "class_id"),
    )

    subject_id:   Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_id:    Mapped[int]           = mapped_column(BigInteger, ForeignKey("school.school_id",             ondelete="CASCADE"), nullable=False)
    class_id:     Mapped[int]           = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id", ondelete="CASCADE"), nullable=False)
    subject_name: Mapped[str]           = mapped_column(String(200), nullable=False)
    description:  Mapped[Optional[str]] = mapped_column(Text,        nullable=True)
    status:       Mapped[StatusEnum]    = mapped_column(Enum(StatusEnum), default=StatusEnum.active, nullable=False)
    created_at:   Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:   Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    class_: Mapped["SchoolStreamClass"] = relationship("SchoolStreamClass", back_populates="subjects")

    def __repr__(self) -> str:
        return f"<SchoolStreamSubject id={self.subject_id} name={self.subject_name!r}>"
