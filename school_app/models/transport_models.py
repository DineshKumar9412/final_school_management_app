# models/transport_models.py
from sqlalchemy import String, Integer, BigInteger, Numeric, Date, DateTime, Time, ForeignKey, func, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import datetime, date, time
from typing import Optional
from decimal import Decimal


# ─────────────────────────────────────────────
# VehicleDetails
# ─────────────────────────────────────────────

class VehicleDetails(Base):
    __tablename__ = "vehicle_details"

    id:                Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    vehicle_no:        Mapped[Optional[str]] = mapped_column(String(15),  nullable=True)
    vehicle_capacity:  Mapped[Optional[int]] = mapped_column(Integer,     nullable=True)
    vehicle_reg_no:    Mapped[Optional[str]] = mapped_column(String(15),  nullable=True)
    status:            Mapped[Optional[str]] = mapped_column(String(1),   nullable=True)
    driver_mob_no:     Mapped[str]           = mapped_column(String(15),  nullable=False)
    helper_mob_no:     Mapped[str]           = mapped_column(String(15),  nullable=False)
    created_at:        Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:        Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<VehicleDetails id={self.id} vehicle_no={self.vehicle_no!r}>"


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

class Routes(Base):
    __tablename__ = "routes"

    id:               Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name:             Mapped[str]           = mapped_column(String(100), nullable=False)
    vehicle_no:       Mapped[Optional[str]] = mapped_column(String(15),  nullable=True)
    distance:         Mapped[Optional[int]] = mapped_column(Integer,     nullable=True)
    status:           Mapped[Optional[str]] = mapped_column(String(1),   nullable=True)
    pick_start_time:  Mapped[time]          = mapped_column(Time,        nullable=False)
    pick_end_time:    Mapped[time]          = mapped_column(Time,        nullable=False)
    drop_start_time:  Mapped[time]          = mapped_column(Time,        nullable=False)
    drop_end_time:    Mapped[time]          = mapped_column(Time,        nullable=False)
    created_at:       Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:       Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Routes id={self.id} name={self.name!r}>"


# ─────────────────────────────────────────────
# VehicleRoutesMap
# ─────────────────────────────────────────────

class VehicleRoutesMap(Base):
    __tablename__ = "vehicle_routes_map"

    id:            Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    route_id:      Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("routes.id", ondelete="SET NULL"), nullable=True)
    vehicle_id:    Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("vehicle_details.id", ondelete="SET NULL", name="fk_vrm_vehicle_id"), nullable=True)
    driver_name:   Mapped[str]           = mapped_column(String(50),  nullable=False)
    helper_name:   Mapped[str]           = mapped_column(String(50),  nullable=False)
    driver_mob_no: Mapped[Optional[str]] = mapped_column(String(15),  nullable=True)
    helper_mob_no: Mapped[Optional[str]] = mapped_column(String(15),  nullable=True)
    created_at:    Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:    Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<VehicleRoutesMap id={self.id} route_id={self.route_id} vehicle_id={self.vehicle_id}>"


# ─────────────────────────────────────────────
# TransportationStudent
# ─────────────────────────────────────────────

class TransportationStudent(Base):
    __tablename__ = "transportation_student"

    id:         Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("vehicle_details.id", ondelete="SET NULL", name="fk_trans_veh_id"), nullable=True)
    class_id:   Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("school_stream_class.class_id",         ondelete="SET NULL"), nullable=True)
    section_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("school_stream_class_section.section_id", ondelete="SET NULL"), nullable=True)
    student_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("student.student_id",                   ondelete="SET NULL"), nullable=True)
    group_id:   Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("school_group.school_group_id",         ondelete="SET NULL"), nullable=True)
    session_yr: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime]      = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TransportationStudent id={self.id} student_id={self.student_id}>"


# ─────────────────────────────────────────────
# VehicleExpenses
# ─────────────────────────────────────────────

class VehicleExpenses(Base):
    __tablename__ = "vehicle_expenses"

    id:          Mapped[int]              = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    vehicle_id:  Mapped[Optional[int]]    = mapped_column(BigInteger, ForeignKey("vehicle_details.id", ondelete="SET NULL"), nullable=True)
    session_yr:  Mapped[Optional[str]]    = mapped_column(String(10),     nullable=True)
    amount:      Mapped[Optional[Decimal]]= mapped_column(Numeric(18, 2), nullable=True)
    date:        Mapped[Optional[datetime]]= mapped_column(DateTime,      nullable=True)
    image:       Mapped[Optional[bytes]]  = mapped_column(LargeBinary,    nullable=True)
    description: Mapped[Optional[str]]   = mapped_column(String(100),    nullable=True)
    created_at:  Mapped[datetime]         = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:  Mapped[datetime]         = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<VehicleExpenses id={self.id} vehicle_id={self.vehicle_id} amount={self.amount}>"
