# api/login.py
import uuid
from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
from typing import Annotated, Optional

SESSION_ADMIN_TTL_DAYS = 10

from database.session import get_db
from database.redis_cache import cache
from models.user_models import Employee, Student, Session, DeviceRegistration
from schemas.user_schemas import WebLoginRequest, AndroidLoginRequest, OtpVerifyRequest
from helper.optmessage import _send_otp_logic, _verify_otp_logic
from response.result import Result

login_router = APIRouter(tags=["LOGIN"])


# ─────────────────────────────────────────────
# Helper: force-logout other active sessions
# ─────────────────────────────────────────────

async def _force_logout_user(user_id: str, db: AsyncSession):
    result = await db.execute(
        select(Session).where(
            Session.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        return
    
    await db.execute(
            update(Session)
            .where(Session.id == session.id)
            .values(user_id=None, role=None)
        )
    await db.commit()
    await cache.delete(f"session:{session.client_key}")


# ─────────────────────────────────────────────
# POST /api/auth/login/web
# ─────────────────────────────────────────────

@login_router.post("/web", summary="Web admin login (mobile + password)")
async def web_login(
    request: Request,
    response: Response,
    payload: WebLoginRequest,
    db: AsyncSession = Depends(get_db),
    client_key: Annotated[Optional[str], Header(description="Client key from device registration (Android/TV). Web clients send it automatically via cookie.")] = None,
):
    client_key = client_key or request.cookies.get("client_key")

    if not client_key:
        return Result(code=401, message="client_key required.", extra={}).http_response()
    
    result = await db.execute(
        select(Session).where(Session.client_key == client_key)
    )
    session = result.scalar_one_or_none()

    if session is None:
        return Result(code=401, message="Invalid Client Key.", extra={}).http_response()

    # Renew expired session with a new client_key
    now = datetime.utcnow()

    if session.valid_till < now:
        new_client_key = str(uuid.uuid4())
        new_valid_till = now + timedelta(days=SESSION_ADMIN_TTL_DAYS)
        await db.execute(
            update(Session)
            .where(Session.client_key == client_key)
            .values(client_key=new_client_key, valid_till=new_valid_till)
        )
        await db.commit()
        await cache.delete(f"session:{client_key}")
        client_key = new_client_key
        response.set_cookie(
            key="client_key",
            value=client_key,
            httponly=True,
            samesite="lax",
            max_age=SESSION_ADMIN_TTL_DAYS * 86400,
        )

    # Find active employee by mobile
    emp_result = await db.execute(
        select(Employee).where(
            Employee.mobile    == payload.mobile_number,
            Employee.is_active == True,
        )
    )
    employee = emp_result.scalar_one_or_none()
  
    if employee is None or employee.password != payload.password:
        return Result(code=401, message="Invalid credentials or insufficient permissions.", extra={}).http_response()

    role = employee.role
    if not role or not role.role_name or role.role_name.lower() != "admin":
        return Result(code=401, message="Admin only Allowed.", extra={}).http_response()

    user_id = str(employee.id)

    await _force_logout_user(user_id, db)

    await db.execute(
        update(Session)
        .where(Session.client_key == client_key)
        .values(user_id=user_id, role="admin")
    )
    await db.commit()

    await cache.delete(f"session:{client_key}")

    return Result(
        code=200,
        message="Login successful.",
        extra={"user_id": user_id, "role": "admin"},
    ).http_response()


# ─────────────────────────────────────────────
# POST /api/auth/login/android
# ─────────────────────────────────────────────

@login_router.post("/android", summary="Android login — sends OTP via FCM")
async def android_login(
    request: Request,
    payload: AndroidLoginRequest,
    db: AsyncSession = Depends(get_db),
    client_key: Annotated[Optional[str], Header(description="Client key from device registration (Android/TV). Web clients send it automatically via cookie.")] = None,
):
    client_key = client_key or request.cookies.get("client_key")

    if not client_key:
        return Result(code=401, message="client_key required.", extra={}).http_response()

    # Check session exists and renew if expired
    sess_result = await db.execute(
        select(Session).where(Session.client_key == client_key)
    )
    session = sess_result.scalar_one_or_none()

    if session is None:
        return Result(code=401, message="Invalid Client Key.", extra={}).http_response()

    now = datetime.utcnow()
    renewed_client_key = None
    if session.valid_till < now:
        new_client_key    = str(uuid.uuid4())
        new_valid_till    = now + timedelta(days=SESSION_ADMIN_TTL_DAYS)
        await db.execute(
            update(Session)
            .where(Session.client_key == client_key)
            .values(client_key=new_client_key, valid_till=new_valid_till)
        )
        await db.commit()
        await cache.delete(f"session:{client_key}")
        client_key        = new_client_key
        renewed_client_key = new_client_key

    stmt = (
        select(DeviceRegistration.fcm_token)
        .join(Session, DeviceRegistration.id == Session.device_id)
        .where(Session.client_key == client_key)
    )

    result = await db.execute(stmt)
    fcm_token = result.scalar_one_or_none()

    if not fcm_token:
        return Result(code=400, message="FCM token missing. Cannot send OTP.", extra={}).http_response()

    # Check student table
    stu_result = await db.execute(
        select(Student).where(
            Student.phone  == payload.mobile_number,
            Student.status == "active",
        )
    )
    student = stu_result.scalar_one_or_none()

    # Check employee table
    emp_result = await db.execute(
        select(Employee).where(
            Employee.mobile    == payload.mobile_number,
            Employee.is_active == True,
        )
    )
    employee = emp_result.scalar_one_or_none()

    if employee:
        role      = employee.role
        role_name = role.role_name.lower() if role and role.role_name else None
        if role_name == "admin":
            employee = None

    if student and employee:
        choices = [
            {
            "role": "student",
            "id": student.student_id,
            "roll_id": student.student_roll_id,
            "fcm_token": fcm_token,
            "mobile": payload.mobile_number
            },
            {
            "role": role_name,
            "id": employee.id,
            "roll_id": employee.emp_id,
            "fcm_token": fcm_token,
            "mobile": payload.mobile_number
            }
            ]
        extra = {"choices": choices, **({"client_key": renewed_client_key} if renewed_client_key else {})}
        return Result(code=202, message="Multiple accounts found. Please choose your role.", extra=extra).http_response()

    if student:
        await _send_otp_logic(payload.mobile_number, db, fcm_token)
        extra = {"role": "student", **({"client_key": renewed_client_key} if renewed_client_key else {})}
        return Result(code=200, message="OTP sent successfully.", extra=extra).http_response()

    if employee:
        await _send_otp_logic(payload.mobile_number, db, fcm_token)
        extra = {"role": role_name, **({"client_key": renewed_client_key} if renewed_client_key else {})}
        return Result(code=200, message="OTP sent successfully.", extra=extra).http_response()

    return Result(code=404, message="Mobile number not found.", extra={}).http_response()


@login_router.post("/android/choice", summary="Multiple accounts found. Please choose your role")
async def android_choice(
    mobile: str,
    fcm_token: str,
    role_name: str,
    db: AsyncSession = Depends(get_db),
):
    if role_name == "student":
        await _send_otp_logic(mobile, db, fcm_token)
        return Result(code=200, message="OTP sent successfully.", extra={"role": "student"}).http_response()

    else:
        await _send_otp_logic(mobile, db, fcm_token)
        return Result(code=200, message="OTP sent successfully.", extra={"role": role_name}).http_response()


# ─────────────────────────────────────────────
# POST /api/auth/login/otp/verify
# ─────────────────────────────────────────────

@login_router.post("/otp/verify", summary="Verify OTP and complete Android login")
async def verify_otp(
    request: Request,
    payload: OtpVerifyRequest,
    db: AsyncSession = Depends(get_db),
    client_key: Annotated[Optional[str], Header(description="Client key from device registration (Android/TV). Web clients send it automatically via cookie.")] = None,
):
    client_key = client_key or request.cookies.get("client_key")

    if not client_key:
        return Result(code=401, message="client_key required.", extra={}).http_response()

    sess_result = await db.execute(
        select(Session).where(Session.client_key == client_key)
    )
    if sess_result.scalar_one_or_none() is None:
        return Result(code=401, message="Invalid session.", extra={}).http_response()

    success, code, message = await _verify_otp_logic(payload.mobile_number, payload.otp, db)
    if not success:
        return Result(code=code, message=message, extra={}).http_response()

    role_choice = (payload.role_choice or "").lower()

    if role_choice == "student":
        stu_result = await db.execute(
            select(Student).where(Student.phone == payload.mobile_number)
        )
        student = stu_result.scalar_one_or_none()
        if student is None:
            return Result(code=404, message="Student not found.", extra={}).http_response()
        user_id = str(student.student_id)
        role    = "student"
    else:
        emp_result = await db.execute(
            select(Employee).where(Employee.mobile == payload.mobile_number)
        )
        employee = emp_result.scalar_one_or_none()
        if employee is None:
            return Result(code=404, message="Employee not found.", extra={}).http_response()
        user_id  = str(employee.id)
        role_obj = employee.role
        role     = role_obj.role_name.lower() if role_obj and role_obj.role_name else "employee"

    await db.execute(
        update(Session)
        .where(Session.client_key == client_key)
        .values(user_id=user_id, role=role)
    )
    await db.commit()

    await cache.delete(f"session:{client_key}")

    return Result(
        code=200,
        message="OTP verified. Login successful.",
        extra={"user_id": user_id, "role": role},
    ).http_response()
