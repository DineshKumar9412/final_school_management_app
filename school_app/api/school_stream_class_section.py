# api/school_stream_class_section.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from database.session import get_db
from database.redis_cache import cache
from models.school_stream_models import SchoolStream, SchoolStreamClass, SchoolStreamClassSection
from schemas.school_stream_schemas import (
    SchoolStreamClassSectionCreate, SchoolStreamClassSectionUpdate, SchoolStreamClassSectionResponse,
)
from security.valid_session import valid_session
from response.result import Result

school_stream_section_router = APIRouter(tags=["SCHOOL STREAM CLASS SECTION"], dependencies=[Depends(valid_session)])

CACHE_TTL = 86400
STATUS_VALUES = {"active", "inactive"}

def clean_search(search: str | None) -> str | None:
    if search is None:
        return None
    return search.strip().strip('"').strip("'").strip()

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
        "school_stream_id": r.class_school_stream_id,   # ← unique label from class table
        "stream_name":      r.stream_name,
        "section_code":     r.section_code,
        "section_name":     r.section_name,
        "status":           r.status,
    }

def _joined_stmt():
    return (
        select(
            SchoolStreamClassSection.section_id,
            SchoolStreamClassSection.school_id,
            SchoolStreamClassSection.class_id,
            SchoolStreamClass.school_stream_id.label("class_school_stream_id"),  # ← unique label
            SchoolStreamClassSection.section_code,
            SchoolStreamClassSection.section_name,
            SchoolStreamClassSection.status,
            SchoolStreamClass.class_code,
            SchoolStream.stream_name,
        )
        .select_from(SchoolStreamClassSection)
        .join(SchoolStreamClass, SchoolStreamClassSection.class_id == SchoolStreamClass.class_id)
        .outerjoin(SchoolStream, SchoolStreamClass.school_stream_id == SchoolStream.school_stream_id)
    )

def _count_stmt():
    return (
        select(func.count(SchoolStreamClassSection.section_id))
        .select_from(SchoolStreamClassSection)
        .join(SchoolStreamClass, SchoolStreamClassSection.class_id == SchoolStreamClass.class_id)
        .outerjoin(SchoolStream, SchoolStreamClass.school_stream_id == SchoolStream.school_stream_id)  # ← join via class
    )

_SECTION_RESULT = {
    "section_id": 1, "school_id": 1, "class_id": 1, "class_code": "10",
    "school_stream_id": None, "stream_name": None,
    "section_code": "A", "section_name": "Rose", "status": "active"
}
_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Section not found.", "result": {}}}}}
_409 = {"content": {"application/json": {"example": {"code": 409, "message": "Section code 'A' already exists for this class.", "result": {}}}}}


@school_stream_section_router.post("/create_section", summary="Create a new section",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Section created successfully.", "result": _SECTION_RESULT}}}},
        409: _409,
    },
)
async def create_section(payload: SchoolStreamClassSectionCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(SchoolStreamClassSection.section_id).where(
            SchoolStreamClassSection.class_id == payload.class_id,
            SchoolStreamClassSection.section_code == payload.section_code,
        )
    )
    if exists.scalar_one_or_none():
        return Result(code=409, message=f"Section code '{payload.section_code}' already exists for this class.", extra={}).http_response()

    obj = SchoolStreamClassSection(**payload.model_dump())
    db.add(obj)
    await db.commit()

    row = (await db.execute(_joined_stmt().where(SchoolStreamClassSection.section_id == obj.section_id))).one()
    data = _row_to_dict(row)
    await cache.delete_pattern("school_stream_section:list:*")
    await cache.delete_pattern("school_stream_section:dropdown:*")
    return Result(code=201, message="Section created successfully.", extra=data).http_response()


@school_stream_section_router.get("/sectionlist", summary="List all sections (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200, "message": "Sections fetched successfully.",
            "result": {"total": 4, "page": 1, "limit": 10, "data": [_SECTION_RESULT]}
        }}}},
    },
)
async def list_sections(
    page:   int        = Query(1,    ge=1),
    limit:  int        = Query(10,   ge=1, le=100),
    search: str | None = Query(None, description="Search by section_name, section_code, class_code, or type 'active'/'inactive'"),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key = _list_key(page, limit, search)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Sections fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit

    if search is not None and search.lower() in STATUS_VALUES:
        filters = [SchoolStreamClassSection.status == search.lower()]
    elif search is not None:
        filters = [
            SchoolStreamClassSection.status == "active",
            or_(
                SchoolStreamClassSection.section_name.like(f"%{search}%"),
                SchoolStreamClassSection.section_code.like(f"%{search}%"),
                SchoolStreamClass.class_code.like(f"%{search}%"),
            ),
        ]
    else:
        filters = [SchoolStreamClassSection.status == "active"]

    total = (await db.execute(_count_stmt().where(*filters))).scalar_one()
    rows = await db.execute(_joined_stmt().where(*filters).order_by(SchoolStreamClassSection.section_id).offset(offset).limit(limit))

    data = {"total": total, "page": page, "limit": limit, "data": [_row_to_dict(r) for r in rows.all()]}
    if total > 0:  # only cache when data exists
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Sections fetched successfully.", extra=data).http_response()


@school_stream_section_router.get("/get_id/{section_id}", summary="Get a section by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Section fetched successfully.", "result": _SECTION_RESULT}}}},
        404: _404,
    },
)
async def get_section(section_id: int, db: AsyncSession = Depends(get_db)):
    key = _item_key(section_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Section fetched successfully (cache).", extra=cached).http_response()

    row = (await db.execute(_joined_stmt().where(SchoolStreamClassSection.section_id == section_id))).one_or_none()
    if row is None:
        return Result(code=404, message="Section not found.", extra={}).http_response()

    data = _row_to_dict(row)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Section fetched successfully.", extra=data).http_response()


@school_stream_section_router.put("/update_section/{section_id}", summary="Update a section",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Section updated successfully.", "result": _SECTION_RESULT}}}},
        404: _404,
    },
)
async def update_section(section_id: int, payload: SchoolStreamClassSectionUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolStreamClassSection).where(SchoolStreamClassSection.section_id == section_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Section not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()

    row = (await db.execute(_joined_stmt().where(SchoolStreamClassSection.section_id == section_id))).one()
    data = _row_to_dict(row)
    await cache.set(_item_key(section_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("school_stream_section:list:*")
    await cache.delete_pattern("school_stream_section:dropdown:*")
    return Result(code=200, message="Section updated successfully.", extra=data).http_response()


@school_stream_section_router.delete("/delete_section/{section_id}", summary="Soft delete a section",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Section deleted successfully.", "result": {"section_id": 1}}}}},
        404: _404,
    },
)
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


@school_stream_section_router.get("/sections/all", summary="Dropdown: Sections",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200, "message": "Dropdown fetched.",
            "result": [{"id": 1, "name": "Rose"}, {"id": 2, "name": "Lily"}]
        }}}},
    },
)
async def dropdown_sections(
    class_id:         int | None = Query(None),
    school_stream_id: int | None = Query(None),
    search:           str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key = f"dropdown:sections:{class_id}:{school_stream_id}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Dropdown fetched (cache).", extra=cached).http_response()

    stmt = (
        select(
            SchoolStreamClassSection.section_id,
            SchoolStreamClassSection.section_code,
            SchoolStream.stream_name,
        )
        .join(SchoolStreamClass, SchoolStreamClassSection.class_id == SchoolStreamClass.class_id)
        .outerjoin(SchoolStream, SchoolStreamClass.school_stream_id == SchoolStream.school_stream_id)
        .where(SchoolStreamClassSection.status == "active")
    )
    if class_id:
        stmt = stmt.where(SchoolStreamClassSection.class_id == class_id)
    if school_stream_id:
        stmt = stmt.where(SchoolStreamClass.school_stream_id == school_stream_id)
    if search:
        stmt = stmt.where(SchoolStreamClassSection.section_name.like(f"%{search}%"))
    stmt = stmt.order_by(SchoolStreamClassSection.section_name)

    rows = await db.execute(stmt)
    data = [
        {
            "section_id":   r.section_id,
            "section_code": r.section_code,
            "stream_name":  r.stream_name,
        }
        for r in rows.all()
    ]
    if data:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Dropdown fetched.", extra=data).http_response()
