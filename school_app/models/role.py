# models/role.py
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from database.base import Base


class RoleCreation(Base):
    __tablename__ = "role_creation"

    role_id     = Column(Integer, primary_key=True)
    role_name   = Column(String(100), nullable=True)
    is_active   = Column(Boolean, default=True, nullable=True)
    created_at  = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
