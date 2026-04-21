# api/school_group.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from database.session import get_db
from database.redis_cache import cache
from models.school_stream_models import (
    SchoolGroup, SchoolStream, SchoolStreamClass, SchoolStreamClassSection, SchoolStreamSubject,
)
from schemas.school_stream_schemas import (
    SchoolGroupCreateRequest, SchoolGroupUpdateRequest, SchoolGroupResponse,
)
from security.valid_session import valid_session
from response.result import Result

school_group_router = APIRouter(tags=["SCHOOL GROUP"], dependencies=[Depends(valid_session)])

CACHE_TTL = 86400
STATUS_VALUES = {"active", "inactive"}

def clean_search(search: str | None) -> str | None:
    if search is None:
        return None
    return search.strip().strip('"').strip("'").strip()

def _group_key(group_id: int) -> str:
    return f"school_group:{group_id}"

def _list_key(page: int, limit: int, search: str | None) -> str:
    return f"school_groups:list:{page}:{limit}:{search}"


@school_group_router.post(
    "/create_group", summary="Create a new school group",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "School group created successfully.", "result": {"school_group_id": 1, "school_id": 1, "group_name": "Primary", "status": "active"}}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Group name 'Primary' already exists for this school.", "result": {}}}}},
    },
)
async def create_school_group(payload: SchoolGroupCreateRequest, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(SchoolGroup.school_group_id).where(
            SchoolGroup.school_id == payload.school_id,
            SchoolGroup.group_name == payload.group_name,
        )
    )
    if exists.scalar_one_or_none():
        return Result(code=409, message=f"Group name '{payload.group_name}' already exists for this school.", extra={}).http_response()

    group = SchoolGroup(**payload.model_dump())
    db.add(group)
    await db.commit()
    await db.refresh(group)

    data = SchoolGroupResponse.model_validate(group).model_dump(mode="json")
    await cache.delete_pattern("school_groups:*")
    await cache.delete_pattern("dropdown:school_groups:*")
    return Result(code=201, message="School group created successfully.", extra=data).http_response()


@school_group_router.get(
    "/grouplist", summary="List all school groups",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "School groups fetched successfully.", "result": {"total": 2, "page": 1, "limit": 10, "data": [{"school_group_id": 1, "school_id": 1, "group_name": "Primary", "status": "active"}]}}}}},
    },
)
async def list_school_groups(
    school_id: int | None = Query(None),
    page:      int        = Query(1,  ge=1),
    limit:     int        = Query(10, ge=1, le=100),
    search:    str | None = Query(None, description="Search by group_name, or type 'active'/'inactive'"),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key = _list_key(page, limit, search)
    cached = await cache.get(key)
    if cached is not None:
        return Result(code=200, message="School groups fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt = select(SchoolGroup)
    if school_id is not None:
        stmt = stmt.where(SchoolGroup.school_id == school_id)
    if search is not None and search.lower() in STATUS_VALUES:
        stmt = stmt.where(SchoolGroup.status == search.lower())
    elif search is not None:
        stmt = stmt.where(SchoolGroup.status == "active", SchoolGroup.group_name.like(f"%{search}%"))
    else:
        stmt = stmt.where(SchoolGroup.status == "active")

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    result = await db.execute(stmt.order_by(SchoolGroup.school_group_id).offset(offset).limit(limit))
    data = {
        "total": total, "page": page, "limit": limit,
        "data": [SchoolGroupResponse.model_validate(g).model_dump(mode="json") for g in result.scalars().all()],
    }
    if total > 0:  # only cache when data exists
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="School groups fetched successfully.", extra=data).http_response()


@school_group_router.get(
    "/get_id/{group_id}", summary="Get a school group by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "School group fetched successfully.", "result": {"school_group_id": 1, "school_id": 1, "group_name": "Primary", "status": "active"}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "School group not found.", "result": {}}}}},
    },
)
async def get_school_group(group_id: int, db: AsyncSession = Depends(get_db)):
    key = _group_key(group_id)
    cached = await cache.get(key)
    if cached is not None:
        return Result(code=200, message="School group fetched successfully (cache).", extra=cached).http_response()

    result = await db.execute(select(SchoolGroup).where(SchoolGroup.school_group_id == group_id))
    group = result.scalar_one_or_none()
    if group is None:
        return Result(code=404, message="School group not found.", extra={}).http_response()

    data = SchoolGroupResponse.model_validate(group).model_dump(mode="json")
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="School group fetched successfully.", extra=data).http_response()


@school_group_router.put(
    "/update_group/{group_id}", summary="Update a school group",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "School group updated successfully.", "result": {"school_group_id": 1, "school_id": 1, "group_name": "Higher Secondary", "status": "active"}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "School group not found.", "result": {}}}}},
    },
)
async def update_school_group(group_id: int, payload: SchoolGroupUpdateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolGroup).where(SchoolGroup.school_group_id == group_id))
    group = result.scalar_one_or_none()
    if group is None:
        return Result(code=404, message="School group not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    await db.commit()
    await db.refresh(group)
    data = SchoolGroupResponse.model_validate(group).model_dump(mode="json")

    await cache.set(_group_key(group_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("school_groups:*")
    return Result(code=200, message="School group updated successfully.", extra=data).http_response()


@school_group_router.delete(
    "/delete_group/{group_id}", summary="Soft delete a school group and all its children",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "School group and all related records deleted successfully.", "result": {"school_group_id": 1}}}}},
        404: {"content": {"application/json": {"example": {"code": 404, "message": "School group not found.", "result": {}}}}},
    },
)
async def delete_school_group(group_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolGroup).where(SchoolGroup.school_group_id == group_id))
    group = result.scalar_one_or_none()
    if group is None:
        return Result(code=404, message="School group not found.", extra={}).http_response()

    class_ids = (await db.execute(select(SchoolStreamClass.class_id).where(SchoolStreamClass.school_group_id == group_id))).scalars().all()
    if class_ids:
        await db.execute(update(SchoolStreamClassSection).where(SchoolStreamClassSection.class_id.in_(class_ids)).values(status="inactive"))
        await db.execute(update(SchoolStreamSubject).where(SchoolStreamSubject.class_id.in_(class_ids)).values(status="inactive"))
        await db.execute(update(SchoolStreamClass).where(SchoolStreamClass.class_id.in_(class_ids)).values(status="inactive"))

    await db.execute(update(SchoolStream).where(SchoolStream.school_group_id == group_id).values(status="inactive"))
    group.status = "inactive"
    await db.commit()

    await cache.delete(_group_key(group_id))
    await cache.delete_pattern("school_groups:*")
    await cache.delete_pattern("school_stream:*")
    await cache.delete_pattern("school_stream_class:*")
    await cache.delete_pattern("school_stream_section:*")
    await cache.delete_pattern("school_stream_subject:*")
    await cache.delete_pattern("dropdown:*")
    return Result(code=200, message="School group and all related records deleted successfully.", extra={"school_group_id": group_id}).http_response()


@school_group_router.get(
    "/school-groups/all", summary="Dropdown: School Groups",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Dropdown fetched.", "result": [{"id": 1, "name": "Primary"}, {"id": 2, "name": "Secondary"}]}}}},
    },
)
async def dropdown_school_groups(school_id: int | None = Query(None), search: str | None = Query(None), db: AsyncSession = Depends(get_db)):
    search = clean_search(search)
    key = f"dropdown:school_groups:{school_id}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Dropdown fetched (cache).", extra=cached).http_response()

    stmt = select(SchoolGroup.school_group_id, SchoolGroup.group_name).where(SchoolGroup.status == "active")
    if school_id:
        stmt = stmt.where(SchoolGroup.school_id == school_id)
    if search:
        stmt = stmt.where(SchoolGroup.group_name.like(f"%{search}%"))
    stmt = stmt.order_by(SchoolGroup.group_name)

    rows = await db.execute(stmt)
    data = [{"school_group_id": r.school_group_id, "name": r.group_name} for r in rows.all()]
    if data:  # only cache when data exists
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Dropdown fetched.", extra=data).http_response()
