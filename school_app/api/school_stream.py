# api/school_stream.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from database.session import get_db
from database.redis_cache import cache
from models.school_stream_models import (
    SchoolGroup, SchoolStream, SchoolStreamClass, SchoolStreamClassSection, SchoolStreamSubject,
)
from schemas.school_stream_schemas import (
    SchoolStreamCreate, SchoolStreamUpdate, SchoolStreamResponse,
)
from security.valid_session import valid_session
from response.result import Result

school_stream_router = APIRouter(tags=["SCHOOL STREAM"], dependencies=[Depends(valid_session)])

CACHE_TTL = 86400
STATUS_VALUES = {"active", "inactive"}

def clean_search(search: str | None) -> str | None:
    if search is None:
        return None
    return search.strip().strip('"').strip("'").strip()

def _item_key(stream_id: int) -> str:
    return f"school_stream:{stream_id}"

def _list_key(page: int, limit: int, search: str | None) -> str:
    return f"school_stream:list:{page}:{limit}:{search}"

_STREAM_RESULT = {
    "school_stream_id": 1, "school_id": 1, "school_group_id": 1,
    "group_name": "Primary", "stream_name": "Science", "stream_code": "SCI", "status": "active"
}
_404 = {"content": {"application/json": {"example": {"code": 404, "message": "School stream not found.", "result": {}}}}}
_409_STREAM = {"content": {"application/json": {"example": {"code": 409, "message": "Stream name 'Science' already exists for this group.", "result": {}}}}}


@school_stream_router.post("/create_stream", summary="Create a new school stream",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "School stream created successfully.", "result": _STREAM_RESULT}}}},
        409: _409_STREAM,
    },
)
async def create_school_stream(payload: SchoolStreamCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(SchoolStream.school_stream_id).where(
            SchoolStream.school_group_id == payload.school_group_id,
            SchoolStream.stream_name == payload.stream_name,
        )
    )
    if exists.scalar_one_or_none():
        return Result(code=409, message=f"Stream name '{payload.stream_name}' already exists for this group.", extra={}).http_response()

    obj = SchoolStream(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    data = SchoolStreamResponse.model_validate(obj).model_dump(mode="json")
    await cache.delete_pattern("school_stream:list:*")
    await cache.delete_pattern("dropdown:streams:*")
    return Result(code=201, message="School stream created successfully.", extra=data).http_response()


@school_stream_router.get("/streamlist", summary="List all school streams (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200, "message": "School streams fetched successfully.",
            "result": {"total": 2, "page": 1, "limit": 10, "data": [_STREAM_RESULT]}
        }}}},
    },
)
async def list_school_streams(
    page:   int        = Query(1,    ge=1),
    limit:  int        = Query(10,   ge=1, le=100),
    search: str | None = Query(None, description="Search by stream_name, or type 'active'/'inactive'"),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key = _list_key(page, limit, search)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="School streams fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt = (
        select(
            SchoolStream.school_stream_id, SchoolStream.school_id, SchoolStream.school_group_id,
            SchoolStream.stream_name, SchoolStream.stream_code, SchoolStream.status, SchoolGroup.group_name,
        )
        .join(SchoolGroup, SchoolStream.school_group_id == SchoolGroup.school_group_id)
    )

    if search is not None and search.lower() in STATUS_VALUES:
        stmt = stmt.where(SchoolStream.status == search.lower())
    elif search is not None:
        stmt = stmt.where(SchoolStream.status == "active", SchoolStream.stream_name.like(f"%{search}%"))
    else:
        stmt = stmt.where(SchoolStream.status == "active")

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await db.execute(stmt.order_by(SchoolStream.school_stream_id).offset(offset).limit(limit))

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            {
                "school_stream_id": r.school_stream_id,
                "school_id":        r.school_id,
                "school_group_id": r.school_group_id,
                "group_name":       r.group_name,
                "stream_name":      r.stream_name,
                "stream_code":      r.stream_code,
                "status":           r.status,
            }
            for r in rows.all()
        ],
    }
    if total > 0:  # only cache when data exists
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="School streams fetched successfully.", extra=data).http_response()


@school_stream_router.get("/get_id/{stream_id}", summary="Get a school stream by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "School stream fetched successfully.", "result": _STREAM_RESULT}}}},
        404: _404,
    },
)
async def get_school_stream(stream_id: int, db: AsyncSession = Depends(get_db)):
    key = _item_key(stream_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="School stream fetched successfully (cache).", extra=cached).http_response()

    result = await db.execute(select(SchoolStream).where(SchoolStream.school_stream_id == stream_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="School stream not found.", extra={}).http_response()

    data = SchoolStreamResponse.model_validate(obj).model_dump(mode="json")
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="School stream fetched successfully.", extra=data).http_response()


@school_stream_router.put("/update_stream/{stream_id}", summary="Update a school stream",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "School stream updated successfully.", "result": _STREAM_RESULT}}}},
        404: _404,
    },
)
async def update_school_stream(stream_id: int, payload: SchoolStreamUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolStream).where(SchoolStream.school_stream_id == stream_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="School stream not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    data = SchoolStreamResponse.model_validate(obj).model_dump(mode="json")

    await cache.set(_item_key(stream_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("school_stream:list:*")
    await cache.delete_pattern("dropdown:streams:*")
    return Result(code=200, message="School stream updated successfully.", extra=data).http_response()


@school_stream_router.delete("/delete_stream/{stream_id}", summary="Soft delete a stream and all its children",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "School stream and all related records deleted successfully.", "result": {"school_stream_id": 1}}}}},
        404: _404,
    },
)
async def delete_school_stream(stream_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolStream).where(SchoolStream.school_stream_id == stream_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="School stream not found.", extra={}).http_response()

    class_ids = (await db.execute(select(SchoolStreamClass.class_id).where(SchoolStreamClass.school_stream_id == stream_id))).scalars().all()
    if class_ids:
        await db.execute(update(SchoolStreamClassSection).where(SchoolStreamClassSection.class_id.in_(class_ids)).values(status="inactive"))
        await db.execute(update(SchoolStreamSubject).where(SchoolStreamSubject.class_id.in_(class_ids)).values(status="inactive"))
        await db.execute(update(SchoolStreamClass).where(SchoolStreamClass.class_id.in_(class_ids)).values(status="inactive"))

    obj.status = "inactive"
    await db.commit()
    await cache.delete(_item_key(stream_id))
    await cache.delete_pattern("school_stream:list:*")
    await cache.delete_pattern("dropdown:streams:*")
    await cache.delete_pattern("school_stream_class:*")
    await cache.delete_pattern("dropdown:classes:*")
    await cache.delete_pattern("school_stream_section:*")
    await cache.delete_pattern("dropdown:sections:*")
    await cache.delete_pattern("school_stream_subject:*")
    await cache.delete_pattern("dropdown:subjects:*")
    await cache.delete_pattern("dropdown:*")
    return Result(code=200, message="School stream and all related records deleted successfully.", extra={"school_stream_id": stream_id}).http_response()


@school_stream_router.get("/streams/all", summary="Dropdown: Streams",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200, "message": "Dropdown fetched.",
            "result": [{"id": 1, "name": "Science", "group_name": "Primary"}]
        }}}},
    },
)
async def dropdown_streams(
    school_group_id: int | None = Query(None),
    search:          str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key = f"dropdown:streams:{school_group_id}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Dropdown fetched (cache).", extra=cached).http_response()

    stmt = (
        select(SchoolStream.school_stream_id, SchoolStream.stream_name, SchoolGroup.group_name)
        .join(SchoolGroup, SchoolStream.school_group_id == SchoolGroup.school_group_id)
        .where(SchoolStream.status == "active")
    )
    if school_group_id:
        stmt = stmt.where(SchoolStream.school_group_id == school_group_id)
    if search:
        stmt = stmt.where(SchoolStream.stream_name.like(f"%{search}%"))

    rows = await db.execute(stmt.order_by(SchoolStream.stream_name))
    data = [{"school_stream_id": r.school_stream_id, "stream_name": r.stream_name, "group_name": r.group_name} for r in rows.all()]
    if data:  # only cache when data exists
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Dropdown fetched.", extra=data).http_response()
