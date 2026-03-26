# api/school_group.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import get_db
from models.school_group_models import SchoolGroup
from schemas.school_group_schemas import (
    SchoolGroupCreateRequest,
    SchoolGroupUpdateRequest,
    SchoolGroupResponse,
)
from response.result import Result

school_group_router = APIRouter(tags=["SCHOOL GROUP"])


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

    return Result(
        code=201,
        message="School group created successfully.",
        extra=SchoolGroupResponse.model_validate(created).model_dump(mode="json"),
    ).http_response()


@school_group_router.get("", summary="List all school groups")
async def list_school_groups(
    school_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SchoolGroup)
    if school_id is not None:
        stmt = stmt.where(SchoolGroup.school_id == school_id)
    stmt = stmt.order_by(SchoolGroup.school_group_id)

    result = await db.execute(stmt)
    groups = result.scalars().all()

    return Result(
        code=200,
        message="School groups fetched successfully.",
        extra={"groups": [SchoolGroupResponse.model_validate(g).model_dump(mode="json") for g in groups]},
    ).http_response()


@school_group_router.get("/{group_id}", summary="Get a school group by ID")
async def get_school_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SchoolGroup).where(SchoolGroup.school_group_id == group_id)
    )
    group = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(status_code=404, detail="School group not found.")

    return Result(
        code=200,
        message="School group fetched successfully.",
        extra=SchoolGroupResponse.model_validate(group).model_dump(mode="json"),
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
    async with db.begin():
        result = await db.execute(
            select(SchoolGroup).where(SchoolGroup.school_group_id == group_id)
        )
        group = result.scalar_one_or_none()

        if group is None:
            raise HTTPException(status_code=404, detail="School group not found.")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(group, field, value)

    await db.refresh(group)

    return Result(
        code=200,
        message="School group updated successfully.",
        extra=SchoolGroupResponse.model_validate(group).model_dump(mode="json"),
    ).http_response()

@school_group_router.delete("/{group_id}", summary="Delete a school group")
async def delete_school_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        result = await db.execute(
            select(SchoolGroup).where(SchoolGroup.school_group_id == group_id)
        )
        group = result.scalar_one_or_none()

        if group is None:
            raise HTTPException(status_code=404, detail="School group not found.")

        await db.delete(group)

    return Result(
        code=200,
        message="School group deleted successfully.",
        extra={"school_group_id": group_id},
    ).http_response()
