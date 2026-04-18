# api/class_teacher.py
"""
Manage Class Section & Teachers
--------------------------------
Uses table: school_class_emp_mapping
  - role_id = 2  → Class Teacher   (POST /class_teacher/create)
  - role_id = 1  → Subject Teacher (POST /subject_teacher/create)

The list API groups records by class + section and returns:
  - class_teacher   : employee with role_id = 2 mapped to that class/section
  - subject_teachers: all other employees mapped to that class (with subject name)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from database.session import get_db
from database.redis_cache import cache
from models.employee_models import EmployeeClassMapping, Employee, Role
from models.school_stream_models import (
    SchoolStreamClass,
    SchoolStreamClassSection,
    SchoolStreamSubject,
    SchoolGroup,
)
from schemas.class_teacher_schemas import (
    ClassTeacherCreate,
    SubjectTeacherCreate,
    ClassSectionTeacherUpdate,
)
from security.valid_session import valid_session
from response.result import Result
from typing import Optional
from collections import defaultdict

class_teacher_router = APIRouter(
    tags=["CLASS SECTION & TEACHERS"],
    dependencies=[Depends(valid_session)],
)

CACHE_TTL = 86400
CLASS_TEACHER_ROLE_ID = 2


# ══════════════════════════════════════════════
# LIST — grouped by class + section
# ══════════════════════════════════════════════

@class_teacher_router.get(
    "/class_section_teacher/list",
    summary="List Class Section & Teachers (grouped)",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200,
            "message": "Class section teachers fetched successfully.",
            "result": {
                "total": 1, "page": 1, "limit": 10,
                "data": [{
                    "class_id": 1, "class_code": "5",
                    "school_group_id": 1,
                    "section_id": 3, "section_code": "C",
                    "group_name": "Primary",
                    "class_teacher": {"map_id": 1, "emp_id": 2026001, "emp_name": "Vanshika"},
                    "subject_teachers": [
                        {"map_id": 2, "emp_id": 2026003, "emp_name": "Suresh Babu", "subject_id": 1, "subject_name": "Telugu"},
                    ]
                }]
            }
        }}}}
    },
)
async def list_class_section_teachers(
    class_id:        Optional[int] = Query(None),
    section_id:      Optional[int] = Query(None),
    school_group_id: Optional[int] = Query(None),
    search:          Optional[str] = Query(None, description="Search by employee name or subject name"),
    page:            int           = Query(1,  ge=1),
    limit:           int           = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    key = f"class_teacher:list:{class_id}:{section_id}:{school_group_id}:{search}:{page}:{limit}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Class section teachers fetched successfully (cache).", extra=cached).http_response()

    stmt = (
        select(
            EmployeeClassMapping.map_id,
            EmployeeClassMapping.emp_id,
            EmployeeClassMapping.role_id,
            EmployeeClassMapping.class_id,
            EmployeeClassMapping.section_id,
            EmployeeClassMapping.subject_id,
            Employee.first_name,
            Employee.last_name,
            SchoolStreamClass.class_code,
            SchoolStreamClass.school_group_id,
            SchoolGroup.group_name,
            SchoolStreamClassSection.section_code,
            SchoolStreamSubject.subject_name,
        )
        # FK is emp_id → employee.emp_id (not employee.id)
        .join(Employee,                 EmployeeClassMapping.emp_id     == Employee.emp_id)
        .join(SchoolStreamClass,        EmployeeClassMapping.class_id   == SchoolStreamClass.class_id)
        .join(SchoolStreamClassSection, EmployeeClassMapping.section_id == SchoolStreamClassSection.section_id)
        .outerjoin(SchoolGroup,         SchoolStreamClass.school_group_id == SchoolGroup.school_group_id)
        .outerjoin(SchoolStreamSubject, EmployeeClassMapping.subject_id == SchoolStreamSubject.subject_id)
    )

    if class_id:
        stmt = stmt.where(EmployeeClassMapping.class_id == class_id)
    if section_id:
        stmt = stmt.where(EmployeeClassMapping.section_id == section_id)
    if school_group_id:
        stmt = stmt.where(SchoolStreamClass.school_group_id == school_group_id)
    if search:
        s = f"%{search}%"
        stmt = stmt.where(or_(
            Employee.first_name.like(s),
            Employee.last_name.like(s),
            SchoolStreamSubject.subject_name.like(s),
            SchoolStreamClass.class_code.like(s),
        ))

    rows = (await db.execute(
        stmt.order_by(EmployeeClassMapping.class_id, EmployeeClassMapping.section_id, EmployeeClassMapping.map_id)
    )).all()

    # group by (class_id, section_id)
    group_map:  dict = defaultdict(lambda: {"class_teacher": None, "subject_teachers": []})
    group_meta: dict = {}

    for r in rows:
        key_cs = (r.class_id, r.section_id)
        if key_cs not in group_meta:
            group_meta[key_cs] = {
                "class_id":        r.class_id,
                "class_code":      r.class_code,
                "school_group_id": r.school_group_id,
                "section_id":      r.section_id,
                "section_code":    r.section_code,
                "group_name":      r.group_name,
            }
        emp_name = f"{r.first_name} {r.last_name or ''}".strip()
        if r.role_id == CLASS_TEACHER_ROLE_ID:
            group_map[key_cs]["class_teacher"] = {
                "map_id":   r.map_id,
                "emp_id":   r.emp_id,
                "emp_name": emp_name,
            }
        else:
            group_map[key_cs]["subject_teachers"].append({
                "map_id":       r.map_id,
                "emp_id":       r.emp_id,
                "emp_name":     emp_name,
                "subject_id":   r.subject_id,
                "subject_name": r.subject_name,
            })

    result_list = []
    for key_cs, meta in group_meta.items():
        result_list.append({
            **meta,
            "class_teacher":    group_map[key_cs]["class_teacher"],
            "subject_teachers": group_map[key_cs]["subject_teachers"],
        })

    total  = len(result_list)
    offset = (page - 1) * limit
    paged  = result_list[offset: offset + limit]

    data = {"total": total, "page": page, "limit": limit, "data": paged}
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)

    return Result(code=200, message="Class section teachers fetched successfully.", extra=data).http_response()


# ══════════════════════════════════════════════
# CREATE — Class Teacher  (role_id required)
# ══════════════════════════════════════════════

@class_teacher_router.post(
    "/class_teacher/create",
    summary="Assign class teacher to a class + section",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Class teacher assigned successfully.", "result": {"map_id": 1, "emp_id": 2026003, "role_id": 2, "class_id": 1, "section_id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Employee not found.", "result": {}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Class teacher already assigned for this class and section.", "result": {}}}}},
    },
)
async def create_class_teacher(payload: ClassTeacherCreate, db: AsyncSession = Depends(get_db)):
    # verify employee by emp_id (the FK column)
    emp = (await db.execute(
        select(Employee.emp_id).where(Employee.emp_id == payload.emp_id)
    )).scalar_one_or_none()
    if not emp:
        return Result(code=404, message="Employee not found.", extra={}).http_response()

    # one class teacher per class+section
    exists = (await db.execute(
        select(EmployeeClassMapping.map_id).where(
            EmployeeClassMapping.class_id   == payload.class_id,
            EmployeeClassMapping.section_id == payload.section_id,
            EmployeeClassMapping.role_id    == payload.role_id,
        )
    )).scalar_one_or_none()
    if exists:
        return Result(code=409, message="Class teacher already assigned for this class and section.", extra={}).http_response()

    obj = EmployeeClassMapping(
        emp_id=payload.emp_id,
        role_id=payload.role_id,
        class_id=payload.class_id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    await cache.delete_pattern("class_teacher:list:*")
    return Result(code=201, message="Class teacher assigned successfully.", extra={
        "map_id":     obj.map_id,
        "emp_id":     obj.emp_id,
        "role_id":    obj.role_id,
        "class_id":   obj.class_id,
        "section_id": obj.section_id,
    }).http_response()


# ══════════════════════════════════════════════
# CREATE — Subject Teacher  (subject_id required, no role_id)
# ══════════════════════════════════════════════

@class_teacher_router.post(
    "/subject_teacher/create",
    summary="Assign subject teacher to a class + section + subject",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Subject teacher assigned successfully.", "result": {"map_id": 2, "emp_id": 2026003, "class_id": 1, "section_id": 1, "subject_id": 2}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Employee not found.", "result": {}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "This subject is already assigned to Ravi Kumar for this class and section.", "result": {"assigned_teacher": "Ravi Kumar"}}}}},
    },
)
async def create_subject_teacher(payload: SubjectTeacherCreate, db: AsyncSession = Depends(get_db)):
    # verify employee by emp_id (the FK column)
    emp = (await db.execute(
        select(Employee.emp_id).where(Employee.emp_id == payload.emp_id)
    )).scalar_one_or_none()
    if not emp:
        return Result(code=404, message="Employee not found.", extra={}).http_response()

    # duplicate check — same employee + class + section + subject
    exists = (await db.execute(
        select(EmployeeClassMapping.map_id).where(
            EmployeeClassMapping.emp_id     == payload.emp_id,
            EmployeeClassMapping.class_id   == payload.class_id,
            EmployeeClassMapping.section_id == payload.section_id,
            EmployeeClassMapping.subject_id == payload.subject_id,
        )
    )).scalar_one_or_none()
    if exists:
        return Result(code=409, message="Mapping already exists for this employee, class, section and subject.", extra={}).http_response()

    # subject already mapped to another teacher in same class + section
    subject_conflict = (await db.execute(
        select(EmployeeClassMapping.emp_id)
        .where(
            EmployeeClassMapping.class_id   == payload.class_id,
            EmployeeClassMapping.section_id == payload.section_id,
            EmployeeClassMapping.subject_id == payload.subject_id,
        )
    )).scalar_one_or_none()
    if subject_conflict:
        # fetch the conflicting teacher name
        conflict_emp = (await db.execute(
            select(Employee.first_name, Employee.last_name)
            .where(Employee.emp_id == subject_conflict)
        )).one_or_none()
        conflict_name = f"{conflict_emp.first_name} {conflict_emp.last_name or ''}".strip() if conflict_emp else "another teacher"
        return Result(
            code=409,
            message=f"This subject is already assigned to {conflict_name} for this class and section.",
            extra={"assigned_teacher": conflict_name},
        ).http_response()

    obj = EmployeeClassMapping(
        emp_id=payload.emp_id,
        role_id=None,
        class_id=payload.class_id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    await cache.delete_pattern("class_teacher:list:*")
    return Result(code=201, message="Subject teacher assigned successfully.", extra={
        "map_id":     obj.map_id,
        "emp_id":     obj.emp_id,
        "class_id":   obj.class_id,
        "section_id": obj.section_id,
        "subject_id": obj.subject_id,
    }).http_response()


# ══════════════════════════════════════════════
# UPDATE mapping
# ══════════════════════════════════════════════

@class_teacher_router.put(
    "/class_section_teacher/update/{map_id}",
    summary="Update class-section-teacher mapping",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Mapping updated successfully.", "result": {"map_id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Mapping not found.", "result": {}}}}},
    },
)
async def update_mapping(map_id: int, payload: ClassSectionTeacherUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmployeeClassMapping).where(EmployeeClassMapping.map_id == map_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return Result(code=404, message="Mapping not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()

    await cache.delete_pattern("class_teacher:list:*")
    return Result(code=200, message="Mapping updated successfully.", extra={"map_id": obj.map_id}).http_response()


# ══════════════════════════════════════════════
# DELETE mapping
# ══════════════════════════════════════════════

@class_teacher_router.delete(
    "/class_section_teacher/delete/{map_id}",
    summary="Delete class-section-teacher mapping",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Mapping deleted successfully.", "result": {"map_id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Mapping not found.", "result": {}}}}},
    },
)
async def delete_mapping(map_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmployeeClassMapping).where(EmployeeClassMapping.map_id == map_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return Result(code=404, message="Mapping not found.", extra={}).http_response()

    await db.delete(obj)
    await db.commit()

    await cache.delete_pattern("class_teacher:list:*")
    return Result(code=200, message="Mapping deleted successfully.", extra={"map_id": map_id}).http_response()
