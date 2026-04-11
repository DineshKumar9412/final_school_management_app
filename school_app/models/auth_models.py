# models/device.py
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from database.base import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from database.base import Base


class DeviceRegistration(Base):
    __tablename__ = "device_registration"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(128), unique=True, nullable=False)
    os = Column(String(20), nullable=False)
    os_version = Column(String(20), nullable=True)
    make = Column(String(50), nullable=True)
    model = Column(String(50), nullable=True)
    app_version = Column(String(20), nullable=True)
    fcm_token = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    registered_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class OtpVerification(Base):
    __tablename__ = "otp_verification"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(128), nullable=False, index=True)
    otp        = Column(String(10), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used    = Column(Boolean, default=False, nullable=False)
    attempts   = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class FcmToken(Base):
    __tablename__ = "fcm_token"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, nullable=True)
    class_id   = Column(Integer, nullable=True)
    section_id = Column(Integer, nullable=True)
    fcm_token  = Column(String(255), unique=True, nullable=True)
    status     = Column(Integer, default=0, nullable=False)   # 0=unseen, 1=stopped


class Session(Base):
    __tablename__ = "session"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    device_id   = Column(Integer, nullable=True)
    user_id     = Column(String(128), nullable=True, index=True)
    role        = Column(String(20), nullable=True)
    client_key  = Column(String(255), unique=True, nullable=False)
    valid_till  = Column(DateTime, nullable=False)
    created_on  = Column(DateTime, server_default=func.now(), nullable=False)
    modified_on = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
