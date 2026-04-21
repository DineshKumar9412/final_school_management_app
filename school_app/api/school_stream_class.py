# api/school_stream_class.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update, outerjoin

from database.session import get_db
from database.redis_cache import cache
from models.school_stream_models import (
    SchoolGroup, SchoolStream, SchoolStreamClass, SchoolStreamClassSection, SchoolStreamSubject,
)
from schemas.school_stream_schemas import (
    SchoolStreamClassCreate, SchoolStreamClassUpdate, SchoolStreamClassResponse,
)
from security.valid_session import valid_session
from response.result import Result

school_stream_class_router = APIRouter(tags=["SCHOOL STREAM CLASS"], dependencies=[Depends(valid_session)])

CACHE_TTL = 86400
STATUS_VALUES = {"active", "inactive"}

def clean_search(search: str | None) -> str | None:
    if search is None:
        return None
    return search.strip().strip('"').strip("'").strip()

def _item_key(class_id: int) -> str:
    return f"school_stream_class:{class_id}"

def _list_key(page: int, limit: int, search: str | None, school_group_id: int | None = None) -> str:
    return f"school_stream_class:list:{page}:{limit}:{search}:{school_group_id}"

def _row_to_dict(r) -> dict:
    return {
        "class_id": r.class_id, "school_id": r.school_id,
        "school_group_id": r.school_group_id, "group_name": r.group_name,
        "school_stream_id": r.school_stream_id, "stream_name": r.stream_name,
        "class_code": r.class_code, "status": r.status,
    }

def _joined_stmt():
    return (
        select(
            SchoolStreamClass.class_id, SchoolStreamClass.school_id,
            SchoolStreamClass.school_group_id, SchoolStreamClass.school_stream_id,
            SchoolStreamClass.class_code, SchoolStreamClass.status,
            SchoolGroup.group_name, SchoolStream.stream_name,
        )
        .join(SchoolGroup, SchoolStreamClass.school_group_id == SchoolGroup.school_group_id)
        .outerjoin(SchoolStream, SchoolStreamClass.school_stream_id == SchoolStream.school_stream_id)
    )

_CLASS_RESULT = {
    "class_id": 1, "school_id": 1, "school_group_id": 1, "group_name": "Primary",
    "school_stream_id": 1, "stream_name": "Science", "class_code": "10", "status": "active"
}
_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Class not found.", "result": {}}}}}
_409 = {"content": {"application/json": {"example": {"code": 409, "message": "Class code '10' already exists for this group.", "result": {}}}}}


@school_stream_class_router.post("/create_class", summary="Create a new class",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Class created successfully.", "result": _CLASS_RESULT}}}},
        409: _409,
    },
)
async def create_class(payload: SchoolStreamClassCreate, db: AsyncSession = Depends(get_db)):
    if payload.class_code:
        exists = await db.execute(
            select(SchoolStreamClass.class_id).where(
                SchoolStreamClass.school_group_id == payload.school_group_id,
                SchoolStreamClass.class_code == payload.class_code,
            )
        )
        if exists.scalar_one_or_none():
            return Result(code=409, message=f"Class code '{payload.class_code}' already exists for this group.", extra={}).http_response()

    obj = SchoolStreamClass(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    row = (await db.execute(_joined_stmt().where(SchoolStreamClass.class_id == obj.class_id))).one()
    data = _row_to_dict(row)
    await cache.delete_pattern("school_stream_class:list:*")
    await cache.delete_pattern("dropdown:classes:*")
    return Result(code=201, message="Class created successfully.", extra=data).http_response()


@school_stream_class_router.get("/classlist", summary="List all classes (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200, "message": "Classes fetched successfully.",
            "result": {"total": 2, "page": 1, "limit": 10, "data": [_CLASS_RESULT]}
        }}}},
    },
)
async def list_classes(
    page:            int        = Query(1,    ge=1),
    limit:           int        = Query(10,   ge=1, le=100),
    search:          str | None = Query(None, description="Search by class_code, or type 'active'/'inactive'"),
    school_group_id: int | None = Query(None, description="Filter by school group ID"),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key = _list_key(page, limit, search, school_group_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Classes fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt = _joined_stmt()

    if school_group_id is not None:
        stmt = stmt.where(SchoolStreamClass.school_group_id == school_group_id)

    if search is not None and search.lower() in STATUS_VALUES:
        stmt = stmt.where(SchoolStreamClass.status == search.lower())
    elif search is not None:
        stmt = stmt.where(SchoolStreamClass.status == "active", SchoolStreamClass.class_code.like(f"%{search}%"))
    else:
        stmt = stmt.where(SchoolStreamClass.status == "active")

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await db.execute(stmt.order_by(SchoolStreamClass.class_id).offset(offset).limit(limit))

    data = {"total": total, "page": page, "limit": limit, "data": [_row_to_dict(r) for r in rows.all()]}
    if total > 0:  # only cache when data exists
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Classes fetched successfully.", extra=data).http_response()


@school_stream_class_router.get("/get_id/{class_id}", summary="Get a class by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Class fetched successfully.", "result": _CLASS_RESULT}}}},
        404: _404,
    },
)
async def get_class(class_id: int, db: AsyncSession = Depends(get_db)):
    key = _item_key(class_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Class fetched successfully (cache).", extra=cached).http_response()

    row = (await db.execute(_joined_stmt().where(SchoolStreamClass.class_id == class_id))).one_or_none()
    if row is None:
        return Result(code=404, message="Class not found.", extra={}).http_response()

    data = _row_to_dict(row)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Class fetched successfully.", extra=data).http_response()


@school_stream_class_router.put("/update_class/{class_id}", summary="Update a class",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Class updated successfully.", "result": _CLASS_RESULT}}}},
        404: _404,
    },
)
async def update_class(class_id: int, payload: SchoolStreamClassUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolStreamClass).where(SchoolStreamClass.class_id == class_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Class not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()

    row = (await db.execute(_joined_stmt().where(SchoolStreamClass.class_id == class_id))).one()
    data = _row_to_dict(row)
    await cache.set(_item_key(class_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("school_stream_class:list:*")
    await cache.delete_pattern("dropdown:classes:*")
    return Result(code=200, message="Class updated successfully.", extra=data).http_response()


@school_stream_class_router.delete("/delete_class/{class_id}", summary="Soft delete a class and all its children",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Class and all related records deleted successfully.", "result": {"class_id": 1}}}}},
        404: _404,
    },
)
async def delete_class(class_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolStreamClass).where(SchoolStreamClass.class_id == class_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Class not found.", extra={}).http_response()

    await db.execute(update(SchoolStreamClassSection).where(SchoolStreamClassSection.class_id == class_id).values(status="inactive"))
    await db.execute(update(SchoolStreamSubject).where(SchoolStreamSubject.class_id == class_id).values(status="inactive"))
    obj.status = "inactive"
    await db.commit()

    await cache.delete(_item_key(class_id))
    await cache.delete_pattern("school_stream_class:list:*")
    await cache.delete_pattern("dropdown:classes:*")
    await cache.delete_pattern("school_stream_section:*")
    await cache.delete_pattern("dropdown:sections:*")
    await cache.delete_pattern("school_stream_subject:*")
    await cache.delete_pattern("dropdown:subjects:*")
    await cache.delete_pattern("dropdown:*")
    return Result(code=200, message="Class and all related records deleted successfully.", extra={"class_id": class_id}).http_response()


@school_stream_class_router.get("/classes/all", summary="Dropdown: Classes",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200, "message": "Dropdown fetched.",
            "result": [{"id": 1, "name": "10"}, {"id": 2, "name": "11"}]
        }}}},
    },
)
async def dropdown_classes(school_stream_id: int | None = Query(None), school_group_id: int | None = Query(None), search: str | None = Query(None), db: AsyncSession = Depends(get_db)):
    search = clean_search(search)
    key = f"dropdown:classes:{school_stream_id}:{school_group_id}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Dropdown fetched (cache).", extra=cached).http_response()

    stmt = (
        select(
            SchoolStreamClass.class_id,
            SchoolStreamClass.class_code,
            SchoolStream.stream_name,
        )
        .outerjoin(SchoolStream, SchoolStreamClass.school_stream_id == SchoolStream.school_stream_id)
        .where(SchoolStreamClass.status == "active")
    )
    if school_stream_id:
        stmt = stmt.where(SchoolStreamClass.school_stream_id == school_stream_id)
    if school_group_id:
        stmt = stmt.where(SchoolStreamClass.school_group_id == school_group_id)
    if search:
        stmt = stmt.where(SchoolStreamClass.class_code.like(f"%{search}%"))

    rows = await db.execute(stmt.order_by(SchoolStreamClass.class_code))
    data = [
        {"class_id": r.class_id, "class_code": r.class_code, "stream_name": r.stream_name}
        for r in rows.all()
    ]
    if data:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Dropdown fetched.", extra=data).http_response()