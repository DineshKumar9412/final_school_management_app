# schemas/user_schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ─────────────────────────────────────────────
# Device Registration
# ─────────────────────────────────────────────

class DeviceRegisterRequest(BaseModel):
    """
    Sent by web / Android client to register or re-register a device.
    Matches: device_registration table columns.
    """
    device_id:   str           = Field(..., max_length=128, description="Unique device identifier (IMEI / UUID / browser fingerprint)")
    os:          str           = Field(..., max_length=20,  description="Platform: web | android | ios")
    os_version:  Optional[str] = Field(None, max_length=20,  description="OS version e.g. '13'")
    make:        Optional[str] = Field(None, max_length=50,  description="Device manufacturer e.g. 'Samsung'")
    model:       Optional[str] = Field(None, max_length=50,  description="Device model e.g. 'Galaxy S23'")
    app_version: Optional[str] = Field(None, max_length=20,  description="App build version e.g. '2.1.0'")
    fcm_token:   Optional[str] = Field(None, max_length=255, description="FCM / APNs push token")

    model_config = {
        "json_schema_extra": {
            "example": {
                "device_id":   "ANDROID-IMEI-XYZ123",
                "os":          "android",
                "os_version":  "13",
                "make":        "Samsung",
                "model":       "Galaxy S23",
                "app_version": "2.1.0",
                "fcm_token":   "fcm-token-abc123"
            }
        }
    }


class DeviceRegisterResponse(BaseModel):
    """Returned after a successful device registration / session resume."""
    client_key: str  = Field(..., description="Opaque session token — store in cookie (web) or secure storage (Android)")
    is_new:     bool = Field(..., description="True → new session created  |  False → existing session resumed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "client_key": "550e8400-e29b-41d4-a716-446655440000",
                "is_new": True
            }
        }
    }


# ─────────────────────────────────────────────
# Session (read / internal)
# ─────────────────────────────────────────────

class SessionSchema(BaseModel):
    """
    Read-only representation of a session row.
    Used internally and for admin/debug responses.
    """
    id:          int
    device_id:   int
    user_id:     Optional[str]
    role:        Optional[str]
    client_key:  str
    valid_till:  datetime
    created_on:  datetime
    modified_on: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Auth Login (post device-register step)
# ─────────────────────────────────────────────

class AuthLoginRequest(BaseModel):
    """
    Sent after the user authenticates (OTP / password).
    Links the anonymous session to a real user_id.
    """
    client_key: str = Field(..., description="client_key received from /device/register")
    user_id:    str = Field(..., description="Authenticated user's ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "client_key": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "USER-101"
            }
        }
    }


class AuthLoginResponse(BaseModel):
    """Returned after successfully linking session to a user."""
    client_key: str
    user_id:    str
    device_id:  int
    valid_till: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Web Login
# ─────────────────────────────────────────────

class WebLoginRequest(BaseModel):
    mobile_number: str = Field(..., description="Employee mobile number")
    password:      str = Field(..., description="Employee password")


# ─────────────────────────────────────────────
# Android Login
# ─────────────────────────────────────────────

class AndroidLoginRequest(BaseModel):
    mobile_number: str = Field(..., description="User mobile number")


# ─────────────────────────────────────────────
# OTP Verify
# ─────────────────────────────────────────────

class OtpVerifyRequest(BaseModel):
    mobile_number: str            = Field(..., description="Mobile number used during login")
    otp:           str            = Field(..., description="6-digit OTP received via FCM")
    role_choice:   Optional[str]  = Field(None, description="'student' or role name — required only when 202 was returned")
