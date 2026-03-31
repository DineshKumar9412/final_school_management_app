# schemas/device.py
from typing import Optional
from pydantic import BaseModel


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
