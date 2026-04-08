# api/exam.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, tuple_, or_
from typing import Optional, List

from database.session import get_db
from database.redis_cache import cache
from models.exam_models import Grade, Exam, ExamTimetable, StudentMarks, OnlineExam, OnlineClass
from models.school_stream_models import SchoolStream
from schemas.exam_schemas import (
    GradeCreate,
    ExamCreate, ExamUpdate,
    ExamTimetableCreate, ExamTimetableUpdate,
    StudentMarksCreate,
    OnlineExamCreate, OnlineExamUpdate,
    OnlineClassCreate, OnlineClassUpdate,
)
from security.valid_session import valid_session
from response.result import Result

exam_router = APIRouter(
    tags=["EXAM"],
    dependencies=[Depends(valid_session)],
)

CACHE_TTL = 86400


# ══════════════════════════════════════════════
# GRADE
# ══════════════════════════════════════════════

@exam_router.post(
    "/grade/create",
    summary="Create a grade",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Grade created successfully.", "result": {"grade_id": 1, "start_range": 90.0, "end_range": 100.0, "grade": "A+", "is_active": True}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Grade range already exists.", "result": {}}}}},
    },
)
async def create_grade(payload: GradeCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(Grade.grade_id).where(
            Grade.start_range == payload.start_range,
            Grade.end_range   == payload.end_range,
        )
    )
    if exists.scalar_one_or_none():
        return Result(code=409, message="Grade range already exists.", extra={}).http_response()

    grade = Grade(**payload.model_dump())
    db.add(grade)
    await db.commit()
    await db.refresh(grade)

    await cache.delete_pattern("grade:list:*")
    return Result(code=201, message="Grade created successfully.", extra={
        "grade_id":    grade.grade_id,
        "start_range": float(grade.start_range),
        "end_range":   float(grade.end_range),
        "grade":       grade.grade,
        "is_active":   grade.is_active,
    }).http_response()


@exam_router.post(
    "/grade/bulk_create",
    summary="Bulk create grades",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "All grades created successfully.", "result": {"created": 3}}}}},
        400: {"content": {"application/json": {"example": {"code": 400, "message": "Invalid range: 100.0-90.0.", "result": {}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Duplicate range in request.", "result": {}}}}},
    },
)
async def create_grades_bulk(payload: List[GradeCreate], db: AsyncSession = Depends(get_db)):
    seen = set()
    for item in payload:
        if item.start_range >= item.end_range:
            return Result(code=400, message=f"Invalid range: {item.start_range}-{item.end_range}. Start must be less than end.", extra={}).http_response()
        key = (item.start_range, item.end_range)
        if key in seen:
            return Result(code=409, message=f"Duplicate range in request: {key}.", extra={}).http_response()
        seen.add(key)

    ranges = [(i.start_range, i.end_range) for i in payload]
    existing = (await db.execute(
        select(Grade.start_range, Grade.end_range).where(
            tuple_(Grade.start_range, Grade.end_range).in_(ranges)
        )
    )).all()
    if existing:
        return Result(code=409, message=f"These ranges already exist: {existing}.", extra={}).http_response()

    grades = [Grade(start_range=i.start_range, end_range=i.end_range, grade=i.grade) for i in payload]
    db.add_all(grades)
    await db.commit()

    await cache.delete_pattern("grade:list:*")
    return Result(code=201, message="All grades created successfully.", extra={"created": len(grades)}).http_response()


@exam_router.get(
    "/grade/list",
    summary="List all grades (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Grades fetched successfully.", "result": {"total": 1, "page": 1, "limit": 10, "data": [{"grade_id": 1, "start_range": 90.0, "end_range": 100.0, "grade": "A+", "is_active": True}]}}}}},
    },
)
async def list_grades(
    is_active: Optional[bool] = Query(None),
    search:    Optional[str]  = Query(None, description="Search by grade (e.g. A+)"),
    page:      int            = Query(1,    ge=1),
    limit:     int            = Query(10,   ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    key = f"grade:list:{is_active}:{search}:{page}:{limit}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Grades fetched successfully (cache).", extra=cached).http_response()

    stmt = select(Grade)
    if is_active is not None:
        stmt = stmt.where(Grade.is_active == is_active)
    if search:
        stmt = stmt.where(Grade.grade.like(f"%{search}%"))

    total  = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    offset = (page - 1) * limit
    rows   = (await db.execute(stmt.order_by(Grade.start_range).offset(offset).limit(limit))).scalars().all()

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            {"grade_id": g.grade_id, "start_range": float(g.start_range),
             "end_range": float(g.end_range), "grade": g.grade, "is_active": g.is_active}
            for g in rows
        ],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Grades fetched successfully.", extra=data).http_response()


@exam_router.get(
    "/grade/get_id/{grade_id}",
    summary="Get grade by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Grade fetched successfully.", "result": {"grade_id": 1, "start_range": 90.0, "end_range": 100.0, "grade": "A+", "is_active": True}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Grade not found.", "result": {}}}}},
    },
)
async def get_grade(grade_id: int, db: AsyncSession = Depends(get_db)):
    key = f"grade:{grade_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Grade fetched successfully (cache).", extra=cached).http_response()

    result = await db.execute(select(Grade).where(Grade.grade_id == grade_id))
    grade = result.scalar_one_or_none()
    if not grade:
        return Result(code=404, message="Grade not found.", extra={}).http_response()

    data = {
        "grade_id":    grade.grade_id,
        "start_range": float(grade.start_range),
        "end_range":   float(grade.end_range),
        "grade":       grade.grade,
        "is_active":   grade.is_active,
    }
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Grade fetched successfully.", extra=data).http_response()


@exam_router.delete(
    "/grade/delete/{grade_id}",
    summary="Delete a grade",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Grade deleted successfully.", "result": {"grade_id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Grade not found.", "result": {}}}}},
    },
)
async def delete_grade(grade_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Grade).where(Grade.grade_id == grade_id))
    grade = result.scalar_one_or_none()
    if not grade:
        return Result(code=404, message="Grade not found.", extra={}).http_response()

    await db.delete(grade)
    await db.commit()
    await cache.delete_pattern("grade:list:*")
    return Result(code=200, message="Grade deleted successfully.", extra={"grade_id": grade_id}).http_response()


# ══════════════════════════════════════════════
# EXAM
# ══════════════════════════════════════════════

@exam_router.post(
    "/exam/create",
    summary="Create an exam",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Exam created successfully.", "result": {"exam_id": 1, "exam_name": "Mid Term 2024", "school_stream_id": 1, "session_yr": "2024-25", "is_active": True}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Exam with this name already exists.", "result": {}}}}},
    },
)
async def create_exam(payload: ExamCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(Exam.exam_id).where(Exam.exam_name == payload.exam_name))
    if exists.scalar_one_or_none():
        return Result(code=409, message="Exam with this name already exists.", extra={}).http_response()

    exam = Exam(**payload.model_dump())
    db.add(exam)
    await db.commit()
    await db.refresh(exam)

    await cache.delete_pattern("exam:list:*")
    return Result(code=201, message="Exam created successfully.", extra={
        "exam_id":          exam.exam_id,
        "exam_name":        exam.exam_name,
        "school_stream_id": exam.school_stream_id,
        "session_yr":       exam.session_yr,
        "exam_description": exam.exam_description,
        "is_active":        exam.is_active,
    }).http_response()


@exam_router.get(
    "/exam/list",
    summary="List exams",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Exams fetched successfully.", "result": {"total": 1, "page": 1, "limit": 10, "data": [{"exam_id": 1, "exam_name": "Mid Term 2024", "school_stream_id": 1, "session_yr": "2024-25", "is_active": True}]}}}}},
    },
)
async def list_exams(
    school_id: Optional[int] = Query(None),
    search:    Optional[str] = Query(None, description="Search by exam_name, session_yr, or 'active'/'inactive'"),
    page:      int           = Query(1,  ge=1),
    limit:     int           = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    key = f"exam:list:{school_id}:{search}:{page}:{limit}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Exams fetched successfully (cache).", extra=cached).http_response()

    stmt = select(Exam)
    if school_id is not None:
        stmt = stmt.where(Exam.school_stream_id == school_id)
    if search is not None and search.lower() in {"active", "inactive"}:
        stmt = stmt.where(Exam.is_active == (search.lower() == "active"))
    elif search:
        stmt = stmt.where(or_(
            Exam.exam_name.like(f"%{search}%"),
            Exam.session_yr.like(f"%{search}%"),
        ))
    else:
        stmt = stmt.where(Exam.is_active == True)

    total  = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    offset = (page - 1) * limit
    rows   = (await db.execute(stmt.order_by(Exam.exam_id).offset(offset).limit(limit))).scalars().all()

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            {"exam_id": e.exam_id, "exam_name": e.exam_name, "school_stream_id": e.school_stream_id,
             "session_yr": e.session_yr, "exam_description": e.exam_description, "is_active": e.is_active}
            for e in rows
        ],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Exams fetched successfully.", extra=data).http_response()


@exam_router.get(
    "/exam/get_id/{exam_id}",
    summary="Get exam by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Exam fetched successfully.", "result": {"exam_id": 1, "exam_name": "Mid Term 2024"}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Exam not found.", "result": {}}}}},
    },
)
async def get_exam(exam_id: int, db: AsyncSession = Depends(get_db)):
    key = f"exam:{exam_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Exam fetched successfully (cache).", extra=cached).http_response()

    result = await db.execute(select(Exam).where(Exam.exam_id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        return Result(code=404, message="Exam not found.", extra={}).http_response()

    data = {"exam_id": exam.exam_id, "exam_name": exam.exam_name, "school_stream_id": exam.school_stream_id,
            "session_yr": exam.session_yr, "exam_description": exam.exam_description, "is_active": exam.is_active}
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Exam fetched successfully.", extra=data).http_response()


@exam_router.put(
    "/exam/update/{exam_id}",
    summary="Update an exam",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Exam updated successfully.", "result": {"exam_id": 1, "exam_name": "Final Term 2024"}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Exam not found.", "result": {}}}}},
    },
)
async def update_exam(exam_id: int, payload: ExamUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Exam).where(Exam.exam_id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        return Result(code=404, message="Exam not found.", extra={}).http_response()

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return Result(code=400, message="No fields provided for update.", extra={}).http_response()

    if "school_stream_id" in update_data:
        stream = (await db.execute(
            select(SchoolStream.school_stream_id).where(SchoolStream.school_stream_id == update_data["school_stream_id"])
        )).scalar_one_or_none()
        if not stream:
            return Result(code=404, message="school_stream_id not found.", extra={}).http_response()

    for field, value in update_data.items():
        setattr(exam, field, value)
    await db.commit()
    await db.refresh(exam)

    data = {"exam_id": exam.exam_id, "exam_name": exam.exam_name, "school_stream_id": exam.school_stream_id,
            "session_yr": exam.session_yr, "exam_description": exam.exam_description, "is_active": exam.is_active}
    await cache.set(f"exam:{exam_id}", data, expire=CACHE_TTL)
    await cache.delete_pattern("exam:list:*")
    return Result(code=200, message="Exam updated successfully.", extra=data).http_response()


@exam_router.delete(
    "/exam/delete/{exam_id}",
    summary="Delete an exam",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Exam deleted successfully.", "result": {"exam_id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Exam not found.", "result": {}}}}},
    },
)
async def delete_exam(exam_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Exam).where(Exam.exam_id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        return Result(code=404, message="Exam not found.", extra={}).http_response()

    await db.delete(exam)
    await db.commit()
    await cache.delete(f"exam:{exam_id}")
    await cache.delete_pattern("exam:list:*")
    return Result(code=200, message="Exam deleted successfully.", extra={"exam_id": exam_id}).http_response()


# ══════════════════════════════════════════════
# EXAM TIMETABLE
# ══════════════════════════════════════════════

@exam_router.post(
    "/exam/timetable/create",
    summary="Create exam timetable",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Exam timetable created successfully.", "result": {"timetable_id": 1}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Timetable already exists for this exam.", "result": {}}}}},
    },
)
async def create_exam_timetable(payload: ExamTimetableCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(ExamTimetable.timetable_id).where(ExamTimetable.exam_id == payload.exam_id)
    )
    if exists.scalar_one_or_none():
        return Result(code=409, message="Timetable already exists for this exam.", extra={}).http_response()

    timetable = ExamTimetable(**payload.model_dump())
    db.add(timetable)
    await db.commit()
    await db.refresh(timetable)

    await cache.delete_pattern("timetable:list:*")
    return Result(code=201, message="Exam timetable created successfully.", extra={"timetable_id": timetable.timetable_id}).http_response()


@exam_router.get(
    "/exam/timetable/list",
    summary="List exam timetables",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Timetables fetched successfully.", "result": {"total": 1, "page": 1, "limit": 10, "data": [{"timetable_id": 1, "exam_id": 1, "subject_id": 1, "total_marks": 100.0, "pass_mark": 35.0}]}}}}},
    },
)
async def list_exam_timetables(
    school_id: Optional[int] = Query(None),
    exam_id:   Optional[int] = Query(None),
    search:    Optional[str] = Query(None, description="Search by exam_name, or 'active'/'inactive'"),
    page:      int           = Query(1,  ge=1),
    limit:     int           = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    key = f"timetable:list:{school_id}:{exam_id}:{search}:{page}:{limit}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Timetables fetched successfully (cache).", extra=cached).http_response()

    stmt = select(ExamTimetable).join(Exam, ExamTimetable.exam_id == Exam.exam_id)
    if school_id:
        stmt = stmt.where(ExamTimetable.school_stream_id == school_id)
    if exam_id:
        stmt = stmt.where(ExamTimetable.exam_id == exam_id)
    if search is not None and search.lower() in {"active", "inactive"}:
        stmt = stmt.where(ExamTimetable.is_active == (search.lower() == "active"))
    elif search:
        stmt = stmt.where(Exam.exam_name.like(f"%{search}%"))
    else:
        stmt = stmt.where(ExamTimetable.is_active == True)

    total  = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    offset = (page - 1) * limit
    rows   = (await db.execute(stmt.order_by(ExamTimetable.timetable_id).offset(offset).limit(limit))).scalars().all()

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            {
                "timetable_id":     t.timetable_id,
                "exam_id":          t.exam_id,
                "school_stream_id": t.school_stream_id,
                "school_group_id":  t.school_group_id,
                "subject_id":       t.subject_id,
                "total_marks":      float(t.total_marks) if t.total_marks else None,
                "pass_mark":        float(t.pass_mark) if t.pass_mark else None,
                "exam_start_date":  str(t.exam_start_date) if t.exam_start_date else None,
                "exam_end_date":    str(t.exam_end_date) if t.exam_end_date else None,
                "start_time":       str(t.start_time),
                "start_ampm":       t.start_ampm,
                "end_time":         str(t.end_time),
                "end_ampm":         t.end_ampm,
                "is_active":        t.is_active,
            }
            for t in rows
        ],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Timetables fetched successfully.", extra=data).http_response()


@exam_router.put(
    "/exam/timetable/update/{timetable_id}",
    summary="Update exam timetable",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Timetable updated successfully.", "result": {"timetable_id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Timetable not found.", "result": {}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Another timetable already exists for this exam.", "result": {}}}}},
    },
)
async def update_exam_timetable(timetable_id: int, payload: ExamTimetableUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ExamTimetable).where(ExamTimetable.timetable_id == timetable_id))
    timetable = result.scalar_one_or_none()
    if not timetable:
        return Result(code=404, message="Timetable not found.", extra={}).http_response()

    if payload.exam_id:
        dup = (await db.execute(
            select(ExamTimetable.timetable_id).where(
                ExamTimetable.exam_id == payload.exam_id,
                ExamTimetable.timetable_id != timetable_id,
            )
        )).scalar_one_or_none()
        if dup:
            return Result(code=409, message="Another timetable already exists for this exam.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(timetable, field, value)
    await db.commit()

    await cache.delete_pattern("timetable:list:*")
    return Result(code=200, message="Timetable updated successfully.", extra={"timetable_id": timetable.timetable_id}).http_response()


@exam_router.delete(
    "/exam/timetable/delete/{timetable_id}",
    summary="Delete exam timetable",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Timetable deleted successfully.", "result": {"timetable_id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Timetable not found.", "result": {}}}}},
    },
)
async def delete_exam_timetable(timetable_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ExamTimetable).where(ExamTimetable.timetable_id == timetable_id))
    timetable = result.scalar_one_or_none()
    if not timetable:
        return Result(code=404, message="Timetable not found.", extra={}).http_response()

    await db.delete(timetable)
    await db.commit()
    await cache.delete_pattern("timetable:list:*")
    return Result(code=200, message="Timetable deleted successfully.", extra={"timetable_id": timetable_id}).http_response()


# ══════════════════════════════════════════════
# STUDENT MARKS
# ══════════════════════════════════════════════

@exam_router.post(
    "/marks/create",
    summary="Create student marks (bulk per student)",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Marks created successfully.", "result": {"subjects_inserted": 2}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Marks already exist for subjects: [1, 2].", "result": {}}}}},
    },
)
async def create_marks(payload: StudentMarksCreate, db: AsyncSession = Depends(get_db)):
    subject_ids = [s.subject_id for s in payload.subjects]

    existing = set((await db.execute(
        select(StudentMarks.subject_id).where(
            StudentMarks.student_id == payload.student_id,
            StudentMarks.subject_id.in_(subject_ids),
        )
    )).scalars().all())

    if existing:
        return Result(code=409, message=f"Marks already exist for subjects: {list(existing)}.", extra={}).http_response()

    marks = [
        StudentMarks(
            student_id=payload.student_id,
            class_id=payload.class_id,
            subject_id=s.subject_id,
            mark=s.mark,
        )
        for s in payload.subjects
    ]
    db.add_all(marks)
    await db.commit()

    await cache.delete_pattern(f"marks:student:{payload.student_id}:*")
    return Result(code=201, message="Marks created successfully.", extra={"subjects_inserted": len(marks)}).http_response()


@exam_router.get(
    "/marks/list",
    summary="Get student marks",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Marks fetched successfully.", "result": {"total": 2, "page": 1, "limit": 10, "data": [{"id": 1, "student_id": 1, "subject_id": 1, "mark": 85.0}]}}}}},
    },
)
async def list_marks(
    student_id: int           = Query(...),
    class_id:   Optional[int] = Query(None),
    subject_id: Optional[int] = Query(None),
    search:     Optional[str] = Query(None, description="Search by subject_id (numeric)"),
    page:       int           = Query(1,    ge=1),
    limit:      int           = Query(10,   ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    key = f"marks:student:{student_id}:{class_id}:{subject_id}:{search}:{page}:{limit}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Marks fetched successfully (cache).", extra=cached).http_response()

    stmt = select(StudentMarks).where(StudentMarks.student_id == student_id)
    if class_id:   stmt = stmt.where(StudentMarks.class_id   == class_id)
    if subject_id: stmt = stmt.where(StudentMarks.subject_id == subject_id)
    if search and search.isdigit():
        stmt = stmt.where(StudentMarks.subject_id == int(search))

    total  = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    offset = (page - 1) * limit
    rows   = (await db.execute(stmt.order_by(StudentMarks.subject_id).offset(offset).limit(limit))).scalars().all()

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            {"id": m.id, "student_id": m.student_id, "class_id": m.class_id,
             "subject_id": m.subject_id, "mark": float(m.mark) if m.mark is not None else None}
            for m in rows
        ],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Marks fetched successfully.", extra=data).http_response()


# ══════════════════════════════════════════════
# ONLINE EXAM
# ══════════════════════════════════════════════

@exam_router.post(
    "/online_exam/create",
    summary="Create online exam",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Online exam created successfully.", "result": {"id": 1, "exam_code": "MATH001", "class_id": 1, "subject_id": 1}}}}},
        400: {"content": {"application/json": {"example": {"code": 400, "message": "End date must be >= start date.", "result": {}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Online exam already exists for this exam_code.", "result": {}}}}},
    },
)
async def create_online_exam(payload: OnlineExamCreate, db: AsyncSession = Depends(get_db)):
    if payload.end_date < payload.start_date:
        return Result(code=400, message="End date must be >= start date.", extra={}).http_response()

    if payload.exam_code:
        exists = (await db.execute(
            select(OnlineExam.id).where(OnlineExam.exam_code == payload.exam_code)
        )).scalar_one_or_none()
        if exists:
            return Result(code=409, message=f"Online exam already exists for exam_code: {payload.exam_code}.", extra={}).http_response()

    exam = OnlineExam(**payload.model_dump())
    db.add(exam)
    await db.commit()
    await db.refresh(exam)

    await cache.delete_pattern("online_exam:list:*")
    return Result(code=201, message="Online exam created successfully.", extra={
        "id": exam.id, "title": exam.title, "class_id": exam.class_id,
        "subject_id": exam.subject_id, "exam_code": exam.exam_code,
        "url": exam.url, "duration": exam.duration,
        "start_date": str(exam.start_date), "end_date": str(exam.end_date),
    }).http_response()


@exam_router.get(
    "/online_exam/list",
    summary="List online exams",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Online exams fetched successfully.", "result": {"total": 1, "page": 1, "limit": 10, "data": [{"id": 1, "exam_code": "MATH001", "class_id": 1, "subject_id": 1}]}}}}},
    },
)
async def list_online_exams(
    class_id:   Optional[int] = Query(None),
    subject_id: Optional[int] = Query(None),
    search:     Optional[str] = Query(None, description="Search by title or exam_code"),
    page:       int           = Query(1,    ge=1),
    limit:      int           = Query(10,   ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    key = f"online_exam:list:{class_id}:{subject_id}:{search}:{page}:{limit}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Online exams fetched successfully (cache).", extra=cached).http_response()

    stmt = select(OnlineExam)
    if class_id:   stmt = stmt.where(OnlineExam.class_id   == class_id)
    if subject_id: stmt = stmt.where(OnlineExam.subject_id == subject_id)
    if search:
        stmt = stmt.where(or_(
            OnlineExam.title.like(f"%{search}%"),
            OnlineExam.exam_code.like(f"%{search}%"),
        ))

    total  = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    offset = (page - 1) * limit
    rows   = (await db.execute(stmt.order_by(OnlineExam.id).offset(offset).limit(limit))).scalars().all()

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            {"id": e.id, "title": e.title, "class_id": e.class_id, "subject_id": e.subject_id,
             "exam_code": e.exam_code, "url": e.url, "duration": e.duration,
             "start_date": str(e.start_date), "end_date": str(e.end_date)}
            for e in rows
        ],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Online exams fetched successfully.", extra=data).http_response()


@exam_router.put(
    "/online_exam/update/{exam_id}",
    summary="Update online exam",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Online exam updated successfully.", "result": {"id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Online exam not found.", "result": {}}}}},
    },
)
async def update_online_exam(exam_id: int, payload: OnlineExamUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OnlineExam).where(OnlineExam.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        return Result(code=404, message="Online exam not found.", extra={}).http_response()

    update_data = payload.model_dump(exclude_unset=True)
    start = update_data.get("start_date", exam.start_date)
    end   = update_data.get("end_date",   exam.end_date)
    if end < start:
        return Result(code=400, message="End date must be >= start date.", extra={}).http_response()

    for field, value in update_data.items():
        setattr(exam, field, value)
    await db.commit()
    await db.refresh(exam)

    await cache.delete_pattern("online_exam:list:*")
    return Result(code=200, message="Online exam updated successfully.", extra={
        "id": exam.id, "title": exam.title, "class_id": exam.class_id,
        "subject_id": exam.subject_id, "exam_code": exam.exam_code,
        "url": exam.url, "duration": exam.duration,
        "start_date": str(exam.start_date), "end_date": str(exam.end_date),
    }).http_response()


@exam_router.delete(
    "/online_exam/delete/{exam_id}",
    summary="Delete online exam",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Online exam deleted successfully.", "result": {"id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Online exam not found.", "result": {}}}}},
    },
)
async def delete_online_exam(exam_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OnlineExam).where(OnlineExam.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        return Result(code=404, message="Online exam not found.", extra={}).http_response()

    await db.delete(exam)
    await db.commit()
    await cache.delete_pattern("online_exam:list:*")
    return Result(code=200, message="Online exam deleted successfully.", extra={"id": exam_id}).http_response()


# ══════════════════════════════════════════════
# ONLINE CLASS
# ══════════════════════════════════════════════

@exam_router.post(
    "/online_class/create",
    summary="Create online class",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Online class created successfully.", "result": {"id": 1, "class_id": 1, "subject_id": 1}}}}},
        400: {"content": {"application/json": {"example": {"code": 400, "message": "End date must be >= start date.", "result": {}}}}},
    },
)
async def create_online_class(payload: OnlineClassCreate, db: AsyncSession = Depends(get_db)):
    if payload.end_date < payload.start_date:
        return Result(code=400, message="End date must be >= start date.", extra={}).http_response()

    obj = OnlineClass(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    await cache.delete_pattern("online_class:list:*")
    return Result(code=201, message="Online class created successfully.", extra={
        "id": obj.id, "title": obj.title, "class_id": obj.class_id,
        "subject_id": obj.subject_id, "url": obj.url, "duration": obj.duration,
        "start_date": str(obj.start_date), "end_date": str(obj.end_date),
    }).http_response()


@exam_router.get(
    "/online_class/list",
    summary="List online classes",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Online classes fetched successfully.", "result": {"total": 1, "page": 1, "limit": 10, "data": [{"id": 1, "class_id": 1, "subject_id": 1}]}}}}},
    },
)
async def list_online_classes(
    class_id:   Optional[int] = Query(None),
    subject_id: Optional[int] = Query(None),
    search:     Optional[str] = Query(None, description="Search by title or url"),
    page:       int           = Query(1,    ge=1),
    limit:      int           = Query(10,   ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    key = f"online_class:list:{class_id}:{subject_id}:{search}:{page}:{limit}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Online classes fetched successfully (cache).", extra=cached).http_response()

    stmt = select(OnlineClass)
    if class_id:   stmt = stmt.where(OnlineClass.class_id   == class_id)
    if subject_id: stmt = stmt.where(OnlineClass.subject_id == subject_id)
    if search:
        stmt = stmt.where(or_(
            OnlineClass.title.like(f"%{search}%"),
            OnlineClass.url.like(f"%{search}%"),
        ))

    total  = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    offset = (page - 1) * limit
    rows   = (await db.execute(stmt.order_by(OnlineClass.id).offset(offset).limit(limit))).scalars().all()

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            {"id": c.id, "title": c.title, "class_id": c.class_id, "subject_id": c.subject_id,
             "url": c.url, "duration": c.duration,
             "start_date": str(c.start_date), "end_date": str(c.end_date)}
            for c in rows
        ],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Online classes fetched successfully.", extra=data).http_response()


@exam_router.put(
    "/online_class/update/{online_class_id}",
    summary="Update online class",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Online class updated successfully.", "result": {"id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Online class not found.", "result": {}}}}},
    },
)
async def update_online_class(online_class_id: int, payload: OnlineClassUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OnlineClass).where(OnlineClass.id == online_class_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return Result(code=404, message="Online class not found.", extra={}).http_response()

    update_data = payload.model_dump(exclude_unset=True)
    start = update_data.get("start_date", obj.start_date)
    end   = update_data.get("end_date",   obj.end_date)
    if end < start:
        return Result(code=400, message="End date must be >= start date.", extra={}).http_response()

    for field, value in update_data.items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)

    await cache.delete_pattern("online_class:list:*")
    return Result(code=200, message="Online class updated successfully.", extra={
        "id": obj.id, "title": obj.title, "class_id": obj.class_id,
        "subject_id": obj.subject_id, "url": obj.url, "duration": obj.duration,
        "start_date": str(obj.start_date), "end_date": str(obj.end_date),
    }).http_response()


@exam_router.delete(
    "/online_class/delete/{online_class_id}",
    summary="Delete online class",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Online class deleted successfully.", "result": {"id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "Online class not found.", "result": {}}}}},
    },
)
async def delete_online_class(online_class_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OnlineClass).where(OnlineClass.id == online_class_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return Result(code=404, message="Online class not found.", extra={}).http_response()

    await db.delete(obj)
    await db.commit()
    await cache.delete_pattern("online_class:list:*")
    return Result(code=200, message="Online class deleted successfully.", extra={"id": online_class_id}).http_response()
