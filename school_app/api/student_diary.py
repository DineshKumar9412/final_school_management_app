# api/student_diary.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.session import get_db
from database.redis_cache import cache
from models.student_diary_models import StudentDiary
from models.student_models import Student
from models.school_stream_models import SchoolStreamClass, SchoolStreamClassSection, SchoolStreamSubject
from schemas.student_diary_schemas import StudentDiaryCreate, StudentDiaryUpdate
from security.valid_session import valid_session
from response.result import Result
from datetime import date

student_diary_router = APIRouter(tags=["STUDENT DIARY"], dependencies=[Depends(valid_session)])

CACHE_TTL = 86400


# ─── helpers ──────────────────────────────────────────────────────────────────

def clean_search(s: str | None) -> str | None:
    if s is None:
        return None
    return s.strip().strip('"').strip("'").strip() or None


def _item_key(diary_id: int) -> str:
    return f"student_diary:{diary_id}"


def _list_key(page: int, limit: int, search: str | None, student_id: int | None,
              class_id: int | None, section_id: int | None, subject_id: int | None,
              dairy_date: date | None, status: str | None) -> str:
    return f"student_diary:list:{page}:{limit}:{search}:{student_id}:{class_id}:{section_id}:{subject_id}:{dairy_date}:{status}"


def _row_to_dict(d: StudentDiary, student_name: str | None, class_code: str | None,
                 section_name: str | None, subject_name: str | None) -> dict:
    return {
        "id":           d.id,
        "student_id":   d.student_id,
        "student_name": student_name,
        "class_id":     d.class_id,
        "class_code":   class_code,
        "section_id":   d.section_id,
        "section_name": section_name,
        "subject_id":   d.subject_id,
        "subject_name": subject_name,
        "task_title":   d.task_title,
        "dairy_date":   d.dairy_date.isoformat() if d.dairy_date else None,
        "status":       d.status,
        "created_at":   d.created_at.isoformat(),
        "updated_at":   d.updated_at.isoformat(),
    }


async def _fetch_labels(db: AsyncSession, student_id: int, class_id: int | None,
                        section_id: int | None, subject_id: int | None):
    """Fetch joined label values for a single diary entry."""
    student_name = None
    class_code   = None
    section_name = None
    subject_name = None

    student = (await db.execute(
        select(Student.first_name, Student.last_name).where(Student.student_id == student_id)
    )).one_or_none()
    if student:
        student_name = f"{student.first_name} {student.last_name}".strip()

    if class_id:
        row = (await db.execute(
            select(SchoolStreamClass.class_code).where(SchoolStreamClass.class_id == class_id)
        )).scalar_one_or_none()
        class_code = row

    if section_id:
        row = (await db.execute(
            select(SchoolStreamClassSection.section_name).where(SchoolStreamClassSection.section_id == section_id)
        )).scalar_one_or_none()
        section_name = row

    if subject_id:
        row = (await db.execute(
            select(SchoolStreamSubject.subject_name).where(SchoolStreamSubject.subject_id == subject_id)
        )).scalar_one_or_none()
        subject_name = row

    return student_name, class_code, section_name, subject_name


_EXAMPLE = {
    "id": 1, "student_id": 1, "student_name": "John Doe",
    "class_id": 1, "class_code": "10",
    "section_id": 1, "section_name": "Rose",
    "subject_id": 1, "subject_name": "Mathematics",
    "task_title": "Math Homework", "dairy_date": "2024-08-15",
    "status": "P",
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:00:00",
}
_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Diary entry not found.", "result": {}}}}}


# ─── CREATE ───────────────────────────────────────────────────────────────────

@student_diary_router.post(
    "/create",
    summary="Create a student diary entry",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Diary entry created successfully.", "result": _EXAMPLE}}}},
    },
)
async def create_diary(payload: StudentDiaryCreate, db: AsyncSession = Depends(get_db)):
    obj = StudentDiary(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    student_name, class_code, section_name, subject_name = await _fetch_labels(
        db, obj.student_id, obj.class_id, obj.section_id, obj.subject_id
    )
    data = _row_to_dict(obj, student_name, class_code, section_name, subject_name)
    await cache.set(_item_key(obj.id), data, expire=CACHE_TTL)
    await cache.delete_pattern("student_diary:list:*")
    return Result(code=201, message="Diary entry created successfully.", extra=data).http_response()


# ─── LIST (paginated) ─────────────────────────────────────────────────────────

@student_diary_router.get(
    "/list",
    summary="List all diary entries (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200, "message": "Diary entries fetched successfully.",
            "result": {"total": 2, "page": 1, "limit": 10, "data": [_EXAMPLE]},
        }}}},
    },
)
async def list_diaries(
    page:       int        = Query(1,    ge=1),
    limit:      int        = Query(10,   ge=1, le=100),
    search:     str | None = Query(None, description="Search by task_title"),
    student_id: int | None = Query(None, description="Filter by student ID"),
    class_id:   int | None = Query(None, description="Filter by class ID"),
    section_id: int | None = Query(None, description="Filter by section ID"),
    subject_id: int | None = Query(None, description="Filter by subject ID"),
    dairy_date: date | None = Query(None, description="Filter by diary date e.g. 2024-08-15"),
    status:     str | None = Query(None, description="Filter by status e.g. P / C"),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key    = _list_key(page, limit, search, student_id, class_id, section_id, subject_id, dairy_date, status)

    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Diary entries fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt   = select(StudentDiary)

    if student_id is not None:
        stmt = stmt.where(StudentDiary.student_id == student_id)
    if class_id is not None:
        stmt = stmt.where(StudentDiary.class_id == class_id)
    if section_id is not None:
        stmt = stmt.where(StudentDiary.section_id == section_id)
    if subject_id is not None:
        stmt = stmt.where(StudentDiary.subject_id == subject_id)
    if dairy_date is not None:
        stmt = stmt.where(StudentDiary.dairy_date == dairy_date)
    if status is not None:
        stmt = stmt.where(StudentDiary.status == status)
    if search:
        stmt = stmt.where(StudentDiary.task_title.like(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await db.execute(
        stmt.order_by(StudentDiary.dairy_date.desc(), StudentDiary.id.desc()).offset(offset).limit(limit)
    )).scalars().all()

    # batch-fetch labels
    student_ids  = {d.student_id for d in rows}
    class_ids    = {d.class_id   for d in rows if d.class_id}
    section_ids  = {d.section_id for d in rows if d.section_id}
    subject_ids  = {d.subject_id for d in rows if d.subject_id}

    student_map: dict[int, str] = {}
    class_map:   dict[int, str] = {}
    section_map: dict[int, str] = {}
    subject_map: dict[int, str] = {}

    if student_ids:
        s_rows = (await db.execute(
            select(Student.student_id, Student.first_name, Student.last_name)
            .where(Student.student_id.in_(student_ids))
        )).all()
        student_map = {r.student_id: f"{r.first_name} {r.last_name}".strip() for r in s_rows}

    if class_ids:
        c_rows = (await db.execute(
            select(SchoolStreamClass.class_id, SchoolStreamClass.class_code)
            .where(SchoolStreamClass.class_id.in_(class_ids))
        )).all()
        class_map = {r.class_id: r.class_code for r in c_rows}

    if section_ids:
        sec_rows = (await db.execute(
            select(SchoolStreamClassSection.section_id, SchoolStreamClassSection.section_name)
            .where(SchoolStreamClassSection.section_id.in_(section_ids))
        )).all()
        section_map = {r.section_id: r.section_name for r in sec_rows}

    if subject_ids:
        sub_rows = (await db.execute(
            select(SchoolStreamSubject.subject_id, SchoolStreamSubject.subject_name)
            .where(SchoolStreamSubject.subject_id.in_(subject_ids))
        )).all()
        subject_map = {r.subject_id: r.subject_name for r in sub_rows}

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            _row_to_dict(
                d,
                student_map.get(d.student_id),
                class_map.get(d.class_id),
                section_map.get(d.section_id),
                subject_map.get(d.subject_id),
            )
            for d in rows
        ],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Diary entries fetched successfully.", extra=data).http_response()


# ─── GET BY ID ────────────────────────────────────────────────────────────────

@student_diary_router.get(
    "/get/{diary_id}",
    summary="Get a diary entry by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Diary entry fetched successfully.", "result": _EXAMPLE}}}},
        404: _404,
    },
)
async def get_diary(diary_id: int, db: AsyncSession = Depends(get_db)):
    key    = _item_key(diary_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Diary entry fetched successfully (cache).", extra=cached).http_response()

    obj = (await db.execute(select(StudentDiary).where(StudentDiary.id == diary_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Diary entry not found.", extra={}).http_response()

    student_name, class_code, section_name, subject_name = await _fetch_labels(
        db, obj.student_id, obj.class_id, obj.section_id, obj.subject_id
    )
    data = _row_to_dict(obj, student_name, class_code, section_name, subject_name)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Diary entry fetched successfully.", extra=data).http_response()


# ─── UPDATE ───────────────────────────────────────────────────────────────────

@student_diary_router.put(
    "/update/{diary_id}",
    summary="Update a diary entry",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Diary entry updated successfully.", "result": _EXAMPLE}}}},
        404: _404,
    },
)
async def update_diary(diary_id: int, payload: StudentDiaryUpdate, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(StudentDiary).where(StudentDiary.id == diary_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Diary entry not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)

    student_name, class_code, section_name, subject_name = await _fetch_labels(
        db, obj.student_id, obj.class_id, obj.section_id, obj.subject_id
    )
    data = _row_to_dict(obj, student_name, class_code, section_name, subject_name)
    await cache.set(_item_key(diary_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("student_diary:list:*")
    return Result(code=200, message="Diary entry updated successfully.", extra=data).http_response()


# ─── DELETE ───────────────────────────────────────────────────────────────────

@student_diary_router.delete(
    "/delete/{diary_id}",
    summary="Delete a diary entry",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Diary entry deleted successfully.", "result": {"id": 1}}}}},
        404: _404,
    },
)
async def delete_diary(diary_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(StudentDiary).where(StudentDiary.id == diary_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Diary entry not found.", extra={}).http_response()

    await db.delete(obj)
    await db.commit()

    await cache.delete(_item_key(diary_id))
    await cache.delete_pattern("student_diary:list:*")
    return Result(code=200, message="Diary entry deleted successfully.", extra={"id": diary_id}).http_response()
