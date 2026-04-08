# api/class_teacher.py
"""
Manage Class Section & Teachers
--------------------------------
Uses existing table: school_class_emp_mapping
  - role_id = 2  → Class Teacher
  - role_id = 1  → Subject Teacher (or any other role)

The list API groups records by class + section and returns:
  - class_teacher  : employee with role_id = 2 mapped to that class
  - subject_teachers: all other employees mapped to that class (with subject name)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from database.session import get_db
from database.redis_cache import cache
from models.employee_models import EmployeeClassMapping, Employee, Role
from models.school_stream_models import (
    SchoolStreamClass,
    SchoolStreamClassSection,
    SchoolStreamSubject,
    SchoolGroup,
)
from schemas.class_teacher_schemas import ClassSectionTeacherCreate, ClassSectionTeacherUpdate
from security.valid_session import valid_session
from response.result import Result
from typing import Optional
from collections import defaultdict

class_teacher_router = APIRouter(
    tags=["CLASS SECTION & TEACHERS"],
    dependencies=[Depends(valid_session)],
)

CACHE_TTL = 86400
CLASS_TEACHER_ROLE_ID = 2   # role_id for "Class Teacher"


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
                "total": 1,
                "page": 1,
                "limit": 10,
                "data": [
                    {
                        "class_id":       1,
                        "class_code":     "5",
                        "section_id":     3,
                        "section_code":   "C",
                        "group_name":     "Primary",
                        "class_teacher":  {"map_id": 1, "emp_id": 2, "emp_name": "Vanshika"},
                        "subject_teachers": [
                            {"map_id": 2, "emp_id": 3, "emp_name": "Sahasra",  "subject_id": 1, "subject_name": "Telugu"},
                            {"map_id": 3, "emp_id": 4, "emp_name": "Safa Anjum", "subject_id": 2, "subject_name": "Hindi"},
                        ]
                    }
                ]
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

    # ── base stmt: join mapping → employee → role → class → subject ──────────
    stmt = (
        select(
            EmployeeClassMapping.map_id,
            EmployeeClassMapping.emp_id,
            EmployeeClassMapping.class_id,
            EmployeeClassMapping.subject_id,
            Employee.first_name,
            Employee.last_name,
            Employee.role_id,
            Role.role_name,
            SchoolStreamClass.class_code,
            SchoolStreamClass.school_group_id,
            SchoolGroup.group_name,
            SchoolStreamSubject.subject_name,
        )
        .join(Employee,           EmployeeClassMapping.emp_id     == Employee.id)
        .join(Role,               Employee.role_id                == Role.role_id)
        .join(SchoolStreamClass,  EmployeeClassMapping.class_id   == SchoolStreamClass.class_id)
        .outerjoin(SchoolGroup,   SchoolStreamClass.school_group_id == SchoolGroup.school_group_id)
        .join(SchoolStreamSubject, EmployeeClassMapping.subject_id == SchoolStreamSubject.subject_id)
    )

    # ── filters ───────────────────────────────────────────────────────────────
    if class_id:
        stmt = stmt.where(EmployeeClassMapping.class_id == class_id)
    if school_group_id:
        stmt = stmt.where(SchoolStreamClass.school_group_id == school_group_id)
    if search:
        s = f"%{search}%"
        stmt = stmt.where(or_(
            Employee.first_name.like(s),
            Employee.last_name.like(s),
            SchoolStreamSubject.subject_name.like(s),
        ))

    rows = (await db.execute(stmt.order_by(EmployeeClassMapping.class_id, EmployeeClassMapping.map_id))).all()

    # ── fetch sections for each class_id (mapping table has no section_id) ───
    class_ids = list({r.class_id for r in rows})
    section_rows = []
    if class_ids:
        sec_stmt = (
            select(
                SchoolStreamClassSection.section_id,
                SchoolStreamClassSection.class_id,
                SchoolStreamClassSection.section_code,
                SchoolStreamClassSection.section_name,
            )
            .where(SchoolStreamClassSection.class_id.in_(class_ids))
        )
        if section_id:
            sec_stmt = sec_stmt.where(SchoolStreamClassSection.section_id == section_id)
        section_rows = (await db.execute(sec_stmt)).all()

    # build section map: class_id → list of sections
    section_map: dict = defaultdict(list)
    for sec in section_rows:
        section_map[sec.class_id].append({
            "section_id":   sec.section_id,
            "section_code": sec.section_code,
            "section_name": sec.section_name,
        })

    # ── group rows by class_id ────────────────────────────────────────────────
    class_map: dict = defaultdict(lambda: {"class_teacher": None, "subject_teachers": []})
    class_meta: dict = {}

    for r in rows:
        cid = r.class_id
        if cid not in class_meta:
            class_meta[cid] = {
                "class_id":   cid,
                "class_code": r.class_code,
                "group_name": r.group_name,
            }
        emp_name = f"{r.first_name} {r.last_name or ''}".strip()
        entry = {
            "map_id":       r.map_id,
            "emp_id":       r.emp_id,
            "emp_name":     emp_name,
            "subject_id":   r.subject_id,
            "subject_name": r.subject_name,
            "role_name":    r.role_name,
        }
        if r.role_id == CLASS_TEACHER_ROLE_ID:
            class_map[cid]["class_teacher"] = {
                "map_id":   r.map_id,
                "emp_id":   r.emp_id,
                "emp_name": emp_name,
            }
        else:
            class_map[cid]["subject_teachers"].append(entry)

    # ── build result — expand each class × its sections ───────────────────────
    result_list = []
    for cid, meta in class_meta.items():
        sections = section_map.get(cid, [{"section_id": None, "section_code": None, "section_name": None}])
        for sec in sections:
            result_list.append({
                "class_id":        cid,
                "class_code":      meta["class_code"],
                "section_id":      sec["section_id"],
                "section_code":    sec["section_code"],
                "section_name":    sec["section_name"],
                "group_name":      meta["group_name"],
                "class_teacher":   class_map[cid]["class_teacher"],
                "subject_teachers": class_map[cid]["subject_teachers"],
            })

    # ── pagination ────────────────────────────────────────────────────────────
    total  = len(result_list)
    offset = (page - 1) * limit
    paged  = result_list[offset: offset + limit]

    data = {"total": total, "page": page, "limit": limit, "data": paged}
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)

    return Result(code=200, message="Class section teachers fetched successfully.", extra=data).http_response()


# ══════════════════════════════════════════════
# CREATE mapping
# ══════════════════════════════════════════════

@class_teacher_router.post(
    "/class_section_teacher/create",
    summary="Assign employee to class + subject",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Mapping created successfully.", "result": {"map_id": 1, "emp_id": 1, "class_id": 1, "subject_id": 2}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Employee not found.", "result": {}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Mapping already exists.", "result": {}}}}},
    },
)
async def create_mapping(payload: ClassSectionTeacherCreate, db: AsyncSession = Depends(get_db)):
    # verify employee
    emp = (await db.execute(select(Employee.id).where(Employee.id == payload.emp_id))).scalar_one_or_none()
    if not emp:
        return Result(code=404, message="Employee not found.", extra={}).http_response()

    # duplicate check
    exists = (await db.execute(
        select(EmployeeClassMapping.map_id).where(
            EmployeeClassMapping.emp_id    == payload.emp_id,
            EmployeeClassMapping.class_id  == payload.class_id,
            EmployeeClassMapping.subject_id == payload.subject_id,
        )
    )).scalar_one_or_none()
    if exists:
        return Result(code=409, message="Mapping already exists for this employee, class, and subject.", extra={}).http_response()

    obj = EmployeeClassMapping(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    await cache.delete_pattern("class_teacher:list:*")
    return Result(code=201, message="Mapping created successfully.", extra={
        "map_id":     obj.map_id,
        "emp_id":     obj.emp_id,
        "class_id":   obj.class_id,
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
