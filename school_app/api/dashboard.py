# api/dashboard.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.session import get_db
from database.redis_cache import cache
from models.school_stream_models import SchoolStreamClass, SchoolStream
from models.student_models import Student
from models.employee_models import Employee
from models.transport_models import VehicleDetails
from models.exam_models import Exam
from models.notification_models import Notification
from security.valid_session import valid_session
from response.result import Result
from datetime import date

dashboard_router = APIRouter(tags=["DASHBOARD"], dependencies=[Depends(valid_session)])

CACHE_TTL = 300  # 5 minutes — dashboard data should refresh frequently


# ─── helpers ──────────────────────────────────────────────────────────────────

def _dashboard_key(session_yr: str | None) -> str:
    return f"dashboard:overview:{session_yr}"


# ─── MAIN DASHBOARD ───────────────────────────────────────────────────────────

@dashboard_router.get(
    "/overview",
    summary="Dashboard overview",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200,
            "message": "Dashboard fetched successfully.",
            "result": {
                "stats": {
                    "total_students":  1234,
                    "active_students": 1200,
                    "total_teachers":  56,
                    "active_teachers": 54,
                    "total_classes":   24,
                    "active_classes":  22,
                    "total_buses":     8,
                    "active_buses":    8,
                },
                "summary": {
                    "exams_this_month": 5,
                    "notices_posted":   5,
                },
            },
        }}}}
    },
)
async def get_dashboard(
    session_yr: str | None = Query(None, description="Filter by session year e.g. 2025-2026"),
    db: AsyncSession = Depends(get_db),
):
    key = _dashboard_key(session_yr)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Dashboard fetched successfully (cache).", extra=cached).http_response()

    today = date.today()

    # ── 1. Total Students ─────────────────────────────────────────────────────
    total_students  = (await db.execute(select(func.count()).select_from(Student))).scalar_one()
    active_students = (await db.execute(
        select(func.count()).select_from(Student).where(Student.status == "active")
    )).scalar_one()

    # ── 1b. Student gender counts ──────────────────────────────────────────────
    male_students   = (await db.execute(
        select(func.count()).select_from(Student)
        .where(Student.status == "active", Student.gender == "male")
    )).scalar_one()
    female_students = (await db.execute(
        select(func.count()).select_from(Student)
        .where(Student.status == "active", Student.gender == "female")
    )).scalar_one()

    # ── 2. Total Teachers (employees with is_active) ──────────────────────────
    total_teachers  = (await db.execute(select(func.count()).select_from(Employee))).scalar_one()
    active_teachers = (await db.execute(
        select(func.count()).select_from(Employee).where(Employee.is_active == True)
    )).scalar_one()

    # ── 3. Total Classes ──────────────────────────────────────────────────────
    total_streams  = (await db.execute(select(func.count()).select_from(SchoolStream))).scalar_one()
    total_classes  = (await db.execute(select(func.count()).select_from(SchoolStreamClass))).scalar_one()
    active_classes = (await db.execute(
        select(func.count()).select_from(SchoolStreamClass).where(SchoolStreamClass.status == "active")
    )).scalar_one()

    # ── 4. Buses ──────────────────────────────────────────────────────────────
    total_buses  = (await db.execute(select(func.count()).select_from(VehicleDetails))).scalar_one()
    active_buses = (await db.execute(
        select(func.count()).select_from(VehicleDetails).where(VehicleDetails.status == "A")
    )).scalar_one()

    # ── 5. Exams this month ───────────────────────────────────────────────────
    exam_stmt = (
        select(func.count()).select_from(Exam)
        .where(
            func.month(Exam.created_at) == today.month,
            func.year(Exam.created_at)  == today.year,
            Exam.is_active == True,
        )
    )
    if session_yr:
        exam_stmt = exam_stmt.where(Exam.session_yr == session_yr)
    exams_this_month = (await db.execute(exam_stmt)).scalar_one()

    # ── 6. Notices posted (from notification table) ───────────────────────────
    notices_posted = (await db.execute(
        select(func.count()).select_from(Notification)
        .where(
            func.month(Notification.created_at) == today.month,
            func.year(Notification.created_at)  == today.year,
        )
    )).scalar_one()

    # ── Build response ────────────────────────────────────────────────────────
    data = {
        "stats": {
            "total_students":  total_students,
            "active_students": active_students,
            "male_students":   male_students,
            "female_students": female_students,
            "total_teachers":  total_teachers,
            "active_teachers": active_teachers,
            "total_classes":   total_classes,
            "total_streams":   total_streams,
            "active_classes":  active_classes,
            "total_buses":     total_buses,
            "active_buses":    active_buses,
        },
        "summary": {
            "exams_this_month": exams_this_month,
            "notices_posted":   notices_posted,
        },
    }

    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Dashboard fetched successfully.", extra=data).http_response()


# ─── TODAY'S BIRTHDAYS ────────────────────────────────────────────────────────

@dashboard_router.get(
    "/birthdays/today",
    summary="Today's student birthdays",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200, "message": "Birthdays fetched successfully.",
            "result": [
                {
                    "student_id": 1,
                    "first_name": "John",
                    "last_name":  "Doe",
                    "dob":        "2010-04-11",
                    "age":        15,
                    "phone":      "9876543210",
                    "gender":     "male",
                    "class_code": "5",
                }
            ],
        }}}},
    },
)
async def get_today_birthdays(db: AsyncSession = Depends(get_db)):
    today = date.today()
    key   = f"dashboard:birthdays:{today}"

    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Birthdays fetched successfully (cache).", extra=cached).http_response()

    from models.student_models import StudentClassMapping
    from sqlalchemy import and_

    rows = (await db.execute(
        select(
            Student.student_id,
            Student.first_name,
            Student.last_name,
            Student.dob,
            Student.phone,
            Student.gender,
            SchoolStreamClass.class_code,
        )
        .outerjoin(StudentClassMapping, and_(
            StudentClassMapping.student_id == Student.student_id,
            StudentClassMapping.status == "active",
            StudentClassMapping.is_active == True,
        ))
        .outerjoin(SchoolStreamClass, StudentClassMapping.class_id == SchoolStreamClass.class_id)
        .where(
            func.month(Student.dob) == today.month,
            func.day(Student.dob)   == today.day,
            Student.status == "active",
        )
        .order_by(Student.first_name)
    )).all()

    data = [
        {
            "student_id": r.student_id,
            "first_name": r.first_name,
            "last_name":  r.last_name,
            "dob":        r.dob.isoformat() if r.dob else None,
            "age":        today.year - r.dob.year if r.dob else None,
            "phone":      r.phone,
            "gender":     r.gender.value if r.gender else None,
            "class_code": r.class_code,
        }
        for r in rows
    ]

    if data:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Birthdays fetched successfully.", extra=data).http_response()
