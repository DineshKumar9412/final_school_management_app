# api/student.py
from fastapi import APIRouter, Depends, Query
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

student_router = APIRouter(tags=["STUDENT"])

CACHE_TTL = 86400
STATUS_VALUES = {"active", "inactive"}


# ══════════════════════════════════════════════
# STUDENT ADMISSION INQUIRY
# ══════════════════════════════════════════════

# ─── CREATE INQUIRY ───────────────────────────

@student_router.post("/inquiry/create", summary="Create student admission inquiry")
async def create_inquiry(payload: StudentInquiryCreate, db: AsyncSession = Depends(get_db)):
    # duplicate check by guardian_phone
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


# ─── GET ALL INQUIRIES ────────────────────────

@student_router.get("/inquiry/list", summary="List student admission inquiries (paginated)")
async def list_inquiries(
    page:     int          = Query(1,    ge=1),
    limit:    int          = Query(10,   ge=1, le=100),
    search:   str | None   = Query(None, description="Search by student_name, guardian_name, guardian_phone, or type 'active'/'inactive'"),
    class_id: int | None   = Query(None),
    db: AsyncSession = Depends(get_db),
):
    key = f"inquiry:list:{page}:{limit}:{search}:{class_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Inquiries fetched successfully.", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt = select(StudentAdmissionInquiry)

    if class_id is not None:
        stmt = stmt.where(StudentAdmissionInquiry.class_id == class_id)

    if search is not None:
        stmt = stmt.where(
            or_(
                StudentAdmissionInquiry.student_name.like(f"%{search}%"),
                StudentAdmissionInquiry.guardian_name.like(f"%{search}%"),
                StudentAdmissionInquiry.guardian_phone.like(f"%{search}%"),
            )
        )

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
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Inquiries fetched successfully.", extra=data).http_response()


# ─── GET INQUIRY BY ID ────────────────────────

@student_router.get("/inquiry/get_id/{inq_id}", summary="Get inquiry by ID")
async def get_inquiry(inq_id: int, db: AsyncSession = Depends(get_db)):
    key = f"inquiry:{inq_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Inquiry fetched successfully.", extra=cached).http_response()

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


# ─── UPDATE INQUIRY ───────────────────────────

@student_router.put("/inquiry/update/{inq_id}", summary="Update student inquiry")
async def update_inquiry(inq_id: int, payload: StudentInquiryUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StudentAdmissionInquiry).where(StudentAdmissionInquiry.student_inq_id == inq_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Inquiry not found.", extra={}).http_response()

    # duplicate phone check (exclude self)
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


# ─── DELETE INQUIRY ───────────────────────────

@student_router.delete("/inquiry/delete/{inq_id}", summary="Delete student inquiry")
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
    """SELECT student with active class+section mapping via LEFT JOIN."""
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
        .outerjoin(SchoolStreamClass,  StudentClassMapping.class_id    == SchoolStreamClass.class_id)
        .outerjoin(SchoolStreamClassSection, StudentClassMapping.section_id == SchoolStreamClassSection.section_id)
    )


def _student_row_to_dict(s, m, class_code, section_code, section_name) -> dict:
    return {
        "student_id":        s.student_id,
        "school_id":         s.school_id,
        "student_roll_id":   s.student_roll_id,
        "first_name":        s.first_name,
        "last_name":         s.last_name,
        "gender":            s.gender,
        "dob":               str(s.dob) if s.dob else None,
        "age":               s.age,
        "email":             s.email,
        "phone":             s.phone,
        "blood_group":       s.blood_group,
        "status":            s.status,
        "class_code":        class_code,
        "section_code":      section_code,
        "section_name":      section_name,
        "enroll_date":       str(m.enroll_date) if m and m.enroll_date else None,
        "mapping_status":    m.status if m else None,
    }


# ─── CREATE STUDENT ───────────────────────────

@student_router.post("/student/create", summary="Create a new student")
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    # duplicate check by student_roll_id
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


# ─── GET STUDENT BY ID ────────────────────────

@student_router.get("/student/get_id/{student_id}", summary="Get student by ID")
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    key = f"student:{student_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Student fetched successfully.", extra=cached).http_response()

    row = (await db.execute(
        _student_joined_stmt().where(Student.student_id == student_id)
    )).one_or_none()

    if row is None:
        return Result(code=404, message="Student not found.", extra={}).http_response()

    s, m, class_code, section_code, section_name = row
    data = _student_row_to_dict(s, m, class_code, section_code, section_name)
    # include full details for single fetch
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


# ─── GET STUDENT LIST (paginated) ─────────────

@student_router.get("/student/list", summary="List students (paginated)")
async def list_students(
    school_id: int          = Query(...),
    class_id:  int | None   = Query(None),
    page:      int          = Query(1,    ge=1),
    limit:     int          = Query(10,   ge=1, le=100),
    search:    str | None   = Query(None, description="Search by name, roll ID, phone, class_code, section_code, or type 'active'/'inactive'"),
    db: AsyncSession = Depends(get_db),
):
    key = f"student:list:{school_id}:{class_id}:{page}:{limit}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Students fetched successfully.", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt = _student_joined_stmt().where(Student.school_id == school_id)

    if class_id is not None:
        stmt = stmt.where(StudentClassMapping.class_id == class_id)

    if search is not None and search.lower() in STATUS_VALUES:
        stmt = stmt.where(Student.status == search.lower())
    elif search is not None:
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
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Students fetched successfully.", extra=data).http_response()


# ─── GET STUDENT DROPDOWN ─────────────────────

@student_router.get("/student/all", summary="Dropdown: Students")
async def dropdown_students(
    school_id: int        = Query(...),
    class_id:  int | None = Query(None),
    search:    str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    key = f"student:dropdown:{school_id}:{class_id}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Dropdown fetched.", extra=cached).http_response()

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
    if search:
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
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Dropdown fetched.", extra=data).http_response()


# ─── UPDATE STUDENT ───────────────────────────

@student_router.put("/student/update/{student_id}", summary="Update student")
async def update_student(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.student_id == student_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Student not found.", extra={}).http_response()

    student_fields = payload.model_dump(exclude_unset=True, exclude={"class_id", "section_id", "enroll_date"})
    for field, value in student_fields.items():
        if hasattr(obj, field):
            setattr(obj, field, value)

    # update mapping if class/section/enroll_date provided
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
            if payload.class_id:   mapping.class_id   = payload.class_id
            if payload.section_id: mapping.section_id = payload.section_id
            if payload.enroll_date: mapping.enroll_date = payload.enroll_date

    await db.commit()

    await cache.delete(f"student:{student_id}")
    await cache.delete_pattern("student:list:*")
    await cache.delete_pattern("student:dropdown:*")
    return Result(code=200, message="Student updated successfully.", extra={"student_id": student_id}).http_response()


# ─── UPDATE STUDENT MAPPING ───────────────────

@student_router.put("/student/mapping/update/{student_id}", summary="Update student class/section mapping")
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
