# models/otp.py
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from database.base import Base


class OtpVerification(Base):
    __tablename__ = "otp_verification"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(128), nullable=False, index=True)
    otp        = Column(String(10), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used    = Column(Boolean, default=False, nullable=False)
    attempts   = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
