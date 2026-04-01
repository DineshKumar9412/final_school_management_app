# api/school_stream_class_section.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.session import get_db
from database.redis_cache import cache
from models.school_stream_models import (
    SchoolStream,
    SchoolStreamClass,
    SchoolStreamClassSection,
)
from schemas.school_stream_schemas import (
    SchoolStreamClassSectionCreate,
    SchoolStreamClassSectionUpdate,
    SchoolStreamClassSectionResponse,
)
from security.valid_session import valid_session
from response.result import Result

school_stream_section_router = APIRouter(
    tags=["SCHOOL STREAM CLASS SECTION"],
    dependencies=[Depends(valid_session)],
)

CACHE_TTL = 86400  # 1 day
STATUS_VALUES = {"active", "inactive"}

def _item_key(section_id: int) -> str:
    return f"school_stream_section:{section_id}"

def _list_key(page: int, limit: int, search: str | None) -> str:
    return f"school_stream_section:list:{page}:{limit}:{search}"


def _row_to_dict(r) -> dict:
    return {
        "section_id":       r.section_id,
        "school_id":        r.school_id,
        "class_id":         r.class_id,
        "class_code":       r.class_code,
        "school_stream_id": r.school_stream_id,
        "stream_name":      r.stream_name,
        "section_code":     r.section_code,
        "section_name":     r.section_name,
        "status":           r.status,
    }


def _joined_stmt():
    """Base SELECT with JOIN to SchoolStreamClass and LEFT JOIN to SchoolStream."""
    return (
        select(
            SchoolStreamClassSection.section_id,
            SchoolStreamClassSection.school_id,
            SchoolStreamClassSection.class_id,
            SchoolStreamClassSection.school_stream_id,
            SchoolStreamClassSection.section_code,
            SchoolStreamClassSection.section_name,
            SchoolStreamClassSection.status,
            SchoolStreamClass.class_code,
            SchoolStream.stream_name,
        )
        .join(SchoolStreamClass, SchoolStreamClassSection.class_id == SchoolStreamClass.class_id)
        .outerjoin(SchoolStream, SchoolStreamClassSection.school_stream_id == SchoolStream.school_stream_id)
    )


# ─── CREATE ───────────────────────────────────

@school_stream_section_router.post("/create_section", summary="Create a new section")
async def create_section(payload: SchoolStreamClassSectionCreate, db: AsyncSession = Depends(get_db)):
    # duplicate check: same class_id + section_name
    exists = await db.execute(
        select(SchoolStreamClassSection.section_id).where(
            SchoolStreamClassSection.class_id == payload.class_id,
            SchoolStreamClassSection.section_name == payload.section_code,
        )
    )
    if exists.scalar_one_or_none():
        return Result(code=409, message=f"Section name '{payload.section_code}' already exists for this class.", extra={}).http_response()

    obj = SchoolStreamClassSection(**payload.model_dump())
    db.add(obj)
    await db.commit()

    row = (await db.execute(
        _joined_stmt().where(SchoolStreamClassSection.section_id == obj.section_id)
    )).one()
    data = _row_to_dict(row)

    await cache.delete_pattern("school_stream_section:list:*")
    await cache.delete_pattern("school_stream_section:dropdown:*")
    return Result(code=201, message="Section created successfully.", extra=data).http_response()


# ─── GET ALL ──────────────────────────────────

@school_stream_section_router.get("/sectionlist", summary="List all sections (paginated)")
async def list_sections(
    page:   int        = Query(1,    ge=1),
    limit:  int        = Query(10,   ge=1, le=100),
    search: str | None = Query(None, description="Search by section_name/section_code, or type 'active'/'inactive' to filter by status"),
    db: AsyncSession = Depends(get_db),
):
    key = _list_key(page, limit, search)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Sections fetched successfully.", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt = _joined_stmt()

    if search is not None and search.lower() in STATUS_VALUES:
        stmt = stmt.where(SchoolStreamClassSection.status == search.lower())
    elif search is not None:
        stmt = stmt.where(
            SchoolStreamClassSection.status == "active",
            SchoolStreamClassSection.section_name.like(f"%{search}%"),
        )
    else:
        stmt = stmt.where(SchoolStreamClassSection.status == "active")

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await db.execute(stmt.order_by(SchoolStreamClassSection.section_id).offset(offset).limit(limit))

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [_row_to_dict(r) for r in rows.all()],
    }
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Sections fetched successfully.", extra=data).http_response()


# ─── GET BY ID ────────────────────────────────

@school_stream_section_router.get("/get_id/{section_id}", summary="Get a section by ID")
async def get_section(section_id: int, db: AsyncSession = Depends(get_db)):
    key = _item_key(section_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Section fetched successfully.", extra=cached).http_response()

    row = (await db.execute(
        _joined_stmt().where(SchoolStreamClassSection.section_id == section_id)
    )).one_or_none()

    if row is None:
        return Result(code=404, message="Section not found.", extra={}).http_response()

    data = _row_to_dict(row)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Section fetched successfully.", extra=data).http_response()


# ─── UPDATE ───────────────────────────────────

@school_stream_section_router.put("/update_section/{section_id}", summary="Update a section")
async def update_section(section_id: int, payload: SchoolStreamClassSectionUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolStreamClassSection).where(SchoolStreamClassSection.section_id == section_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Section not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()

    row = (await db.execute(
        _joined_stmt().where(SchoolStreamClassSection.section_id == section_id)
    )).one()
    data = _row_to_dict(row)

    await cache.set(_item_key(section_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("school_stream_section:list:*")
    await cache.delete_pattern("school_stream_section:dropdown:*")
    return Result(code=200, message="Section updated successfully.", extra=data).http_response()


# ─── DELETE (soft) ────────────────────────────

@school_stream_section_router.delete("/delete_section/{section_id}", summary="Soft delete a section")
async def delete_section(section_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolStreamClassSection).where(SchoolStreamClassSection.section_id == section_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Section not found.", extra={}).http_response()

    obj.status = "inactive"
    await db.commit()
    await cache.delete(_item_key(section_id))
    await cache.delete_pattern("school_stream_section:list:*")
    await cache.delete_pattern("school_stream_section:dropdown:*")
    return Result(code=200, message="Section deleted successfully.", extra={"section_id": section_id}).http_response()


# ─── DROPDOWN ─────────────────────────────────

@school_stream_section_router.get("/sections/all", summary="Dropdown: Sections")
async def dropdown_sections(class_id: int | None = Query(None), search: str | None = Query(None), db: AsyncSession = Depends(get_db)):
    key = f"dropdown:sections:{class_id}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Dropdown fetched.", extra=cached).http_response()

    stmt = select(SchoolStreamClassSection.section_id, SchoolStreamClassSection.section_name).where(
        SchoolStreamClassSection.status == "active"
    )
    if class_id:
        stmt = stmt.where(SchoolStreamClassSection.class_id == class_id)
    if search:
        stmt = stmt.where(SchoolStreamClassSection.section_name.like(f"%{search}%"))
    stmt = stmt.order_by(SchoolStreamClassSection.section_name)

    rows = await db.execute(stmt)
    data = [{"id": r.section_id, "name": r.section_name} for r in rows.all()]
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Dropdown fetched.", extra=data).http_response()
