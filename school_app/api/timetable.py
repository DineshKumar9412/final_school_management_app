# api/timetable.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from database.session import get_db
from database.redis_cache import cache
from models.timetable_models import TimeTable
from models.school_stream_models import SchoolStreamClass, SchoolStreamClassSection, SchoolStreamSubject
from schemas.timetable_schemas import TimeTableCreate, TimeTableUpdate
from security.valid_session import valid_session
from response.result import Result
from typing import Optional
from datetime import date

timetable_router = APIRouter(
    tags=["TIMETABLE"],
    dependencies=[Depends(valid_session)],
)

CACHE_TTL = 86400

_TT_RESULT = {
    "id": 1, "class_id": 1, "section_id": 1, "school_id": 1,
    "school_group_id": 1, "subject_id": 1, "subject_name": "Math",
    "class_code": "10", "section_code": "A",
    "school_table_name": "2024-25 Timetable",
    "type": "W", "date": None,
    "start_time": "09:00:00", "start_ampm": "AM",
    "end_time": "10:00:00", "end_ampm": "AM",
    "duration": 60, "day": "Mon",
}
_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Timetable not found.", "result": {}}}}}


def _row_to_dict(t, class_code=None, section_code=None, subject_name=None) -> dict:
    return {
        "id":                t.id,
        "class_id":          t.class_id,
        "class_code":        class_code,
        "section_id":        t.section_id,
        "section_code":      section_code,
        "school_id":         t.school_id,
        "school_group_id":   t.school_group_id,
        "subject_id":        t.subject_id,
        "subject_name":      subject_name,
        "school_table_name": t.school_table_name,
        "type":              t.type,
        "date":              str(t.date) if t.date else None,
        "start_time":        str(t.start_time),
        "start_ampm":        t.start_ampm,
        "end_time":          str(t.end_time),
        "end_ampm":          t.end_ampm,
        "duration":          t.duration,
        "day":               t.day,
    }


def _joined_stmt():
    return (
        select(
            TimeTable,
            SchoolStreamClass.class_code,
            SchoolStreamClassSection.section_code,
            SchoolStreamSubject.subject_name,
        )
        .outerjoin(SchoolStreamClass,        TimeTable.class_id   == SchoolStreamClass.class_id)
        .outerjoin(SchoolStreamClassSection, TimeTable.section_id == SchoolStreamClassSection.section_id)
        .outerjoin(SchoolStreamSubject,      TimeTable.subject_id == SchoolStreamSubject.subject_id)
    )


# ══════════════════════════════════════════════
# CREATE
# ══════════════════════════════════════════════

@timetable_router.post(
    "/timetable/create",
    summary="Create a timetable entry",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Timetable created successfully.", "result": _TT_RESULT}}}},
    },
)
async def create_timetable(payload: TimeTableCreate, db: AsyncSession = Depends(get_db)):
    obj = TimeTable(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    row = (await db.execute(_joined_stmt().where(TimeTable.id == obj.id))).one()
    t, class_code, section_code, subject_name = row
    data = _row_to_dict(t, class_code, section_code, subject_name)

    await cache.delete_pattern("timetable:list:*")
    return Result(code=201, message="Timetable created successfully.", extra=data).http_response()


# ══════════════════════════════════════════════
# GET BY ID
# ══════════════════════════════════════════════

@timetable_router.get(
    "/timetable/get_id/{timetable_id}",
    summary="Get timetable by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Timetable fetched successfully.", "result": _TT_RESULT}}}},
        404: _404,
    },
)
async def get_timetable(timetable_id: int, db: AsyncSession = Depends(get_db)):
    key = f"timetable:{timetable_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Timetable fetched successfully (cache).", extra=cached).http_response()

    row = (await db.execute(_joined_stmt().where(TimeTable.id == timetable_id))).one_or_none()
    if not row:
        return Result(code=404, message="Timetable not found.", extra={}).http_response()

    t, class_code, section_code, subject_name = row
    data = _row_to_dict(t, class_code, section_code, subject_name)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Timetable fetched successfully.", extra=data).http_response()


# ══════════════════════════════════════════════
# LIST
# ══════════════════════════════════════════════

@timetable_router.get(
    "/timetable/list",
    summary="List timetables (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Timetables fetched successfully.", "result": {"total": 1, "page": 1, "limit": 10, "data": [_TT_RESULT]}}}}}
    },
)
async def list_timetables(
    school_id:       Optional[int] = Query(None),
    class_id:        Optional[int] = Query(None),
    section_id:      Optional[int] = Query(None),
    school_group_id: Optional[int] = Query(None),
    subject_id:      Optional[int] = Query(None),
    search:          Optional[str] = Query(None, description="Search by school_table_name, subject_name, day (Mon/Tue...), type (W/D), or date (YYYY-MM-DD)"),
    page:            int           = Query(1,  ge=1),
    limit:           int           = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    key = f"timetable:list:{school_id}:{class_id}:{section_id}:{school_group_id}:{subject_id}:{search}:{page}:{limit}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Timetables fetched successfully (cache).", extra=cached).http_response()

    stmt = _joined_stmt()
    if school_id:       stmt = stmt.where(TimeTable.school_id       == school_id)
    if class_id:        stmt = stmt.where(TimeTable.class_id        == class_id)
    if section_id:      stmt = stmt.where(TimeTable.section_id      == section_id)
    if school_group_id: stmt = stmt.where(TimeTable.school_group_id == school_group_id)
    if subject_id:      stmt = stmt.where(TimeTable.subject_id      == subject_id)

    if search:
        s = search.strip()
        # date format YYYY-MM-DD
        try:
            from datetime import date as _date
            parsed_date = _date.fromisoformat(s)
            stmt = stmt.where(TimeTable.date == parsed_date)
        except ValueError:
            # day match: Mon, Tue etc
            days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
            if s.lower() in days:
                stmt = stmt.where(TimeTable.day == s.capitalize()[:3])
            # type match: W or D
            elif s.upper() in {"W", "D"}:
                stmt = stmt.where(TimeTable.type == s.upper())
            # text search
            else:
                stmt = stmt.where(or_(
                    TimeTable.school_table_name.like(f"%{s}%"),
                    SchoolStreamSubject.subject_name.like(f"%{s}%"),
                ))

    total  = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    offset = (page - 1) * limit
    rows   = (await db.execute(stmt.order_by(TimeTable.id).offset(offset).limit(limit))).all()

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [_row_to_dict(t, cc, sc, sn) for t, cc, sc, sn in rows],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Timetables fetched successfully.", extra=data).http_response()


# ══════════════════════════════════════════════
# UPDATE
# ══════════════════════════════════════════════

@timetable_router.put(
    "/timetable/update/{timetable_id}",
    summary="Update a timetable entry",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Timetable updated successfully.", "result": _TT_RESULT}}}},
        404: _404,
    },
)
async def update_timetable(timetable_id: int, payload: TimeTableUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TimeTable).where(TimeTable.id == timetable_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return Result(code=404, message="Timetable not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()

    row = (await db.execute(_joined_stmt().where(TimeTable.id == timetable_id))).one()
    t, class_code, section_code, subject_name = row
    data = _row_to_dict(t, class_code, section_code, subject_name)

    await cache.delete(f"timetable:{timetable_id}")
    await cache.delete_pattern("timetable:list:*")
    return Result(code=200, message="Timetable updated successfully.", extra=data).http_response()


# ══════════════════════════════════════════════
# DELETE
# ══════════════════════════════════════════════

@timetable_router.delete(
    "/timetable/delete/{timetable_id}",
    summary="Delete a timetable entry",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Timetable deleted successfully.", "result": {"id": 1}}}}},
        404: _404,
    },
)
async def delete_timetable(timetable_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TimeTable).where(TimeTable.id == timetable_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return Result(code=404, message="Timetable not found.", extra={}).http_response()

    await db.delete(obj)
    await db.commit()

    await cache.delete(f"timetable:{timetable_id}")
    await cache.delete_pattern("timetable:list:*")
    return Result(code=200, message="Timetable deleted successfully.", extra={"id": timetable_id}).http_response()
