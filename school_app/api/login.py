# api/login.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from database.session import get_db
from database.redis_cache import cache
from models.user_models import Employee, Student, Session
from schemas.user_schemas import WebLoginRequest, AndroidLoginRequest, OtpVerifyRequest
from helper.optmessage import _send_otp_logic, _verify_otp_logic
from security.dependencies import validate_session
from response.result import Result

login_router = APIRouter(tags=["LOGIN"])


# ─────────────────────────────────────────────
# Helper: force-logout other active sessions
# ─────────────────────────────────────────────

async def _force_logout_user(user_id: str, current_client_key: str, db: AsyncSession):
    """
    Clears any other active session tied to this user_id.
    Must be called inside an existing db.begin() block.
    """
    result = await db.execute(
        select(Session).where(
            Session.user_id    == user_id,
            Session.valid_till >  datetime.utcnow(),
            Session.client_key != current_client_key,
        )
    )
    for s in result.scalars().all():
        s.user_id   = None
        s.role      = None
        s.device_id = None
        await cache.delete(f"session:{s.client_key}")


# ─────────────────────────────────────────────
# POST /api/auth/login/web
# ─────────────────────────────────────────────

@login_router.post("/web", summary="Web admin login (mobile + password)")
async def web_login(
    payload: WebLoginRequest,
    session: dict = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    if payload.platform != "web":
        return Result(code=400, message="Invalid platform. Expected 'web'.", extra={}).http_response()

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

    # Role must be admin
    role = employee.role  # joined
    if not role or not role.role_name or role.role_name.lower() != "admin":
        return Result(code=401, message="Invalid credentials or insufficient permissions.", extra={}).http_response()

    user_id = str(employee.id)

    async with db.begin():
        await _force_logout_user(user_id, session["client_key"], db)

        sess_result = await db.execute(
            select(Session).where(Session.client_key == session["client_key"])
        )
        db_session = sess_result.scalar_one()
        db_session.user_id = user_id
        db_session.role    = "admin"

    await cache.delete(f"session:{session['client_key']}")

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
    payload: AndroidLoginRequest,
    session: dict = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    # FCM token comes directly from enriched session
    device_info = session.get("device_id")
    fcm_token   = device_info.get("fcm_token") if device_info else None

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

    # Validate employee role
    if employee:
        role      = employee.role  # joined
        role_name = role.role_name.lower() if role and role.role_name else None
        if role_name == "admin":
            return Result(code=401, message="Admin login is not allowed on mobile.", extra={}).http_response()
    else:
        role_name = None

    # Mobile found in both tables — ask user to choose
    if student and employee:
        return Result(
            code=202,
            message="Multiple accounts found. Please choose your role.",
            extra={"choices": ["student", role_name or "employee"]},
        ).http_response()

    if student:
        await _send_otp_logic(payload.mobile_number, db, fcm_token)
        return Result(code=200, message="OTP sent successfully.", extra={"role": "student"}).http_response()

    if employee:
        await _send_otp_logic(payload.mobile_number, db, fcm_token)
        return Result(code=200, message="OTP sent successfully.", extra={"role": role_name}).http_response()

    return Result(code=404, message="Mobile number not found.", extra={}).http_response()


# ─────────────────────────────────────────────
# POST /api/auth/login/otp/verify
# ─────────────────────────────────────────────

@login_router.post("/otp/verify", summary="Verify OTP and complete Android login")
async def verify_otp(
    payload: OtpVerifyRequest,
    session: dict = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
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

    async with db.begin():
        await _force_logout_user(user_id, session["client_key"], db)

        sess_result = await db.execute(
            select(Session).where(Session.client_key == session["client_key"])
        )
        db_session = sess_result.scalar_one()
        db_session.user_id = user_id
        db_session.role    = role

    await cache.delete(f"session:{session['client_key']}")

    return Result(
        code=200,
        message="OTP verified. Login successful.",
        extra={"user_id": user_id, "role": role},
    ).http_response()
