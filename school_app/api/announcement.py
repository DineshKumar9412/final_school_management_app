# api/announcement.py
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.session import get_db
from database.redis_cache import cache
from models.announcement_models import Announcement
from models.school_stream_models import SchoolStreamClass, SchoolStreamClassSection
from schemas.announcement_schemas import AnnouncementCreate, AnnouncementUpdate
from security.valid_session import valid_session
from response.result import Result

announcement_router = APIRouter(tags=["ANNOUNCEMENT"], dependencies=[Depends(valid_session)])

CACHE_TTL = 86400


# ─── helpers ──────────────────────────────────────────────────────────────────

def clean_search(s: str | None) -> str | None:
    if s is None:
        return None
    return s.strip().strip('"').strip("'").strip() or None


def _item_key(announcement_id: int) -> str:
    return f"announcement:{announcement_id}"


def _list_key(page: int, limit: int, search: str | None, class_id: int | None, section_id: int | None) -> str:
    return f"announcement:list:{page}:{limit}:{search}:{class_id}:{section_id}"


def _row_to_dict(a: Announcement, class_code: str | None, section_name: str | None) -> dict:
    return {
        "id":           a.id,
        "class_id":     a.class_id,
        "class_code":   class_code,
        "section_id":   a.section_id,
        "section_name": section_name,
        "title":        a.title,
        "description":  a.description,
        "has_file":     a.file is not None,
        "url":          a.url,
        "created_at":   a.created_at.isoformat(),
        "updated_at":   a.updated_at.isoformat(),
    }


async def _fetch_labels(db: AsyncSession, class_id: int | None, section_id: int | None):
    """Return (class_code, section_name) for a single announcement."""
    class_code   = None
    section_name = None
    if class_id:
        row = (await db.execute(
            select(SchoolStreamClass.class_code).where(SchoolStreamClass.class_id == class_id)
        )).scalar_one_or_none()
        class_code = row
    if section_id:
        row = (await db.execute(
            select(SchoolStreamClassSection.section_name).where(SchoolStreamClassSection.section_id == section_id)
        )).scalar_one_or_none()
        section_name = row
    return class_code, section_name


_EXAMPLE = {
    "id": 1, "class_id": 1, "class_code": "10",
    "section_id": 1, "section_name": "Rose",
    "title": "Parent-Teacher Meeting",
    "description": "PTM scheduled for all students of Class 10.",
    "has_file": False, "url": None,
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:00:00",
}
_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Announcement not found.", "result": {}}}}}


# ─── CREATE ───────────────────────────────────────────────────────────────────

@announcement_router.post(
    "/create",
    summary="Create an announcement (with optional file upload)",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Announcement created successfully.", "result": _EXAMPLE}}}},
    },
)
async def create_announcement(
    payload: AnnouncementCreate,
    file:    UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read() if file else None

    obj = Announcement(
        **payload.model_dump(),
        file=file_bytes,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    class_code, section_name = await _fetch_labels(db, obj.class_id, obj.section_id)
    data = _row_to_dict(obj, class_code, section_name)
    await cache.set(_item_key(obj.id), data, expire=CACHE_TTL)
    await cache.delete_pattern("announcement:list:*")
    return Result(code=201, message="Announcement created successfully.", extra=data).http_response()


# ─── LIST (paginated) ─────────────────────────────────────────────────────────

@announcement_router.get(
    "/list",
    summary="List all announcements (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200, "message": "Announcements fetched successfully.",
            "result": {"total": 2, "page": 1, "limit": 10, "data": [_EXAMPLE]},
        }}}},
    },
)
async def list_announcements(
    page:       int        = Query(1,    ge=1),
    limit:      int        = Query(10,   ge=1, le=100),
    search:     str | None = Query(None, description="Search by title"),
    class_id:   int | None = Query(None, description="Filter by class ID"),
    section_id: int | None = Query(None, description="Filter by section ID"),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key    = _list_key(page, limit, search, class_id, section_id)

    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Announcements fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt   = select(Announcement)

    if class_id is not None:
        stmt = stmt.where(Announcement.class_id == class_id)
    if section_id is not None:
        stmt = stmt.where(Announcement.section_id == section_id)
    if search:
        stmt = stmt.where(Announcement.title.like(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await db.execute(
        stmt.order_by(Announcement.id.desc()).offset(offset).limit(limit)
    )).scalars().all()

    # batch-fetch class_code and section_name
    class_ids   = {a.class_id   for a in rows if a.class_id}
    section_ids = {a.section_id for a in rows if a.section_id}

    class_map: dict[int, str] = {}
    section_map: dict[int, str] = {}

    if class_ids:
        c_rows = (await db.execute(
            select(SchoolStreamClass.class_id, SchoolStreamClass.class_code)
            .where(SchoolStreamClass.class_id.in_(class_ids))
        )).all()
        class_map = {r.class_id: r.class_code for r in c_rows}

    if section_ids:
        s_rows = (await db.execute(
            select(SchoolStreamClassSection.section_id, SchoolStreamClassSection.section_name)
            .where(SchoolStreamClassSection.section_id.in_(section_ids))
        )).all()
        section_map = {r.section_id: r.section_name for r in s_rows}

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            _row_to_dict(a, class_map.get(a.class_id), section_map.get(a.section_id))
            for a in rows
        ],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Announcements fetched successfully.", extra=data).http_response()


# ─── GET BY ID ────────────────────────────────────────────────────────────────

@announcement_router.get(
    "/get/{announcement_id}",
    summary="Get an announcement by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Announcement fetched successfully.", "result": _EXAMPLE}}}},
        404: _404,
    },
)
async def get_announcement(announcement_id: int, db: AsyncSession = Depends(get_db)):
    key    = _item_key(announcement_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Announcement fetched successfully (cache).", extra=cached).http_response()

    obj = (await db.execute(select(Announcement).where(Announcement.id == announcement_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Announcement not found.", extra={}).http_response()

    class_code, section_name = await _fetch_labels(db, obj.class_id, obj.section_id)
    data = _row_to_dict(obj, class_code, section_name)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Announcement fetched successfully.", extra=data).http_response()


# ─── GET FILE ─────────────────────────────────────────────────────────────────

@announcement_router.get(
    "/file/{announcement_id}",
    summary="Download announcement file (binary)",
    responses={
        200: {"content": {"application/octet-stream": {}}},
        404: _404,
    },
)
async def get_announcement_file(announcement_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Announcement).where(Announcement.id == announcement_id))).scalar_one_or_none()
    if obj is None or obj.file is None:
        return Result(code=404, message="File not found.", extra={}).http_response()
    return Response(content=obj.file, media_type="application/octet-stream")


# ─── UPDATE ───────────────────────────────────────────────────────────────────

@announcement_router.put(
    "/update/{announcement_id}",
    summary="Update an announcement",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Announcement updated successfully.", "result": _EXAMPLE}}}},
        404: _404,
    },
)
async def update_announcement(
    announcement_id: int,
    payload: AnnouncementUpdate,
    file:    UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    obj = (await db.execute(select(Announcement).where(Announcement.id == announcement_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Announcement not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    if file is not None:
        obj.file = await file.read()

    await db.commit()
    await db.refresh(obj)

    class_code, section_name = await _fetch_labels(db, obj.class_id, obj.section_id)
    data = _row_to_dict(obj, class_code, section_name)
    await cache.set(_item_key(announcement_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("announcement:list:*")
    return Result(code=200, message="Announcement updated successfully.", extra=data).http_response()


# ─── DELETE ───────────────────────────────────────────────────────────────────

@announcement_router.delete(
    "/delete/{announcement_id}",
    summary="Delete an announcement",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Announcement deleted successfully.", "result": {"id": 1}}}}},
        404: _404,
    },
)
async def delete_announcement(announcement_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Announcement).where(Announcement.id == announcement_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Announcement not found.", extra={}).http_response()

    await db.delete(obj)
    await db.commit()

    await cache.delete(_item_key(announcement_id))
    await cache.delete_pattern("announcement:list:*")
    return Result(code=200, message="Announcement deleted successfully.", extra={"id": announcement_id}).http_response()
