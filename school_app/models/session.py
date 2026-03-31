# models/session.py
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func
from database.base import Base


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
