# models/device.py
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
