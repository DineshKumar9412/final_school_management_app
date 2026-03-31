# models/employee.py
from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Enum, Integer, LargeBinary, Numeric, String
from sqlalchemy.sql import func
from database.base import Base


class Employee(Base):
    __tablename__ = "employee"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    emp_id      = Column(Integer, nullable=True)
    role_id     = Column(Integer, nullable=True)
    first_name  = Column(String(100), nullable=False)
    last_name   = Column(String(100), nullable=False)
    DOB         = Column(Date, nullable=True)
    gender      = Column(Enum("male", "female", "other"), nullable=True)
    qualification = Column(String(100), nullable=True)
    mobile      = Column(String(20), nullable=True)
    address     = Column(String(255), nullable=True)
    email       = Column(String(100), nullable=True)
    password    = Column(String(255), nullable=True)
    salary      = Column(Numeric(10, 2), nullable=True)
    session_yr  = Column(String(20), nullable=True)
    joining_dt  = Column(Date, nullable=True)
    emp_img     = Column(LargeBinary, nullable=True)
    status      = Column(Enum("teaching", "non teaching"), nullable=True)
    is_active   = Column(Boolean, default=True, nullable=True)
    created_at  = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
