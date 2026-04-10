# api/android_login.py
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from helper.optmessage import _send_otp_logic, _verify_otp_logic
from models.auth_models import DeviceRegistration, FcmToken, Session
from models.employee_models import Employee, Role
from models.student_models import Student, StudentClassMapping
from response.result import Result
from schemas.auth_schemas import AndroidLoginRequest, AndroidResendOtpRequest, AndroidVerifyOtpRequest
from security.valid_session import valid_session

android_router = APIRouter(tags=["SCHOOL AUTH"])

SESSION_TTL_HOURS = 24 * 90         # 3 months


# ── Android Login ──────────────────────────────────────────────────────────────

@android_router.post("/android/login/")
async def android_login(
    payload: AndroidLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1. Look up device by device_id
    device_result = await db.execute(
        select(DeviceRegistration).where(
            DeviceRegistration.device_id == payload.device_id,
            DeviceRegistration.is_active == True,
        )
    )
    device = device_result.scalar_one_or_none()
    if not device:
        return Result(code=404, message="Device not registered").http_response()

    # 2. Look up employee and student by mobile number
    emp_result = await db.execute(
        select(Employee).where(
            Employee.mobile == payload.mobile,
            Employee.is_active == True,
        )
    )
    employee = emp_result.scalar_one_or_none()

    stu_result = await db.execute(
        select(Student).where(
            Student.phone == payload.mobile,
            Student.status == "active",
        )
    )
    student = stu_result.scalar_one_or_none()

    if not employee and not student:
        return Result(code=404, message="Mobile number not found").http_response()

    # 3. Build user_info list
    user_info = []

    if employee:
        role_name = None
        if employee.role_id is not None:
            role_result = await db.execute(
                select(Role).where(Role.role_id == employee.role_id)
            )
            role = role_result.scalar_one_or_none()
            role_name = role.role_name if role else None

        if role_name != "admin":
            user_info.append({
                "user_id": str(employee.id),
                "role": role_name or "employee",
                "empl_id": employee.emp_id,
            })

    if student:
        user_info.append({
            "user_id": str(student.student_id),
            "role": "student",
            "stud_id": student.student_roll_id,
        })

    # admin-only mobile → not allowed on android
    if not user_info:
        return Result(code=403, message="Admin accounts must use web login").http_response()

    # 4. Create session (user_id / role left null until OTP is verified)
    new_session = Session(
        device_id  = device.id,
        client_key = str(uuid4()),
        valid_till = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS),
    )
    db.add(new_session)
    await db.flush()   # get new_session.id

    # 5. Generate and send OTP via FCM (identifier = mobile number)
    otp = await _send_otp_logic(
        identifier = payload.mobile,
        db         = db,
        fcb_token  = device.fcm_token or "",
    )

    await db.commit()

    # 6. Return client_key immediately — used for resend-otp and verify-otp
    return Result(
        code    = 200,
        message = "OTP sent",
        extra   = {
            "otp"        : otp,
            "client_key" : new_session.client_key,
            "mobile_no"  : payload.mobile,
            "user_info"  : user_info,
        },
    ).http_response()

# ── Android Resend OTP ─────────────────────────────────────────────────────────

@android_router.post("/android/resend-otp/")
async def android_resend_otp(
    payload: AndroidResendOtpRequest,
    session: Session = Depends(valid_session),   # client_key → session
    db: AsyncSession = Depends(get_db),
):
    # 1. Look up device to get fcm_token
    device_result = await db.execute(
        select(DeviceRegistration).where(
            DeviceRegistration.id == session.device_id,
            DeviceRegistration.is_active == True,
        )
    )
    device = device_result.scalar_one_or_none()
    if not device:
        return Result(code=404, message="Device not found").http_response()

    # 2. Resend OTP — same session, new OTP, old OTP invalidated automatically
    otp = await _send_otp_logic(
        identifier = payload.mobile_no,
        db         = db,
        fcb_token  = device.fcm_token or "",
    )

    return Result(
        code    = 200,
        message = "OTP resent",
        extra   = {
            "otp"       : otp,
            "mobile_no" : payload.mobile_no,
        },
    ).http_response()


# ── Android Verify OTP ─────────────────────────────────────────────────────────

@android_router.post("/android/verify-otp/")
async def android_verify_otp(
    payload: AndroidVerifyOtpRequest,
    session: Session = Depends(valid_session),   # client_key → session
    db: AsyncSession = Depends(get_db),
):
    # 1. Verify OTP (identifier = mobile number, same as used during login)
    ok, code, message = await _verify_otp_logic(
        identifier = payload.mobile_no,
        otp        = payload.otp,
        db         = db,
    )
    if not ok:
        return Result(code=code, message=message).http_response()

    # 2. Null out any existing sessions mapped to this user_id (logout old sessions)
    old_sessions_result = await db.execute(
        select(Session).where(
            Session.user_id == payload.user_info.user_id,
            Session.id != session.id,           # exclude the current session
        )
    )
    old_sessions = old_sessions_result.scalars().all()
    for old in old_sessions:
        old.user_id = None
        old.role    = None

    # 3. Map user_id and role onto the current session
    session.user_id = payload.user_info.user_id
    session.role    = payload.user_info.role

    # 4. If student — upsert fcm_token table with class/section info
    if payload.user_info.role == "student":
        # Get student's class + section from mapping
        mapping_result = await db.execute(
            select(StudentClassMapping).where(
                StudentClassMapping.student_id == int(payload.user_info.user_id),
                StudentClassMapping.is_active == True,
            )
        )
        mapping = mapping_result.scalar_one_or_none()

        # Get fcm_token from device
        device_result = await db.execute(
            select(DeviceRegistration).where(DeviceRegistration.id == session.device_id)
        )
        device = device_result.scalar_one_or_none()

        if device and device.fcm_token:
            fcm_result = await db.execute(
                select(FcmToken).where(FcmToken.fcm_token == device.fcm_token)
            )
            fcm_rec = fcm_result.scalar_one_or_none()

            if fcm_rec:
                fcm_rec.user_id    = int(payload.user_info.user_id)
                fcm_rec.class_id   = mapping.class_id if mapping else None
                fcm_rec.section_id = mapping.section_id if mapping else None
            else:
                db.add(FcmToken(
                    user_id    = int(payload.user_info.user_id),
                    class_id   = mapping.class_id if mapping else None,
                    section_id = mapping.section_id if mapping else None,
                    fcm_token  = device.fcm_token,
                ))

    await db.commit()

    return Result(
        code    = 200,
        message = "OTP verified",
        extra   = {
            "client_key" : session.client_key,
            "valid_till" : session.valid_till.isoformat(),
        },
    ).http_response()

