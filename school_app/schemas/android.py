# schemas/android.py
from typing import Optional
from pydantic import BaseModel


class AndroidLoginRequest(BaseModel):
    mobile: str
    device_id: str


class UserInfo(BaseModel):
    user_id: str
    role: str
    empl_id: Optional[int] = None
    stud_id: Optional[str] = None  # student_roll_id


class AndroidVerifyOtpRequest(BaseModel):
    otp: str
    mobile_no: str
    user_info: UserInfo


class AndroidResendOtpRequest(BaseModel):
    mobile_no: str
