# api/school_group.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import get_db
from database.redis_cache import cache
from models.school_group_models import SchoolGroup
from schemas.school_group_schemas import (
    SchoolGroupCreateRequest,
    SchoolGroupUpdateRequest,
    SchoolGroupResponse,
)
from security.dependencies import validate_session
from response.result import Result

school_group_router = APIRouter(
    tags=["SCHOOL GROUP"],
    dependencies=[Depends(validate_session)],
)

CACHE_TTL = 300  # seconds

def _group_key(group_id: int) -> str:
    return f"school_group:{group_id}"

def _list_key(school_id: int | None) -> str:
    return f"school_groups:school:{school_id}" if school_id else "school_groups:all"


# ─────────────────────────────────────────────
# POST /school-group
# ─────────────────────────────────────────────

@school_group_router.post("", summary="Create a new school group")
async def create_school_group(
    payload: SchoolGroupCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        group = SchoolGroup(
            school_id=payload.school_id,
            group_name=payload.group_name,
            description=payload.description,
            start_date=payload.start_date,
            end_date=payload.end_date,
            validity_days=payload.validity_days,
            status=payload.status,
        )
        db.add(group)
        await db.flush()
        group_id = group.school_group_id

    result = await db.execute(
        select(SchoolGroup).where(SchoolGroup.school_group_id == group_id)
    )
    created = result.scalar_one()
    data = SchoolGroupResponse.model_validate(created).model_dump(mode="json")

    # Invalidate list caches
    await cache.delete_pattern("school_groups:*")

    return Result(
        code=201,
        message="School group created successfully.",
        extra=data,
    ).http_response()


# ─────────────────────────────────────────────
# GET /school-group
# ─────────────────────────────────────────────

@school_group_router.get("", summary="List all school groups")
async def list_school_groups(
    school_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    key = _list_key(school_id)

    cached = await cache.get(key)
    if cached is not None:
        return Result(
            code=200,
            message="School groups fetched successfully.",
            extra=cached,
        ).http_response()

    stmt = select(SchoolGroup)
    if school_id is not None:
        stmt = stmt.where(SchoolGroup.school_id == school_id)
    stmt = stmt.order_by(SchoolGroup.school_group_id)

    result = await db.execute(stmt)
    groups = result.scalars().all()
    data = {"groups": [SchoolGroupResponse.model_validate(g).model_dump(mode="json") for g in groups]}

    await cache.set(key, data, expire=CACHE_TTL)

    return Result(
        code=200,
        message="School groups fetched successfully.",
        extra=data,
    ).http_response()


# ─────────────────────────────────────────────
# GET /school-group/{group_id}
# ─────────────────────────────────────────────

@school_group_router.get("/{group_id}", summary="Get a school group by ID")
async def get_school_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
):
    key = _group_key(group_id)

    cached = await cache.get(key)
    if cached is not None:
        return Result(
            code=200,
            message="School group fetched successfully.",
            extra=cached,
        ).http_response()

    result = await db.execute(
        select(SchoolGroup).where(SchoolGroup.school_group_id == group_id)
    )
    group = result.scalar_one_or_none()

    if group is None:
        return Result(code=404, message="School group not found.", extra={}).http_response()

    data = SchoolGroupResponse.model_validate(group).model_dump(mode="json")
    await cache.set(key, data, expire=CACHE_TTL)

    return Result(
        code=200,
        message="School group fetched successfully.",
        extra=data,
    ).http_response()


# ─────────────────────────────────────────────
# PUT /school-group/{group_id}
# ─────────────────────────────────────────────

@school_group_router.put("/{group_id}", summary="Update a school group")
async def update_school_group(
    group_id: int,
    payload: SchoolGroupUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    check = await db.execute(
        select(SchoolGroup).where(SchoolGroup.school_group_id == group_id)
    )
    if check.scalar_one_or_none() is None:
        return Result(code=404, message="School group not found.", extra={}).http_response()

    async with db.begin():
        result = await db.execute(
            select(SchoolGroup).where(SchoolGroup.school_group_id == group_id)
        )
        group = result.scalar_one()

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(group, field, value)

    await db.refresh(group)
    data = SchoolGroupResponse.model_validate(group).model_dump(mode="json")

    # Refresh single cache, invalidate list caches
    await cache.set(_group_key(group_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("school_groups:*")

    return Result(
        code=200,
        message="School group updated successfully.",
        extra=data,
    ).http_response()


# ─────────────────────────────────────────────
# DELETE /school-group/{group_id}
# ─────────────────────────────────────────────

@school_group_router.delete("/{group_id}", summary="Delete a school group")
async def delete_school_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
):
    check = await db.execute(
        select(SchoolGroup).where(SchoolGroup.school_group_id == group_id)
    )
    if check.scalar_one_or_none() is None:
        return Result(code=404, message="School group not found.", extra={}).http_response()

    async with db.begin():
        result = await db.execute(
            select(SchoolGroup).where(SchoolGroup.school_group_id == group_id)
        )
        group = result.scalar_one()
        await db.delete(group)

    # Invalidate single and list caches
    await cache.delete(_group_key(group_id))
    await cache.delete_pattern("school_groups:*")

    return Result(
        code=200,
        message="School group deleted successfully.",
        extra={"school_group_id": group_id},
    ).http_response()
