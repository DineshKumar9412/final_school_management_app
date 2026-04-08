# models/emp_leave_request_models.py
from sqlalchemy import String, BigInteger, Date, Enum, ForeignKey, func, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import datetime, date
from typing import Optional
import enum


class LeaveTypeEnum(str, enum.Enum):
    full         = "Full"
    first_half   = "First Half"
    second_half  = "Second Half"


class LeaveStatusEnum(str, enum.Enum):
    approved  = "Approved"
    rejected  = "Rejected"
    pending   = "Pending"


class EmpLeaveRequest(Base):
    __tablename__ = "emp_leave_request"

    id:          Mapped[int]                      = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    emp_id:      Mapped[Optional[int]]            = mapped_column(BigInteger, ForeignKey("employee.id", ondelete="SET NULL"), nullable=True)
    reason:      Mapped[str]                      = mapped_column(String(1000), nullable=False)
    from_dt:     Mapped[date]                     = mapped_column(Date, nullable=False)
    to_date:     Mapped[date]                     = mapped_column(Date, nullable=False)
    type:        Mapped[Optional[LeaveTypeEnum]]  = mapped_column(Enum(LeaveTypeEnum), nullable=True)
    status:      Mapped[Optional[LeaveStatusEnum]]= mapped_column(Enum(LeaveStatusEnum), nullable=True, default=LeaveStatusEnum.pending)
    attachments: Mapped[Optional[bytes]]          = mapped_column(LargeBinary, nullable=True)
    created_at:  Mapped[datetime]                 = mapped_column(server_default=func.current_timestamp(), nullable=False)
    updated_at:  Mapped[datetime]                 = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<EmpLeaveRequest id={self.id} emp_id={self.emp_id} status={self.status}>"
