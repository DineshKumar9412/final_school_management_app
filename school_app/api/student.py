# api/student.py
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, update

from database.session import get_db
from database.redis_cache import cache
from models.student_models import StudentAdmissionInquiry, Student, StudentClassMapping
from models.school_stream_models import SchoolStreamClass, SchoolStreamClassSection
from schemas.student_schemas import (
    StudentInquiryCreate,
    StudentInquiryUpdate,
    StudentCreate,
    StudentUpdate,
    StudentMappingUpdate,
)
from response.result import Result
from typing import Optional
from datetime import date
from io import BytesIO
import pandas as pd

student_router = APIRouter(tags=["STUDENT"])

CACHE_TTL = 86400
STATUS_VALUES = {"active", "inactive"}

# ── reusable response examples ────────────────────────────────────────────────
_INQ_RESULT = {"student_inq_id": 1, "student_name": "Arjun Kumar", "gender": "male", "age": 13, "class_id": 1, "guardian_name": "Ramesh Kumar", "guardian_phone": "9876501234", "guardian_occupation": "Business", "guardian_gender": "male"}
_STU_RESULT = {"student_id": 1, "school_id": 1, "student_roll_id": "2026001", "first_name": "Arjun", "last_name": "Kumar", "gender": "male", "dob": "2012-06-15", "age": 13, "email": "arjun@example.com", "phone": "9876543210", "blood_group": "B+", "status": "active", "class_code": "10", "section_code": "A", "section_name": "Rose", "enroll_date": "2024-06-01", "mapping_status": "active"}
_404_INQ  = {"content": {"application/json": {"example": {"code": 404, "message": "Inquiry not found.", "result": {}}}}}
_404_STU  = {"content": {"application/json": {"example": {"code": 404, "message": "Student not found.", "result": {}}}}}
_409_INQ  = {"content": {"application/json": {"example": {"code": 409, "message": "Inquiry with phone already exists.", "result": {}}}}}
_409_STU  = {"content": {"application/json": {"example": {"code": 409, "message": "Student with roll ID already exists.", "result": {}}}}}
_404_MAP  = {"content": {"application/json": {"example": {"code": 404, "message": "Active mapping not found.", "result": {}}}}}


def clean_search(search: str | None) -> str | None:
    if search is None:
        return None
    return search.strip().strip('"').strip("'").strip()


# ══════════════════════════════════════════════
# STUDENT ADMISSION INQUIRY
# ══════════════════════════════════════════════

@student_router.post(
    "/inquiry/create",
    summary="Create student admission inquiry",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Student inquiry created successfully.", "result": {"student_inq_id": 1, "student_name": "Arjun Kumar", "guardian_phone": "9876501234"}}}}},
        409: _409_INQ,
    },
)
async def create_inquiry(payload: StudentInquiryCreate, db: AsyncSession = Depends(get_db)):
    if payload.guardian_phone:
        exists = await db.execute(
            select(StudentAdmissionInquiry.student_inq_id).where(
                StudentAdmissionInquiry.guardian_phone == payload.guardian_phone
            )
        )
        if exists.scalar_one_or_none():
            return Result(code=409, message=f"Inquiry with phone '{payload.guardian_phone}' already exists.", extra={}).http_response()

    obj = StudentAdmissionInquiry(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    await cache.delete_pattern("inquiry:list:*")
    return Result(code=201, message="Student inquiry created successfully.", extra={
        "student_inq_id": obj.student_inq_id,
        "student_name":   obj.student_name,
        "guardian_phone": obj.guardian_phone,
    }).http_response()


@student_router.get(
    "/inquiry/list",
    summary="List student admission inquiries (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Inquiries fetched successfully.", "result": {"total": 1, "page": 1, "limit": 10, "data": [_INQ_RESULT]}}}}}
    },
)
async def list_inquiries(
    page:   int        = Query(1,    ge=1),
    limit:  int        = Query(10,   ge=1, le=100),
    search: str | None = Query(None, description="Search by student_name, guardian_name, guardian_phone, class_id (numeric), or 'all'"),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key = f"inquiry:list:{page}:{limit}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Inquiries fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt = select(StudentAdmissionInquiry)

    if search is not None and search.lower() != "all":
        if search.isdigit():
            stmt = stmt.where(StudentAdmissionInquiry.class_id == int(search))
        else:
            stmt = stmt.where(or_(
                StudentAdmissionInquiry.student_name.like(f"%{search}%"),
                StudentAdmissionInquiry.guardian_name.like(f"%{search}%"),
                StudentAdmissionInquiry.guardian_phone.like(f"%{search}%"),
            ))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await db.execute(stmt.order_by(StudentAdmissionInquiry.student_inq_id.desc()).offset(offset).limit(limit))

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            {
                "student_inq_id":      r.student_inq_id,
                "student_name":        r.student_name,
                "gender":              r.gender,
                "age":                 r.age,
                "class_id":            r.class_id,
                "guardian_name":       r.guardian_name,
                "guardian_phone":      r.guardian_phone,
                "guardian_occupation": r.guardian_occupation,
                "guardian_gender":     r.guardian_gender,
            }
            for r in rows.scalars().all()
        ],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Inquiries fetched successfully.", extra=data).http_response()


@student_router.get(
    "/inquiry/get_id/{inq_id}",
    summary="Get inquiry by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Inquiry fetched successfully.", "result": _INQ_RESULT}}}},
        404: _404_INQ,
    },
)
async def get_inquiry(inq_id: int, db: AsyncSession = Depends(get_db)):
    key = f"inquiry:{inq_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Inquiry fetched successfully (cache).", extra=cached).http_response()

    result = await db.execute(select(StudentAdmissionInquiry).where(StudentAdmissionInquiry.student_inq_id == inq_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Inquiry not found.", extra={}).http_response()

    data = {
        "student_inq_id":      obj.student_inq_id,
        "student_name":        obj.student_name,
        "gender":              obj.gender,
        "age":                 obj.age,
        "class_id":            obj.class_id,
        "guardian_name":       obj.guardian_name,
        "guardian_phone":      obj.guardian_phone,
        "guardian_occupation": obj.guardian_occupation,
        "guardian_gender":     obj.guardian_gender,
    }
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Inquiry fetched successfully.", extra=data).http_response()


@student_router.put(
    "/inquiry/update/{inq_id}",
    summary="Update student inquiry",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Inquiry updated successfully.", "result": {"student_inq_id": 1, "student_name": "Arjun Kumar", "guardian_phone": "9876501234"}}}}},
        404: _404_INQ,
        409: _409_INQ,
    },
)
async def update_inquiry(inq_id: int, payload: StudentInquiryUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StudentAdmissionInquiry).where(StudentAdmissionInquiry.student_inq_id == inq_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Inquiry not found.", extra={}).http_response()

    if payload.guardian_phone:
        dup = await db.execute(
            select(StudentAdmissionInquiry.student_inq_id).where(
                StudentAdmissionInquiry.guardian_phone == payload.guardian_phone,
                StudentAdmissionInquiry.student_inq_id != inq_id,
            )
        )
        if dup.scalar_one_or_none():
            return Result(code=409, message="Another inquiry with this phone already exists.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)

    await cache.delete(f"inquiry:{inq_id}")
    await cache.delete_pattern("inquiry:list:*")
    return Result(code=200, message="Inquiry updated successfully.", extra={
        "student_inq_id": obj.student_inq_id,
        "student_name":   obj.student_name,
        "guardian_phone": obj.guardian_phone,
    }).http_response()


@student_router.delete(
    "/inquiry/delete/{inq_id}",
    summary="Delete student inquiry",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Inquiry deleted successfully.", "result": {"student_inq_id": 1}}}}},
        404: _404_INQ,
    },
)
async def delete_inquiry(inq_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StudentAdmissionInquiry).where(StudentAdmissionInquiry.student_inq_id == inq_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Inquiry not found.", extra={}).http_response()

    await db.delete(obj)
    await db.commit()
    await cache.delete(f"inquiry:{inq_id}")
    await cache.delete_pattern("inquiry:list:*")
    return Result(code=200, message="Inquiry deleted successfully.", extra={"student_inq_id": inq_id}).http_response()


# ══════════════════════════════════════════════
# STUDENT
# ══════════════════════════════════════════════

def _student_joined_stmt():
    return (
        select(
            Student,
            StudentClassMapping,
            SchoolStreamClass.class_code,
            SchoolStreamClassSection.section_code,
            SchoolStreamClassSection.section_name,
        )
        .outerjoin(StudentClassMapping, and_(
            StudentClassMapping.student_id == Student.student_id,
            StudentClassMapping.status == "active",
            StudentClassMapping.is_active == True,
        ))
        .outerjoin(SchoolStreamClass, StudentClassMapping.class_id == SchoolStreamClass.class_id)
        .outerjoin(SchoolStreamClassSection, StudentClassMapping.section_id == SchoolStreamClassSection.section_id)
    )


def _student_row_to_dict(s, m, class_code, section_code, section_name) -> dict:
    return {
        "student_id":      s.student_id,
        "school_id":       s.school_id,
        "student_roll_id": s.student_roll_id,
        "first_name":      s.first_name,
        "last_name":       s.last_name,
        "gender":          s.gender,
        "dob":             str(s.dob) if s.dob else None,
        "age":             s.age,
        "email":           s.email,
        "phone":           s.phone,
        "blood_group":     s.blood_group,
        "status":          s.status,
        "class_code":      class_code,
        "section_code":    section_code,
        "section_name":    section_name,
        "enroll_date":     str(m.enroll_date) if m and m.enroll_date else None,
        "mapping_status":  m.status if m else None,
    }


@student_router.post(
    "/student/create",
    summary="Create a new student",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Student created successfully.", "result": {"student_id": 1, "first_name": "Arjun"}}}}},
        409: _409_STU,
    },
)
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    if payload.student_roll_id:
        exists = await db.execute(
            select(Student.student_id).where(Student.student_roll_id == payload.student_roll_id)
        )
        if exists.scalar_one_or_none():
            return Result(code=409, message=f"Student with roll ID '{payload.student_roll_id}' already exists.", extra={}).http_response()

    student = Student(**payload.model_dump(exclude={"class_id", "section_id", "enroll_date"}))
    db.add(student)
    await db.flush()

    mapping = StudentClassMapping(
        student_id=student.student_id,
        class_id=payload.class_id,
        section_id=payload.section_id,
        enroll_date=payload.enroll_date,
        valid_from_date=date.today(),
        status="active",
        is_active=True,
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(student)

    await cache.delete_pattern("student:list:*")
    return Result(code=201, message="Student created successfully.", extra={
        "student_id": student.student_id,
        "first_name": student.first_name,
    }).http_response()


@student_router.get(
    "/student/get_id/{student_id}",
    summary="Get student by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Student fetched successfully.", "result": {**_STU_RESULT, "address_line1": "12 MG Road", "city": "Chennai", "state": "Tamil Nadu", "country": "India", "postal_code": "600001", "emergency_contact": "9698509001", "guardian_first_name": "Ramesh", "guardian_last_name": "Kumar", "guardian_phone": "9876501234", "guardian_email": "ramesh@example.com", "guardian_gender": "male"}}}}},
        404: _404_STU,
    },
)
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    key = f"student:{student_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Student fetched successfully (cache).", extra=cached).http_response()

    row = (await db.execute(_student_joined_stmt().where(Student.student_id == student_id))).one_or_none()
    if row is None:
        return Result(code=404, message="Student not found.", extra={}).http_response()

    s, m, class_code, section_code, section_name = row
    data = _student_row_to_dict(s, m, class_code, section_code, section_name)
    data.update({
        "address_line1":       s.address_line1,
        "address_line2":       s.address_line2,
        "city":                s.city,
        "state":               s.state,
        "country":             s.country,
        "postal_code":         s.postal_code,
        "emergency_contact":   s.emergency_contact,
        "guardian_first_name": s.guardian_first_name,
        "guardian_last_name":  s.guardian_last_name,
        "guardian_phone":      s.guardian_phone,
        "guardian_email":      s.guardian_email,
        "guardian_gender":     s.guardian_gender,
    })
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Student fetched successfully.", extra=data).http_response()


@student_router.get(
    "/student/list",
    summary="List students (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Students fetched successfully.", "result": {"total": 1, "page": 1, "limit": 10, "data": [_STU_RESULT]}}}}}
    },
)
async def list_students(
    school_id:  int        = Query(...),
    class_id:   int | None = Query(None),
    section_id: int | None = Query(None),
    page:       int        = Query(1,    ge=1),
    limit:      int        = Query(10,   ge=1, le=100),
    search:     str | None = Query(None, description="Search by name/roll/phone/class_code/section_code, 'active'/'inactive', or 'all'"),
    db: AsyncSession = Depends(get_db),
):
    key = f"student:list:{school_id}:{class_id}:{section_id}:{page}:{limit}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Students fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt = _student_joined_stmt().where(Student.school_id == school_id)

    if class_id is not None:
        stmt = stmt.where(StudentClassMapping.class_id == class_id)

    if section_id is not None:
        stmt = stmt.where(StudentClassMapping.section_id == section_id)

    if search is not None and search.lower() in STATUS_VALUES:
        stmt = stmt.where(Student.status == search.lower())
    elif search is not None and search.lower() != "all":
        stmt = stmt.where(or_(
            Student.first_name.like(f"%{search}%"),
            Student.last_name.like(f"%{search}%"),
            Student.student_roll_id.like(f"%{search}%"),
            Student.phone.like(f"%{search}%"),
            SchoolStreamClass.class_code.like(f"%{search}%"),
            SchoolStreamClassSection.section_code.like(f"%{search}%"),
        ))
    else:
        stmt = stmt.where(Student.status == "active")

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await db.execute(stmt.order_by(Student.student_id.desc()).offset(offset).limit(limit))

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [_student_row_to_dict(s, m, cc, sc, sn) for s, m, cc, sc, sn in rows.all()],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Students fetched successfully.", extra=data).http_response()


@student_router.get(
    "/student/all",
    summary="Dropdown: Students",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Dropdown fetched.", "result": [{"id": 1, "name": "Arjun Kumar", "roll_id": "2026001"}]}}}}
    },
)
async def dropdown_students(
    school_id:  int        = Query(...),
    class_id:   int | None = Query(None),
    section_id: int | None = Query(None),
    search:     str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    key = f"student:dropdown:{school_id}:{class_id}:{section_id}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Dropdown fetched (cache).", extra=cached).http_response()

    stmt = (
        select(Student.student_id, Student.first_name, Student.last_name, Student.student_roll_id)
        .outerjoin(StudentClassMapping, and_(
            StudentClassMapping.student_id == Student.student_id,
            StudentClassMapping.status == "active",
            StudentClassMapping.is_active == True,
        ))
        .where(Student.school_id == school_id, Student.status == "active")
    )
    if class_id:
        stmt = stmt.where(StudentClassMapping.class_id == class_id)
    if section_id:
        stmt = stmt.where(StudentClassMapping.section_id == section_id)
    if search and search.lower() != "all":
        stmt = stmt.where(or_(
            Student.first_name.like(f"%{search}%"),
            Student.last_name.like(f"%{search}%"),
            Student.student_roll_id.like(f"%{search}%"),
        ))

    rows = await db.execute(stmt.order_by(Student.first_name))
    data = [
        {"id": r.student_id, "name": f"{r.first_name} {r.last_name or ''}".strip(), "roll_id": r.student_roll_id}
        for r in rows.all()
    ]
    if data:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Dropdown fetched.", extra=data).http_response()


@student_router.put(
    "/student/update/{student_id}",
    summary="Update student",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Student updated successfully.", "result": {"student_id": 1}}}}},
        404: _404_STU,
    },
)
async def update_student(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.student_id == student_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Student not found.", extra={}).http_response()

    student_fields = payload.model_dump(exclude_unset=True, exclude={"class_id", "section_id", "enroll_date"})
    for field, value in student_fields.items():
        if hasattr(obj, field):
            setattr(obj, field, value)

    if any([payload.class_id, payload.section_id, payload.enroll_date]):
        mapping_res = await db.execute(
            select(StudentClassMapping).where(
                StudentClassMapping.student_id == student_id,
                StudentClassMapping.status == "active",
                StudentClassMapping.is_active == True,
            )
        )
        mapping = mapping_res.scalar_one_or_none()
        if mapping:
            if payload.class_id:    mapping.class_id    = payload.class_id
            if payload.section_id:  mapping.section_id  = payload.section_id
            if payload.enroll_date: mapping.enroll_date = payload.enroll_date

    await db.commit()
    await cache.delete(f"student:{student_id}")
    await cache.delete_pattern("student:list:*")
    await cache.delete_pattern("student:dropdown:*")
    return Result(code=200, message="Student updated successfully.", extra={"student_id": student_id}).http_response()


@student_router.put(
    "/student/mapping/update/{student_id}",
    summary="Update student class/section mapping",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Mapping updated successfully.", "result": {"student_id": 1, "class_id": 2, "section_id": 3, "status": "active"}}}}},
        404: _404_MAP,
    },
)
async def update_student_mapping(student_id: int, payload: StudentMappingUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StudentClassMapping).where(
            StudentClassMapping.student_id == student_id,
            StudentClassMapping.status == "active",
            StudentClassMapping.is_active == True,
        )
    )
    mapping = result.scalar_one_or_none()
    if mapping is None:
        return Result(code=404, message="Active mapping not found for this student.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(mapping, field, value)
    await db.commit()

    await cache.delete(f"student:{student_id}")
    await cache.delete_pattern("student:list:*")
    await cache.delete_pattern("student:dropdown:*")
    return Result(code=200, message="Mapping updated successfully.", extra={
        "student_id": student_id,
        "class_id":   mapping.class_id,
        "section_id": mapping.section_id,
        "status":     mapping.status,
    }).http_response()


# ══════════════════════════════════════════════
# GUARDIAN LIST BY CLASS / SECTION
# ══════════════════════════════════════════════

@student_router.get(
    "/student/guardian/list",
    summary="Get guardian list by class/section (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Guardians fetched successfully.", "result": {"total": 1, "page": 1, "limit": 10, "data": [{"student_id": 1, "student_name": "Arjun Kumar", "guardian_first_name": "Ramesh", "guardian_last_name": "Kumar", "guardian_phone": "9876501234", "guardian_email": "ramesh@example.com", "guardian_gender": "male"}]}}}}},
    },
)
async def get_guardian_list_by_class(
    class_id:   int | None = Query(None),
    section_id: int | None = Query(None),
    search:     str | None = Query(None, description="Search by student/guardian name, phone, email, or 'all'"),
    page:       int        = Query(1,  ge=1),
    limit:      int        = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    key = f"guardian:list:{class_id}:{section_id}:{page}:{limit}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Guardians fetched successfully (cache).", extra=cached).http_response()

    conditions = [
        StudentClassMapping.status == "active",
        StudentClassMapping.is_active == True,
    ]
    if class_id:
        conditions.append(StudentClassMapping.class_id == class_id)
    if section_id:
        conditions.append(StudentClassMapping.section_id == section_id)

    if search and search.lower() != "all":
        s = search.strip()
        conditions.append(or_(
            Student.first_name.like(f"%{s}%"),
            Student.guardian_first_name.like(f"%{s}%"),
            Student.guardian_last_name.like(f"%{s}%"),
            Student.guardian_phone.like(f"%{s}%"),
            Student.guardian_email.like(f"%{s}%"),
        ))

    count_stmt = (
        select(func.count(func.distinct(Student.student_id)))
        .select_from(Student)
        .join(StudentClassMapping, StudentClassMapping.student_id == Student.student_id)
        .where(*conditions)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * limit
    stmt = (
        select(
            Student.student_id,
            Student.first_name.label("student_name"),
            Student.guardian_first_name,
            Student.guardian_last_name,
            Student.guardian_phone,
            Student.guardian_email,
            Student.guardian_gender,
        )
        .join(StudentClassMapping, StudentClassMapping.student_id == Student.student_id)
        .where(*conditions)
        .order_by(Student.student_id.desc())
        .offset(offset).limit(limit)
    )

    rows = (await db.execute(stmt)).all()
    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            {
                "student_id":          g.student_id,
                "student_name":        g.student_name,
                "guardian_first_name": g.guardian_first_name,
                "guardian_last_name":  g.guardian_last_name,
                "guardian_phone":      g.guardian_phone,
                "guardian_email":      g.guardian_email,
                "guardian_gender":     g.guardian_gender,
            }
            for g in rows
        ],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Guardians fetched successfully.", extra=data).http_response()


# ══════════════════════════════════════════════
# BULK UPLOAD STUDENTS
# ══════════════════════════════════════════════

@student_router.post(
    "/student/bulk_upload",
    summary="Bulk upload students via CSV/Excel",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Bulk student upload completed.", "result": {"created": 5, "skipped_count": 1, "skipped": ["Row 3: Roll ID 2026001 already exists"]}}}}},
        400: {"content": {"application/json": {"example": {"code": 400, "message": "Missing columns: guardian_phone.", "result": {}}}}},
    },
)
async def bulk_upload_students(
    school_id: int = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        return Result(code=400, message="File name is missing.", extra={}).http_response()
    if not (file.filename.endswith(".csv") or file.filename.endswith(".xlsx")):
        return Result(code=400, message="Only CSV or Excel files allowed.", extra={}).http_response()

    contents = await file.read()
    file_obj = BytesIO(contents)

    try:
        df = pd.read_csv(file_obj) if file.filename.endswith(".csv") else pd.read_excel(file_obj)
    except Exception as e:
        return Result(code=400, message=f"File parsing error: {str(e)}", extra={}).http_response()

    required_columns = ["student_roll_id", "first_name", "guardian_phone", "gender", "age", "class_id", "section_id", "enroll_date"]
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        return Result(code=400, message=f"Missing columns: {', '.join(missing_cols)}", extra={}).http_response()

    df = df.fillna("")
    created_count = 0
    skipped_rows  = []

    roll_ids = [str(r).strip() for r in df["student_roll_id"].tolist() if r]
    existing_result = await db.execute(select(Student.student_roll_id).where(Student.student_roll_id.in_(roll_ids)))
    existing_roll_ids = {r for r in existing_result.scalars().all()}

    for index, row in df.iterrows():
        try:
            if not row["student_roll_id"]:
                raise ValueError("student_roll_id is required")
            if not row["class_id"] or not row["section_id"]:
                raise ValueError("class_id and section_id are required")
            if not row["guardian_phone"]:
                raise ValueError("guardian_phone is required")

            roll_id = str(row["student_roll_id"]).strip()
            if roll_id in existing_roll_ids:
                raise ValueError(f"Roll ID {roll_id} already exists")

            enroll_date = pd.to_datetime(row["enroll_date"], errors="coerce")
            if pd.isna(enroll_date):
                raise ValueError("Invalid enroll_date format")

            student = Student(
                school_id=school_id,
                student_roll_id=roll_id,
                first_name=str(row["first_name"]).strip(),
                last_name=str(row.get("last_name", "")).strip() or None,
                gender=str(row["gender"]).lower() if row["gender"] else None,
                age=int(row["age"]) if row["age"] else None,
                guardian_phone=str(row["guardian_phone"]).strip(),
            )
            db.add(student)
            await db.flush()

            mapping = StudentClassMapping(
                student_id=student.student_id,
                class_id=int(row["class_id"]),
                section_id=int(row["section_id"]),
                enroll_date=enroll_date.date(),
                valid_from_date=date.today(),
                status="active",
                is_active=True,
            )
            db.add(mapping)
            created_count += 1
            existing_roll_ids.add(roll_id)

        except Exception as row_error:
            skipped_rows.append(f"Row {index + 2}: {str(row_error)}")
            continue

    await db.commit()
    await cache.delete_pattern("student:list:*")

    return Result(code=200, message="Bulk student upload completed.", extra={
        "created":       created_count,
        "skipped_count": len(skipped_rows),
        "skipped":       skipped_rows[:10],
    }).http_response()


# ══════════════════════════════════════════════
# TRANSFER STUDENT
# ══════════════════════════════════════════════

@student_router.post(
    "/student/transfer",
    summary="Transfer student to a different section",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Student transferred successfully.", "result": {"student_id": 1, "class_id": 1, "old_section": 3, "new_section": 4}}}}},
        404: _404_STU,
    },
)
async def transfer_student(
    student_id: int = Query(...),
    section_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    student_result = await db.execute(select(Student).where(Student.student_id == student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        return Result(code=404, message="Student not found.", extra={}).http_response()

    mapping_result = await db.execute(
        select(StudentClassMapping).where(
            StudentClassMapping.student_id == student.student_id,
            StudentClassMapping.is_active == True,
        )
    )
    mapping = mapping_result.scalar_one_or_none()
    if not mapping:
        return Result(code=404, message="Active mapping not found.", extra={}).http_response()

    old_section = mapping.section_id
    class_id    = mapping.class_id

    mapping.is_active = False
    mapping.status    = "inactive"

    db.add(StudentClassMapping(
        student_id=student.student_id,
        class_id=class_id,
        section_id=section_id,
        valid_from_date=date.today(),
        enroll_date=mapping.enroll_date,
        is_active=True,
        status="active",
    ))
    await db.commit()

    await cache.delete(f"student:{student_id}")
    await cache.delete_pattern("student:list:*")

    return Result(code=200, message="Student transferred successfully.", extra={
        "student_id":  student.student_id,
        "class_id":    class_id,
        "old_section": old_section,
        "new_section": section_id,
    }).http_response()


# ══════════════════════════════════════════════
# PROMOTE STUDENTS
# ══════════════════════════════════════════════

@student_router.post(
    "/student/promote",
    summary="Promote all students from one class to the next",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Students promoted successfully.", "result": {"from_class_id": 1, "to_class_id": 2, "total_promoted": 25, "skipped_students": []}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "No active students found in this class.", "result": {}}}}},
        400: {"content": {"application/json": {"example": {"code": 400, "message": "Invalid class_code format — must be numeric.", "result": {}}}}},
    },
)
async def promote_students(
    from_class_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    class_row = (await db.execute(
        select(SchoolStreamClass.class_code, SchoolStreamClass.school_id)
        .where(SchoolStreamClass.class_id == from_class_id, SchoolStreamClass.status == "active")
    )).first()

    if not class_row:
        return Result(code=404, message="Invalid from_class_id.", extra={}).http_response()

    current_class_code, school_id = class_row

    try:
        next_class_code = str(int(current_class_code) + 1)
    except ValueError:
        return Result(code=400, message="Invalid class_code format — must be numeric.", extra={}).http_response()

    to_class_id = (await db.execute(
        select(SchoolStreamClass.class_id).where(
            SchoolStreamClass.class_code == next_class_code,
            SchoolStreamClass.school_id  == school_id,
            SchoolStreamClass.status     == "active",
        )
    )).scalar_one_or_none()

    if not to_class_id:
        return Result(code=404, message=f"Next class (code={next_class_code}) not found.", extra={}).http_response()

    rows = (await db.execute(
        select(StudentClassMapping, SchoolStreamClassSection.section_code)
        .join(SchoolStreamClassSection, SchoolStreamClassSection.section_id == StudentClassMapping.section_id)
        .where(StudentClassMapping.class_id == from_class_id, StudentClassMapping.is_active == True)
    )).all()

    if not rows:
        return Result(code=404, message="No active students found in this class.", extra={}).http_response()

    section_map = {
        r.section_code: r.section_id
        for r in (await db.execute(
            select(SchoolStreamClassSection.section_id, SchoolStreamClassSection.section_code)
            .where(SchoolStreamClassSection.class_id == to_class_id)
        )).all()
    }

    new_records      = []
    skipped_students = []

    for mapping, section_code in rows:
        new_section_id = section_map.get(section_code)
        if not new_section_id:
            skipped_students.append(mapping.student_id)
            continue

        mapping.is_active     = False
        mapping.status        = "inactive"
        mapping.valid_to_date = date.today()

        new_records.append(StudentClassMapping(
            student_id=mapping.student_id,
            class_id=to_class_id,
            section_id=new_section_id,
            valid_from_date=date.today(),
            is_active=True,
            status="active",
        ))

    db.add_all(new_records)
    await db.commit()
    await cache.delete_pattern("student:list:*")

    return Result(code=200, message="Students promoted successfully.", extra={
        "from_class_id":    from_class_id,
        "to_class_id":      to_class_id,
        "total_promoted":   len(new_records),
        "skipped_students": skipped_students,
    }).http_response()
