# api/holiday.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.session import get_db
from database.redis_cache import cache
from models.holiday_models import Holiday
from schemas.holiday_schemas import HolidayCreate, HolidayUpdate
from security.valid_session import valid_session
from response.result import Result
from datetime import date

holiday_router = APIRouter(tags=["HOLIDAY"], dependencies=[Depends(valid_session)])

CACHE_TTL = 86400


# ─── helpers ──────────────────────────────────────────────────────────────────

def clean_search(s: str | None) -> str | None:
    if s is None:
        return None
    return s.strip().strip('"').strip("'").strip() or None


def _item_key(holiday_id: int) -> str:
    return f"holiday:{holiday_id}"


def _list_key(page: int, limit: int, search: str | None, year: int | None, month: int | None) -> str:
    return f"holiday:list:{page}:{limit}:{search}:{year}:{month}"


def _row_to_dict(h: Holiday) -> dict:
    return {
        "id":           h.id,
        "holiday_date": h.holiday_date.isoformat(),
        "title":        h.title,
        "description":  h.description,
        "created_at":   h.created_at.isoformat(),
        "updated_at":   h.updated_at.isoformat(),
    }


_EXAMPLE = {
    "id": 1, "holiday_date": "2024-08-15",
    "title": "Independence Day",
    "description": "National holiday.",
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:00:00",
}
_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Holiday not found.", "result": {}}}}}


# ─── CREATE ───────────────────────────────────────────────────────────────────

@holiday_router.post(
    "/create",
    summary="Create a holiday",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Holiday created successfully.", "result": _EXAMPLE}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Holiday 'Independence Day' on 2024-08-15 already exists.", "result": {}}}}},
    },
)
async def create_holiday(payload: HolidayCreate, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(
        select(Holiday.id).where(
            Holiday.holiday_date == payload.holiday_date,
            Holiday.title        == payload.title,
        )
    )).scalar_one_or_none()
    if exists:
        return Result(code=409, message=f"Holiday '{payload.title}' on {payload.holiday_date} already exists.", extra={}).http_response()

    obj = Holiday(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    data = _row_to_dict(obj)
    await cache.set(_item_key(obj.id), data, expire=CACHE_TTL)
    await cache.delete_pattern("holiday:list:*")
    return Result(code=201, message="Holiday created successfully.", extra=data).http_response()


# ─── LIST (paginated) ─────────────────────────────────────────────────────────

@holiday_router.get(
    "/list",
    summary="List all holidays (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200, "message": "Holidays fetched successfully.",
            "result": {"total": 2, "page": 1, "limit": 10, "data": [_EXAMPLE]},
        }}}},
    },
)
async def list_holidays(
    page:   int        = Query(1,    ge=1),
    limit:  int        = Query(10,   ge=1, le=100),
    search: str | None = Query(None, description="Search by title"),
    year:   int | None = Query(None, description="Filter by year  e.g. 2024"),
    month:  int | None = Query(None, ge=1, le=12, description="Filter by month e.g. 8"),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key    = _list_key(page, limit, search, year, month)

    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Holidays fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt   = select(Holiday)

    if search:
        stmt = stmt.where(Holiday.title.like(f"%{search}%"))
    if year:
        stmt = stmt.where(func.year(Holiday.holiday_date) == year)
    if month:
        stmt = stmt.where(func.month(Holiday.holiday_date) == month)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await db.execute(
        stmt.order_by(Holiday.holiday_date).offset(offset).limit(limit)
    )).scalars().all()

    data = {
        "total": total, "page": page, "limit": limit,
        "data":  [_row_to_dict(h) for h in rows],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Holidays fetched successfully.", extra=data).http_response()


# ─── GET BY ID ────────────────────────────────────────────────────────────────

@holiday_router.get(
    "/get/{holiday_id}",
    summary="Get a holiday by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Holiday fetched successfully.", "result": _EXAMPLE}}}},
        404: _404,
    },
)
async def get_holiday(holiday_id: int, db: AsyncSession = Depends(get_db)):
    key    = _item_key(holiday_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Holiday fetched successfully (cache).", extra=cached).http_response()

    obj = (await db.execute(select(Holiday).where(Holiday.id == holiday_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Holiday not found.", extra={}).http_response()

    data = _row_to_dict(obj)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Holiday fetched successfully.", extra=data).http_response()


# ─── UPDATE ───────────────────────────────────────────────────────────────────

@holiday_router.put(
    "/update/{holiday_id}",
    summary="Update a holiday",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Holiday updated successfully.", "result": _EXAMPLE}}}},
        404: _404,
    },
)
async def update_holiday(holiday_id: int, payload: HolidayUpdate, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Holiday).where(Holiday.id == holiday_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Holiday not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)

    data = _row_to_dict(obj)
    await cache.set(_item_key(holiday_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("holiday:list:*")
    return Result(code=200, message="Holiday updated successfully.", extra=data).http_response()


# ─── DELETE ───────────────────────────────────────────────────────────────────

@holiday_router.delete(
    "/delete/{holiday_id}",
    summary="Delete a holiday",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Holiday deleted successfully.", "result": {"id": 1}}}}},
        404: _404,
    },
)
async def delete_holiday(holiday_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Holiday).where(Holiday.id == holiday_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Holiday not found.", extra={}).http_response()

    await db.delete(obj)
    await db.commit()

    await cache.delete(_item_key(holiday_id))
    await cache.delete_pattern("holiday:list:*")
    return Result(code=200, message="Holiday deleted successfully.", extra={"id": holiday_id}).http_response()
