# helper/decorators.py
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Annotated

from database.session import get_db
from models.user_models import Session as SessionModel, DeviceRegistration
from models.student_web_models import Student, SchoolClassStudentMapping
from models.admin_models import SchoolUser, SchoolStreamClass, SchoolStream
from models.teacher_web_models import Employee, EmployeeRoleClassSubjectMap, Role
from database.redis_cache import cache


async def _resolve_user(user_id: str, role: str, db: AsyncSession) -> dict | None:

    if role == "student":
        stmt = (
            select(
                Student,
                SchoolClassStudentMapping.class_id,
                SchoolClassStudentMapping.status.label("mapping_status"),
                SchoolStreamClass.class_name,
                SchoolStreamClass.class_code,
                SchoolStream.stream_name,
            )
            .outerjoin(SchoolClassStudentMapping, SchoolClassStudentMapping.student_id == Student.student_id)
            .outerjoin(SchoolStreamClass, SchoolStreamClass.class_id == SchoolClassStudentMapping.class_id)
            .outerjoin(SchoolStream, SchoolStream.school_stream_id == SchoolStreamClass.school_stream_id)
            .where(Student.student_id == int(user_id))
        )
        result = await db.execute(stmt)
        row = result.first()

        if row:
            student = row[0]
            return {
                "id":             student.student_id,
                "role":           "student",
                "name":           f"{student.first_name} {student.last_name or ''}".strip(),
                "phone":          student.phone,
                "email":          student.email,
                "gender":         student.gender,
                "dob":            student.dob.isoformat() if student.dob else None,
                "blood_group":    student.blood_group,
                "status":         student.status,
                "class": {
                    "class_id":   row.class_id,
                    "class_name": row.class_name,
                    "section":    row.class_code,
                    "stream":     row.stream_name,
                    "status":     row.mapping_status,
                } if row.class_id else None,
                "guardian": {
                    "name":   f"{student.guardian_first_name or ''} {student.guardian_last_name or ''}".strip() or None,
                    "phone":  student.guardian_phone,
                    "email":  student.guardian_email,
                    "gender": student.guardian_gender,
                }
            }

    else:
        su_stmt = select(SchoolUser).where(SchoolUser.user_id == int(user_id))
        su_result = await db.execute(su_stmt)
        school_user = su_result.scalar_one_or_none()

        if school_user:
            emp_stmt = (
                select(
                    Employee,
                    EmployeeRoleClassSubjectMap.class_id,
                    SchoolStreamClass.class_name,
                    SchoolStreamClass.class_code,
                    SchoolStream.stream_name,
                    Role.role_name,
                )
                .outerjoin(EmployeeRoleClassSubjectMap, EmployeeRoleClassSubjectMap.emp_id == Employee.id)
                .outerjoin(SchoolStreamClass, SchoolStreamClass.class_id == EmployeeRoleClassSubjectMap.class_id)
                .outerjoin(SchoolStream, SchoolStream.school_stream_id == SchoolStreamClass.school_stream_id)
                .outerjoin(Role, Role.role_id == EmployeeRoleClassSubjectMap.role_id)
                .where(Employee.mobile == school_user.phone)
            )
            emp_result = await db.execute(emp_stmt)
            emp_row = emp_result.first()

            return {
                "id":           school_user.user_id,
                "role":         school_user.role,
                "name":         school_user.full_name,
                "phone":        school_user.phone,
                "email":        school_user.email,
                "status":       school_user.status,
                "employee": {
                    "emp_id":        emp_row[0].id,
                    "gender":        emp_row[0].gender,
                    "dob":           emp_row[0].DOB.isoformat() if emp_row[0].DOB else None,
                    "qualification": emp_row[0].qualification,
                    "joining_date":  emp_row[0].joining_dt.isoformat() if emp_row[0].joining_dt else None,
                    "class": {
                        "class_id":   emp_row.class_id,
                        "class_name": emp_row.class_name,
                        "section":    emp_row.class_code,
                        "stream":     emp_row.stream_name,
                    } if emp_row.class_id else None,
                    "role_name": emp_row.role_name,
                } if emp_row else None
            }

    return None


async def validate_session(
    client_key: Annotated[str, Header(description="Client key from device registration")],
    db: AsyncSession = Depends(get_db),
) -> SessionModel:

    cache_key = f"session:{client_key}"

    # 1. Check cache first
    cached = await cache.get(cache_key)
    if cached:
        valid_till = datetime.fromisoformat(cached["valid_till"])

        if valid_till < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please re-register your device."
            )

        session = SessionModel(
            id         = cached["id"],
            device_id  = cached["device_id"],
            user_id    = cached["user_id"],
            role       = cached.get("role"),
            client_key = cached["client_key"],
            valid_till = valid_till,
        )

        if cached.get("device"):
            session.device = DeviceRegistration(
                id        = cached["device"]["id"],
                device_id = cached["device"]["device_id"],
                fcm_token = cached["device"]["fcm_token"],
                os        = cached["device"]["os"],
                is_active = cached["device"]["is_active"],
            )

        session.user = cached.get("user")
        return session

    # 2. Cache miss — query DB
    stmt = (
        select(SessionModel)
        .options(selectinload(SessionModel.device))
        .where(SessionModel.client_key == client_key)
    )

    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client key."
        )

    # 3. Check expiry
    if session.valid_till < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please re-register your device."
        )

    # 4. Resolve user if user_id + role are set
    user_data = None
    if session.user_id and session.role:
        user_data = await _resolve_user(session.user_id, session.role, db)

    session.user = user_data

    # 5. Store in cache
    await cache.set(
        cache_key,
        {
            "id":         session.id,
            "device_id":  session.device_id,
            "user_id":    session.user_id,
            "role":       session.role,
            "client_key": session.client_key,
            "valid_till": session.valid_till.isoformat(),
            "device": {
                "id":        session.device.id,
                "device_id": session.device.device_id,
                "fcm_token": session.device.fcm_token,
                "os":        session.device.os,
                "is_active": session.device.is_active,
            },
            "user": user_data,
        },
        expire=300
    )

    return session
