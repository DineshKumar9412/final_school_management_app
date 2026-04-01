# api/school_stream_subject.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.session import get_db
from database.redis_cache import cache
from models.school_stream_models import (
    SchoolStream,
    SchoolStreamClass,
    SchoolStreamSubject,
)
from schemas.school_stream_schemas import (
    SchoolStreamSubjectCreate,
    SchoolStreamSubjectUpdate,
    SchoolStreamSubjectResponse,
)
from security.valid_session import valid_session
from response.result import Result

school_stream_subject_router = APIRouter(
    tags=["SCHOOL STREAM SUBJECT"],
    dependencies=[Depends(valid_session)],
)

CACHE_TTL = 86400  # 1 day
STATUS_VALUES = {"active", "inactive"}

def _item_key(subject_id: int) -> str:
    return f"school_stream_subject:{subject_id}"

def _list_key(page: int, limit: int, search: str | None) -> str:
    return f"school_stream_subject:list:{page}:{limit}:{search}"


def _row_to_dict(r) -> dict:
    return {
        "subject_id":       r.subject_id,
        "school_id":        r.school_id,
        "class_id":         r.class_id,
        "class_code":       r.class_code,
        "stream_name":      r.stream_name,
        "subject_name":     r.subject_name,
        "status":           r.status,
    }


def _joined_stmt():
    """Base SELECT with JOIN to SchoolStreamClass and LEFT JOIN to SchoolStream."""
    return (
        select(
            SchoolStreamSubject.subject_id,
            SchoolStreamSubject.school_id,
            SchoolStreamSubject.class_id,
            SchoolStreamSubject.subject_name,
            SchoolStreamSubject.status,
            SchoolStreamClass.class_code,
            SchoolStreamClass.school_stream_id,
            SchoolStream.stream_name,
        )
        .join(SchoolStreamClass, SchoolStreamSubject.class_id == SchoolStreamClass.class_id)
        .outerjoin(SchoolStream, SchoolStreamClass.school_stream_id == SchoolStream.school_stream_id)
    )


# ─── CREATE ───────────────────────────────────

@school_stream_subject_router.post("/create_subject", summary="Create a new subject")
async def create_subject(payload: SchoolStreamSubjectCreate, db: AsyncSession = Depends(get_db)):
    # duplicate check: same class_id + subject_name
    exists = await db.execute(
        select(SchoolStreamSubject.subject_id).where(
            SchoolStreamSubject.class_id == payload.class_id,
            SchoolStreamSubject.subject_name == payload.subject_name,
        )
    )
    if exists.scalar_one_or_none():
        return Result(code=409, message=f"Subject name '{payload.subject_name}' already exists for this class.", extra={}).http_response()

    obj = SchoolStreamSubject(**payload.model_dump())
    db.add(obj)
    await db.commit()

    row = (await db.execute(
        _joined_stmt().where(SchoolStreamSubject.subject_id == obj.subject_id)
    )).one()
    data = _row_to_dict(row)

    await cache.delete_pattern("school_stream_subject:list:*")
    await cache.delete_pattern("school_stream_subject:dropdown:*")
    return Result(code=201, message="Subject created successfully.", extra=data).http_response()


# ─── GET ALL ──────────────────────────────────

@school_stream_subject_router.get("/subjectlist", summary="List all subjects (paginated)")
async def list_subjects(
    page:   int        = Query(1,    ge=1),
    limit:  int        = Query(10,   ge=1, le=100),
    search: str | None = Query(None, description="Search by subject_name, or type 'active'/'inactive' to filter by status"),
    db: AsyncSession = Depends(get_db),
):
    key = _list_key(page, limit, search)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Subjects fetched successfully.", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt = _joined_stmt()

    if search is not None and search.lower() in STATUS_VALUES:
        stmt = stmt.where(SchoolStreamSubject.status == search.lower())
    elif search is not None:
        stmt = stmt.where(
            SchoolStreamSubject.status == "active",
            SchoolStreamSubject.subject_name.like(f"%{search}%"),
        )
    else:
        stmt = stmt.where(SchoolStreamSubject.status == "active")

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await db.execute(stmt.order_by(SchoolStreamSubject.subject_id).offset(offset).limit(limit))

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [_row_to_dict(r) for r in rows.all()],
    }
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Subjects fetched successfully.", extra=data).http_response()


# ─── GET BY ID ────────────────────────────────

@school_stream_subject_router.get("/get_id/{subject_id}", summary="Get a subject by ID")
async def get_subject(subject_id: int, db: AsyncSession = Depends(get_db)):
    key = _item_key(subject_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Subject fetched successfully.", extra=cached).http_response()

    row = (await db.execute(
        _joined_stmt().where(SchoolStreamSubject.subject_id == subject_id)
    )).one_or_none()

    if row is None:
        return Result(code=404, message="Subject not found.", extra={}).http_response()

    data = _row_to_dict(row)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Subject fetched successfully.", extra=data).http_response()


# ─── UPDATE ───────────────────────────────────

@school_stream_subject_router.put("/update_subject/{subject_id}", summary="Update a subject")
async def update_subject(subject_id: int, payload: SchoolStreamSubjectUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolStreamSubject).where(SchoolStreamSubject.subject_id == subject_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Subject not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()

    row = (await db.execute(
        _joined_stmt().where(SchoolStreamSubject.subject_id == subject_id)
    )).one()
    data = _row_to_dict(row)

    await cache.set(_item_key(subject_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("school_stream_subject:list:*")
    await cache.delete_pattern("school_stream_subject:dropdown:*")
    return Result(code=200, message="Subject updated successfully.", extra=data).http_response()


# ─── DELETE (soft) ────────────────────────────

@school_stream_subject_router.delete("/delete_subject/{subject_id}", summary="Soft delete a subject")
async def delete_subject(subject_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolStreamSubject).where(SchoolStreamSubject.subject_id == subject_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Subject not found.", extra={}).http_response()

    obj.status = "inactive"
    await db.commit()
    await cache.delete(_item_key(subject_id))
    await cache.delete_pattern("school_stream_subject:list:*")
    await cache.delete_pattern("school_stream_subject:dropdown:*")
    return Result(code=200, message="Subject deleted successfully.", extra={"subject_id": subject_id}).http_response()


# ─── DROPDOWN ─────────────────────────────────

@school_stream_subject_router.get("/subjects/all", summary="Dropdown: Subjects")
async def dropdown_subjects(class_id: int | None = Query(None), search: str | None = Query(None), db: AsyncSession = Depends(get_db)):
    key = f"dropdown:subjects:{class_id}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Dropdown fetched.", extra=cached).http_response()

    stmt = select(SchoolStreamSubject.subject_id, SchoolStreamSubject.subject_name).where(SchoolStreamSubject.status == "active")
    if class_id:
        stmt = stmt.where(SchoolStreamSubject.class_id == class_id)
    if search:
        stmt = stmt.where(SchoolStreamSubject.subject_name.like(f"%{search}%"))

    rows = await db.execute(stmt.order_by(SchoolStreamSubject.subject_name))
    data = [{"id": r.subject_id, "name": r.subject_name} for r in rows.all()]
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Dropdown fetched.", extra=data).http_response()
