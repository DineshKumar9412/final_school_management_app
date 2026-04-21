# schemas/auth.py
from pydantic import BaseModel
from typing import Optional

class WebLoginRequest(BaseModel):
    mobile: str
    password: str

from typing import Optional
from pydantic import BaseModel


class AndroidLoginRequest(BaseModel):
    mobile: str
    device_id: str


class UserInfo(BaseModel):
    user_id: int
    role: str
    empl_id: Optional[int] = None
    stud_id: Optional[str] = None  # student_roll_id


class AndroidVerifyOtpRequest(BaseModel):
    otp: str
    mobile_no: str
    user_info: UserInfo


class AndroidResendOtpRequest(BaseModel):
    mobile_no: str


class RegisterDeviceRequest(BaseModel):
    device_id: str
    os: str
    os_version: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    app_version: Optional[str] = None
    fcm_token: Optional[str] = None


class RegisterDeviceResponse(BaseModel):
    device_id: str
    is_new: bool
