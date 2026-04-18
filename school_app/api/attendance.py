# api/attendance.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.session import get_db
from database.redis_cache import cache
from models.attendance_models import EmployeeAttendance, StudentAttendance
from models.employee_models import Employee
from models.student_models import Student
from schemas.attendance_schemas import (
    EmpAttendanceBulkCreate, EmpAttendanceUpdate,
    StudentAttendanceBulkCreate, StudentAttendanceUpdate,
)
from security.valid_session import valid_session
from response.result import Result
from typing import Optional
from datetime import date

attendance_router = APIRouter(
    tags=["ATTENDANCE"],
    dependencies=[Depends(valid_session)],
)

CACHE_TTL = 86400


# ══════════════════════════════════════════════
# EMPLOYEE ATTENDANCE
# ══════════════════════════════════════════════

@attendance_router.post(
    "/employee/attendance/bulk",
    summary="Bulk create employee attendance",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Employee attendance created successfully.", "result": {"created": [1, 2], "skipped": [3]}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Attendance already exists for all employees.", "result": {"skipped": [1, 2]}}}}},
    },
)
async def create_bulk_employee_attendance(
    payload: EmpAttendanceBulkCreate,
    db: AsyncSession = Depends(get_db),
):
    created = []
    skipped = []

    for emp in payload.employees:
        exists = await db.scalar(
            select(EmployeeAttendance.att_id).where(
                EmployeeAttendance.emp_id       == emp.emp_id,
                EmployeeAttendance.attendance_dt == payload.attendance_dt,
            )
        )
        if exists:
            skipped.append(emp.emp_id)
            continue

        db.add(EmployeeAttendance(
            school_group_id=payload.school_group_id,
            emp_id=emp.emp_id,
            attendance_dt=payload.attendance_dt,
            status=emp.status,
        ))
        created.append(emp.emp_id)

    if not created:
        return Result(code=409, message="Attendance already exists for all employees.", extra={"skipped": skipped}).http_response()

    await db.commit()
    await cache.delete_pattern(f"emp_attendance:list:*")
    return Result(code=201, message="Employee attendance created successfully.", extra={
        "created": created,
        "skipped": skipped,
    }).http_response()


@attendance_router.get(
    "/employee/attendance/list",
    summary="List employee attendance (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Employee attendance fetched successfully.", "result": {"total": 2, "page": 1, "limit": 10, "data": [{"att_id": 1, "emp_id": 1, "emp_name": "John Doe", "attendance_dt": "2024-06-01", "status": "P"}]}}}}},
    },
)
async def list_employee_attendance(
    school_group_id: Optional[int]  = Query(None),
    emp_id:          Optional[int]  = Query(None),
    attendance_dt:   Optional[date] = Query(None),
    status:          Optional[str]  = Query(None, description="P or A"),
    page:            int            = Query(1,  ge=1),
    limit:           int            = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    key = f"emp_attendance:list:{school_group_id}:{emp_id}:{attendance_dt}:{status}:{page}:{limit}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Employee attendance fetched successfully (cache).", extra=cached).http_response()

    stmt = (
        select(
            EmployeeAttendance.att_id,
            EmployeeAttendance.emp_id,
            EmployeeAttendance.school_group_id,
            EmployeeAttendance.attendance_dt,
            EmployeeAttendance.status,
            Employee.first_name,
            Employee.last_name,
        )
        .outerjoin(Employee, EmployeeAttendance.emp_id == Employee.id)
    )

    if school_group_id: stmt = stmt.where(EmployeeAttendance.school_group_id == school_group_id)
    if emp_id:          stmt = stmt.where(EmployeeAttendance.emp_id          == emp_id)
    if attendance_dt:   stmt = stmt.where(EmployeeAttendance.attendance_dt   == attendance_dt)
    if status:          stmt = stmt.where(EmployeeAttendance.status          == status.upper())

    total  = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    offset = (page - 1) * limit
    rows   = (await db.execute(stmt.order_by(EmployeeAttendance.att_id.desc()).offset(offset).limit(limit))).all()

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            {
                "att_id":          r.att_id,
                "emp_id":          r.emp_id,
                "emp_name":        f"{r.first_name or ''} {r.last_name or ''}".strip(),
                "school_group_id": r.school_group_id,
                "attendance_dt":   str(r.attendance_dt),
                "status":          r.status,
            }
            for r in rows
        ],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Employee attendance fetched successfully.", extra=data).http_response()


@attendance_router.get(
    "/employee/attendance/get/{att_id}",
    summary="Get employee attendance by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Employee attendance fetched successfully.", "result": {"att_id": 1, "emp_id": 1, "emp_name": "John Doe", "school_group_id": 1, "attendance_dt": "2024-06-01", "status": "P"}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Attendance record not found.", "result": {}}}}},
    },
)
async def get_employee_attendance(att_id: int, db: AsyncSession = Depends(get_db)):
    key = f"emp_attendance:{att_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Employee attendance fetched successfully (cache).", extra=cached).http_response()

    row = (await db.execute(
        select(
            EmployeeAttendance.att_id,
            EmployeeAttendance.emp_id,
            EmployeeAttendance.school_group_id,
            EmployeeAttendance.attendance_dt,
            EmployeeAttendance.status,
            Employee.first_name,
            Employee.last_name,
        )
        .outerjoin(Employee, EmployeeAttendance.emp_id == Employee.id)
        .where(EmployeeAttendance.att_id == att_id)
    )).one_or_none()

    if not row:
        return Result(code=404, message="Attendance record not found.", extra={}).http_response()

    data = {
        "att_id":          row.att_id,
        "emp_id":          row.emp_id,
        "emp_name":        f"{row.first_name or ''} {row.last_name or ''}".strip(),
        "school_group_id": row.school_group_id,
        "attendance_dt":   str(row.attendance_dt),
        "status":          row.status,
    }
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Employee attendance fetched successfully.", extra=data).http_response()


@attendance_router.put(
    "/employee/attendance/update/{att_id}",
    summary="Update employee attendance status",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Employee attendance updated successfully.", "result": {"att_id": 1, "status": "P"}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Attendance record not found.", "result": {}}}}},
    },
)
async def update_employee_attendance(
    att_id: int,
    payload: EmpAttendanceUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmployeeAttendance).where(EmployeeAttendance.att_id == att_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return Result(code=404, message="Attendance record not found.", extra={}).http_response()

    obj.status = payload.status
    await db.commit()

    await cache.delete(f"emp_attendance:{att_id}")
    await cache.delete_pattern("emp_attendance:list:*")
    return Result(code=200, message="Employee attendance updated successfully.", extra={
        "att_id": obj.att_id,
        "emp_id": obj.emp_id,
        "status": obj.status,
    }).http_response()


@attendance_router.delete(
    "/employee/attendance/delete/{att_id}",
    summary="Delete employee attendance record",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Employee attendance deleted successfully.", "result": {"att_id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Attendance record not found.", "result": {}}}}},
    },
)
async def delete_employee_attendance(att_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmployeeAttendance).where(EmployeeAttendance.att_id == att_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return Result(code=404, message="Attendance record not found.", extra={}).http_response()

    await db.delete(obj)
    await db.commit()

    await cache.delete_pattern("emp_attendance:list:*")
    return Result(code=200, message="Employee attendance deleted successfully.", extra={"att_id": att_id}).http_response()


# ══════════════════════════════════════════════
# STUDENT ATTENDANCE
# ══════════════════════════════════════════════

@attendance_router.post(
    "/student/attendance/bulk",
    summary="Bulk create student attendance",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Student attendance created successfully.", "result": {"created": [1, 2], "skipped": [3]}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Attendance already exists for all students.", "result": {"skipped": [1, 2]}}}}},
    },
)
async def create_bulk_student_attendance(
    payload: StudentAttendanceBulkCreate,
    db: AsyncSession = Depends(get_db),
):
    created = []
    skipped = []

    for student in payload.students:
        exists = await db.scalar(
            select(StudentAttendance.att_id).where(
                StudentAttendance.student_id    == student.student_id,
                StudentAttendance.attendance_dt == payload.attendance_dt,
            )
        )
        if exists:
            skipped.append(student.student_id)
            continue

        db.add(StudentAttendance(
            class_id=payload.class_id,
            section_id=payload.section_id,
            school_group_id=payload.school_group_id,
            student_id=student.student_id,
            attendance_dt=payload.attendance_dt,
            status=student.status,
        ))
        created.append(student.student_id)

    if not created:
        return Result(code=409, message="Attendance already exists for all students.", extra={"skipped": skipped}).http_response()

    await db.commit()
    await cache.delete_pattern("student_attendance:list:*")
    return Result(code=201, message="Student attendance created successfully.", extra={
        "created": created,
        "skipped": skipped,
    }).http_response()


@attendance_router.get(
    "/student/attendance/list",
    summary="List student attendance (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Student attendance fetched successfully.", "result": {"total": 2, "page": 1, "limit": 10, "data": [{"att_id": 1, "student_id": 1, "student_name": "Arjun Kumar", "class_id": 1, "section_id": 1, "attendance_dt": "2024-06-01", "status": "P"}]}}}}},
    },
)
async def list_student_attendance(
    school_group_id: Optional[int]  = Query(None),
    class_id:        Optional[int]  = Query(None),
    section_id:      Optional[int]  = Query(None),
    student_id:      Optional[int]  = Query(None),
    attendance_dt:   Optional[date] = Query(None),
    status:          Optional[str]  = Query(None, description="P or A"),
    page:            int            = Query(1,  ge=1),
    limit:           int            = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    key = f"student_attendance:list:{school_group_id}:{class_id}:{section_id}:{student_id}:{attendance_dt}:{status}:{page}:{limit}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Student attendance fetched successfully (cache).", extra=cached).http_response()

    stmt = (
        select(
            StudentAttendance.att_id,
            StudentAttendance.student_id,
            StudentAttendance.class_id,
            StudentAttendance.section_id,
            StudentAttendance.school_group_id,
            StudentAttendance.attendance_dt,
            StudentAttendance.status,
            Student.first_name,
            Student.last_name,
        )
        .outerjoin(Student, StudentAttendance.student_id == Student.student_id)
    )

    if school_group_id: stmt = stmt.where(StudentAttendance.school_group_id == school_group_id)
    if class_id:        stmt = stmt.where(StudentAttendance.class_id        == class_id)
    if section_id:      stmt = stmt.where(StudentAttendance.section_id      == section_id)
    if student_id:      stmt = stmt.where(StudentAttendance.student_id      == student_id)
    if attendance_dt:   stmt = stmt.where(StudentAttendance.attendance_dt   == attendance_dt)
    if status:          stmt = stmt.where(StudentAttendance.status          == status.upper())

    total  = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    offset = (page - 1) * limit
    rows   = (await db.execute(stmt.order_by(StudentAttendance.att_id.desc()).offset(offset).limit(limit))).all()

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            {
                "att_id":          r.att_id,
                "student_id":      r.student_id,
                "student_name":    f"{r.first_name or ''} {r.last_name or ''}".strip(),
                "class_id":        r.class_id,
                "section_id":      r.section_id,
                "school_group_id": r.school_group_id,
                "attendance_dt":   str(r.attendance_dt),
                "status":          r.status,
            }
            for r in rows
        ],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Student attendance fetched successfully.", extra=data).http_response()


@attendance_router.put(
    "/student/attendance/update",
    summary="Update student attendance status",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Student attendance updated successfully.", "result": {"att_id": 1, "status": "A"}}}}},
        400: {"content": {"application/json": {"example": {"code": 400, "message": "Provide at least att_id or student_id + attendance_dt.", "result": {}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Attendance record not found.", "result": {}}}}},
    },
)
async def update_student_attendance(
    payload:       StudentAttendanceUpdate,
    att_id:        int | None  = Query(None, description="Filter by attendance record ID"),
    student_id:    int | None  = Query(None, description="Filter by student ID"),
    attendance_dt: date | None = Query(None, description="Filter by attendance date e.g. 2024-06-01"),
    db: AsyncSession = Depends(get_db),
):
    if att_id is None and student_id is None:
        return Result(code=400, message="Provide either att_id or student_id.", extra={}).http_response()

    stmt = select(StudentAttendance)
    if att_id is not None:
        stmt = stmt.where(StudentAttendance.att_id == att_id)
    if student_id is not None:
        stmt = stmt.where(StudentAttendance.student_id == student_id)
    if attendance_dt is not None:
        stmt = stmt.where(StudentAttendance.attendance_dt == attendance_dt)

    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if not obj:
        return Result(code=404, message="Attendance record not found.", extra={}).http_response()

    obj.status = payload.status
    await db.commit()

    await cache.delete_pattern("student_attendance:list:*")
    return Result(code=200, message="Student attendance updated successfully.", extra={
        "att_id":     obj.att_id,
        "student_id": obj.student_id,
        "status":     obj.status,
    }).http_response()


@attendance_router.delete(
    "/student/attendance/delete/{att_id}",
    summary="Delete student attendance record",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Student attendance deleted successfully.", "result": {"att_id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Attendance record not found.", "result": {}}}}},
    },
)
async def delete_student_attendance(att_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StudentAttendance).where(StudentAttendance.att_id == att_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return Result(code=404, message="Attendance record not found.", extra={}).http_response()

    await db.delete(obj)
    await db.commit()

    await cache.delete_pattern("student_attendance:list:*")
    return Result(code=200, message="Student attendance deleted successfully.", extra={"att_id": att_id}).http_response()


# ══════════════════════════════════════════════
# ATTENDANCE COUNT — TODAY
# ══════════════════════════════════════════════

@attendance_router.get(
    "/student/attendance/count/today",
    summary="Student attendance count for today",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200,
            "message": "Student attendance count fetched successfully.",
            "result": {
                "date":       "2024-06-01",
                "total":      300,
                "present":    282,
                "absent":     18,
                "percentage": 94.0,
            }
        }}}}
    },
)
async def student_attendance_count_today(
    group_id:   int | None = Query(None, description="Filter by school group ID"),
    class_id:   int | None = Query(None, description="Filter by class ID"),
    section_id: int | None = Query(None, description="Filter by section ID"),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    key   = f"student_attendance:count:{today}:{group_id}:{class_id}:{section_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Student attendance count fetched successfully (cache).", extra=cached).http_response()

    stmt_base = select(func.count()).select_from(StudentAttendance)\
        .where(StudentAttendance.attendance_dt == today)
    if group_id:
        stmt_base = stmt_base.where(StudentAttendance.school_group_id == group_id)
    if class_id:
        stmt_base = stmt_base.where(StudentAttendance.class_id == class_id)
    if section_id:
        stmt_base = stmt_base.where(StudentAttendance.section_id == section_id)

    total   = (await db.execute(stmt_base)).scalar_one()
    present = (await db.execute(
        stmt_base.where(StudentAttendance.status == "P")
    )).scalar_one()
    absent     = total - present
    percentage = round((present / total * 100), 1) if total > 0 else 0.0

    data = {
        "date":       str(today),
        "total":      total,
        "present":    present,
        "absent":     absent,
        "percentage": percentage,
    }
    if total > 0:
        await cache.set(key, data, expire=300)
    return Result(code=200, message="Student attendance count fetched successfully.", extra=data).http_response()


@attendance_router.get(
    "/employee/attendance/count/today",
    summary="Employee attendance count for today",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200,
            "message": "Employee attendance count fetched successfully.",
            "result": {
                "date":       "2024-06-01",
                "total":      56,
                "present":    50,
                "absent":     6,
                "percentage": 89.3,
            }
        }}}}
    },
)
async def employee_attendance_count_today(
    group_id: int | None = Query(None, description="Filter by school group ID"),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    key   = f"emp_attendance:count:{today}:{group_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Employee attendance count fetched successfully (cache).", extra=cached).http_response()

    stmt_base = select(func.count()).select_from(EmployeeAttendance)\
        .where(EmployeeAttendance.attendance_dt == today)
    if group_id:
        stmt_base = stmt_base.where(EmployeeAttendance.school_group_id == group_id)

    total   = (await db.execute(stmt_base)).scalar_one()
    present = (await db.execute(
        stmt_base.where(EmployeeAttendance.status == "P")
    )).scalar_one()
    absent     = total - present
    percentage = round((present / total * 100), 1) if total > 0 else 0.0

    data = {
        "date":       str(today),
        "total":      total,
        "present":    present,
        "absent":     absent,
        "percentage": percentage,
    }
    if total > 0:
        await cache.set(key, data, expire=300)
    return Result(code=200, message="Employee attendance count fetched successfully.", extra=data).http_response()
