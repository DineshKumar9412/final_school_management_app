# models/student.py
from sqlalchemy import BigInteger, Column, Enum, String
from database.base import Base


class Student(Base):
    __tablename__ = "student"

    student_id      = Column(BigInteger, primary_key=True, autoincrement=True)
    student_roll_id = Column(String(50), nullable=True)
    first_name      = Column(String(100), nullable=False)
    last_name       = Column(String(100), nullable=True)
    phone           = Column(String(30), nullable=True)
    status          = Column(Enum("active", "inactive"), default="active", nullable=True)
