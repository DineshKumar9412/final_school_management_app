# api/notification.py
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.session import get_db
from database.redis_cache import cache
from models.notification_models import Notification
from models.employee_models import Role
from schemas.notification_schemas import NotificationCreate, NotificationUpdate
from security.valid_session import valid_session
from response.result import Result

notification_router = APIRouter(tags=["NOTIFICATION"], dependencies=[Depends(valid_session)])

CACHE_TTL = 86400


# ─── helpers ──────────────────────────────────────────────────────────────────

def clean_search(s: str | None) -> str | None:
    if s is None:
        return None
    return s.strip().strip('"').strip("'").strip() or None


def _item_key(notification_id: int) -> str:
    return f"notification:{notification_id}"


def _list_key(page: int, limit: int, search: str | None, role_id: int | None) -> str:
    return f"notification:list:{page}:{limit}:{search}:{role_id}"


def _row_to_dict(n: Notification, role_name: str | None) -> dict:
    return {
        "id":         n.id,
        "title":      n.title,
        "message":    n.message,
        "role_id":    n.role_id,
        "role_name":  role_name,
        "has_image":  n.image is not None,
        "created_at": n.created_at.isoformat(),
        "updated_at": n.updated_at.isoformat(),
    }


_EXAMPLE = {
    "id": 1,
    "title": "School Closed",
    "message": "School will remain closed tomorrow.",
    "role_id": 1,
    "role_name": "Teacher",
    "has_image": False,
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:00:00",
}
_LIST_EXAMPLE = {
    "code": 200, "message": "Notifications fetched successfully.",
    "result": {
        "total": 1, "page": 1, "limit": 10,
        "data": [_EXAMPLE],
    }
}
_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Notification not found.", "result": {}}}}}


# ─── CREATE ───────────────────────────────────────────────────────────────────

@notification_router.post(
    "/create",
    summary="Create a notification (with optional image)",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Notification created successfully.", "result": _EXAMPLE}}}},
        409: {"content": {"application/json": {"example": {"code": 409, "message": "Notification with this title already exists for this role.", "result": {}}}}},
    },
)
async def create_notification(
    title:   str            = Form(..., max_length=100),
    message: str | None     = Form(None),
    role_id: int | None     = Form(None),
    image:   UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    exists = (await db.execute(
        select(Notification.id).where(
            Notification.title   == title,
            Notification.role_id == role_id,
        )
    )).scalar_one_or_none()
    if exists:
        return Result(code=409, message="Notification with this title already exists for this role.", extra={}).http_response()

    image_bytes = await image.read() if image else None

    obj = Notification(
        title=title,
        message=message,
        role_id=role_id,
        image=image_bytes,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    role_name = None
    if obj.role_id:
        role = (await db.execute(select(Role).where(Role.role_id == obj.role_id))).scalar_one_or_none()
        role_name = role.role_name if role else None

    data = _row_to_dict(obj, role_name)
    await cache.set(_item_key(obj.id), data, expire=CACHE_TTL)
    await cache.delete_pattern("notification:list:*")
    return Result(code=201, message="Notification created successfully.", extra=data).http_response()


# ─── LIST (paginated) ─────────────────────────────────────────────────────────

@notification_router.get(
    "/list",
    summary="List all notifications (paginated)",
    responses={
        200: {"content": {"application/json": {"example": _LIST_EXAMPLE}}},
    },
)
async def list_notifications(
    page:    int        = Query(1,    ge=1),
    limit:   int        = Query(10,   ge=1, le=100),
    search:  str | None = Query(None, description="Search by title"),
    role_id: int | None = Query(None, description="Filter by role ID"),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key    = _list_key(page, limit, search, role_id)

    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Notifications fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit

    stmt = select(Notification)
    if role_id is not None:
        stmt = stmt.where(Notification.role_id == role_id)
    if search:
        stmt = stmt.where(Notification.title.like(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await db.execute(
        stmt.order_by(Notification.id.desc()).offset(offset).limit(limit)
    )).scalars().all()

    # batch-fetch role names
    role_ids = {n.role_id for n in rows if n.role_id}
    role_map: dict[int, str] = {}
    if role_ids:
        roles = (await db.execute(
            select(Role).where(Role.role_id.in_(role_ids))
        )).scalars().all()
        role_map = {r.role_id: r.role_name for r in roles}

    data = {
        "total": total, "page": page, "limit": limit,
        "data":  [_row_to_dict(n, role_map.get(n.role_id)) for n in rows],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Notifications fetched successfully.", extra=data).http_response()


# ─── GET BY ID ────────────────────────────────────────────────────────────────

@notification_router.get(
    "/get/{notification_id}",
    summary="Get a notification by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Notification fetched successfully.", "result": _EXAMPLE}}}},
        404: _404,
    },
)
async def get_notification(notification_id: int, db: AsyncSession = Depends(get_db)):
    key    = _item_key(notification_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Notification fetched successfully (cache).", extra=cached).http_response()

    obj = (await db.execute(select(Notification).where(Notification.id == notification_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Notification not found.", extra={}).http_response()

    role_name = None
    if obj.role_id:
        role = (await db.execute(select(Role).where(Role.role_id == obj.role_id))).scalar_one_or_none()
        role_name = role.role_name if role else None

    data = _row_to_dict(obj, role_name)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Notification fetched successfully.", extra=data).http_response()


# ─── GET IMAGE ────────────────────────────────────────────────────────────────

@notification_router.get(
    "/image/{notification_id}",
    summary="Get notification image (binary)",
    responses={
        200: {"content": {"image/*": {}}},
        404: _404,
    },
)
async def get_notification_image(notification_id: int, db: AsyncSession = Depends(get_db)):
    from fastapi.responses import Response
    obj = (await db.execute(select(Notification).where(Notification.id == notification_id))).scalar_one_or_none()
    if obj is None or obj.image is None:
        return Result(code=404, message="Image not found.", extra={}).http_response()
    return Response(content=obj.image, media_type="image/jpeg")


# ─── UPDATE ───────────────────────────────────────────────────────────────────

@notification_router.put(
    "/update/{notification_id}",
    summary="Update a notification",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Notification updated successfully.", "result": _EXAMPLE}}}},
        404: _404,
    },
)
async def update_notification(
    notification_id: int,
    title:   str | None     = Form(None, max_length=100),
    message: str | None     = Form(None),
    role_id: int | None     = Form(None),
    image:   UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    obj = (await db.execute(select(Notification).where(Notification.id == notification_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Notification not found.", extra={}).http_response()

    if title   is not None: obj.title   = title
    if message is not None: obj.message = message
    if role_id is not None: obj.role_id = role_id
    if image   is not None: obj.image   = await image.read()

    await db.commit()
    await db.refresh(obj)

    role_name = None
    if obj.role_id:
        role = (await db.execute(select(Role).where(Role.role_id == obj.role_id))).scalar_one_or_none()
        role_name = role.role_name if role else None

    data = _row_to_dict(obj, role_name)
    await cache.set(_item_key(notification_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("notification:list:*")
    return Result(code=200, message="Notification updated successfully.", extra=data).http_response()


# ─── DELETE ───────────────────────────────────────────────────────────────────

@notification_router.delete(
    "/delete/{notification_id}",
    summary="Delete a notification",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Notification deleted successfully.", "result": {"id": 1}}}}},
        404: _404,
    },
)
async def delete_notification(notification_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Notification).where(Notification.id == notification_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Notification not found.", extra={}).http_response()

    await db.delete(obj)
    await db.commit()

    await cache.delete(_item_key(notification_id))
    await cache.delete_pattern("notification:list:*")
    return Result(code=200, message="Notification deleted successfully.", extra={"id": notification_id}).http_response()
