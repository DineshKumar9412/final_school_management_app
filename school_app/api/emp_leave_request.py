# api/emp_leave_request.py
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.session import get_db
from database.redis_cache import cache
from models.emp_leave_request_models import EmpLeaveRequest, LeaveTypeEnum, LeaveStatusEnum
from models.employee_models import Employee
from schemas.emp_leave_request_schemas import EmpLeaveRequestCreate, EmpLeaveRequestUpdate
from security.valid_session import valid_session
from response.result import Result
from datetime import date

emp_leave_router = APIRouter(tags=["EMPLOYEE LEAVE REQUEST"], dependencies=[Depends(valid_session)])

CACHE_TTL = 86400


# ─── helpers ──────────────────────────────────────────────────────────────────

def clean_search(s: str | None) -> str | None:
    if s is None:
        return None
    return s.strip().strip('"').strip("'").strip() or None


def _item_key(leave_id: int) -> str:
    return f"emp_leave_request:{leave_id}"


def _list_key(page, limit, search, emp_id, status, leave_type, from_dt, to_date) -> str:
    return f"emp_leave_request:list:{page}:{limit}:{search}:{emp_id}:{status}:{leave_type}:{from_dt}:{to_date}"


def _row_to_dict(r: EmpLeaveRequest, emp_name: str | None) -> dict:
    return {
        "id":             r.id,
        "emp_id":         r.emp_id,
        "emp_name":       emp_name,
        "reason":         r.reason,
        "from_dt":        r.from_dt.isoformat(),
        "to_date":        r.to_date.isoformat(),
        "type":           r.type.value if r.type else None,
        "status":         r.status.value if r.status else None,
        "has_attachment": r.attachments is not None,
        "created_at":     r.created_at.isoformat(),
        "updated_at":     r.updated_at.isoformat(),
    }


async def _get_emp_name(db: AsyncSession, emp_id: int | None) -> str | None:
    if not emp_id:
        return None
    row = (await db.execute(
        select(Employee.first_name, Employee.last_name).where(Employee.id == emp_id)
    )).one_or_none()
    return f"{row.first_name} {row.last_name}".strip() if row else None


_EXAMPLE = {
    "id": 1, "emp_id": 1, "emp_name": "John Doe",
    "reason": "Family function",
    "from_dt": "2024-08-15", "to_date": "2024-08-16",
    "type": "Full", "status": "Pending",
    "has_attachment": False,
    "created_at": "2024-01-01T10:00:00", "updated_at": "2024-01-01T10:00:00",
}
_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Leave request not found.", "result": {}}}}}


# ─── CREATE ───────────────────────────────────────────────────────────────────

@emp_leave_router.post(
    "/create",
    summary="Create an employee leave request (with optional attachment)",
    responses={
        201: {"content": {"application/json": {"example": {"code": 201, "message": "Leave request created successfully.", "result": _EXAMPLE}}}},
    },
)
async def create_leave_request(
    payload:    EmpLeaveRequestCreate,
    attachment: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    obj = EmpLeaveRequest(
        **payload.model_dump(),
        attachments=await attachment.read() if attachment else None,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    emp_name = await _get_emp_name(db, obj.emp_id)
    data = _row_to_dict(obj, emp_name)
    await cache.set(_item_key(obj.id), data, expire=CACHE_TTL)
    await cache.delete_pattern("emp_leave_request:list:*")
    return Result(code=201, message="Leave request created successfully.", extra=data).http_response()


# ─── LIST (paginated) ─────────────────────────────────────────────────────────

@emp_leave_router.get(
    "/list",
    summary="List all leave requests (paginated)",
    responses={
        200: {"content": {"application/json": {"example": {
            "code": 200, "message": "Leave requests fetched successfully.",
            "result": {"total": 2, "page": 1, "limit": 10, "data": [_EXAMPLE]},
        }}}},
    },
)
async def list_leave_requests(
    page:       int        = Query(1,    ge=1),
    limit:      int        = Query(10,   ge=1, le=100),
    search:     str | None = Query(None, description="Search by reason"),
    emp_id:     int | None = Query(None, description="Filter by employee ID"),
    status:     str | None = Query(None, description="Filter by status: Approved / Rejected / Pending"),
    leave_type: str | None = Query(None, description="Filter by type: Full / First Half / Second Half"),
    from_dt:    date | None = Query(None, description="Filter from date e.g. 2024-08-01"),
    to_date:    date | None = Query(None, description="Filter to date e.g. 2024-08-31"),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key    = _list_key(page, limit, search, emp_id, status, leave_type, from_dt, to_date)

    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Leave requests fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt   = select(EmpLeaveRequest)

    if emp_id is not None:
        stmt = stmt.where(EmpLeaveRequest.emp_id == emp_id)
    if status is not None:
        stmt = stmt.where(EmpLeaveRequest.status == status)
    if leave_type is not None:
        stmt = stmt.where(EmpLeaveRequest.type == leave_type)
    if from_dt is not None:
        stmt = stmt.where(EmpLeaveRequest.from_dt >= from_dt)
    if to_date is not None:
        stmt = stmt.where(EmpLeaveRequest.to_date <= to_date)
    if search:
        stmt = stmt.where(EmpLeaveRequest.reason.like(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await db.execute(
        stmt.order_by(EmpLeaveRequest.id.desc()).offset(offset).limit(limit)
    )).scalars().all()

    # batch-fetch employee names
    emp_ids = {r.emp_id for r in rows if r.emp_id}
    emp_map: dict[int, str] = {}
    if emp_ids:
        emp_rows = (await db.execute(
            select(Employee.id, Employee.first_name, Employee.last_name)
            .where(Employee.id.in_(emp_ids))
        )).all()
        emp_map = {r.id: f"{r.first_name} {r.last_name}".strip() for r in emp_rows}

    data = {
        "total": total, "page": page, "limit": limit,
        "data":  [_row_to_dict(r, emp_map.get(r.emp_id)) for r in rows],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Leave requests fetched successfully.", extra=data).http_response()


# ─── GET BY ID ────────────────────────────────────────────────────────────────

@emp_leave_router.get(
    "/get/{leave_id}",
    summary="Get a leave request by ID",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Leave request fetched successfully.", "result": _EXAMPLE}}}},
        404: _404,
    },
)
async def get_leave_request(leave_id: int, db: AsyncSession = Depends(get_db)):
    key    = _item_key(leave_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Leave request fetched successfully (cache).", extra=cached).http_response()

    obj = (await db.execute(select(EmpLeaveRequest).where(EmpLeaveRequest.id == leave_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Leave request not found.", extra={}).http_response()

    emp_name = await _get_emp_name(db, obj.emp_id)
    data = _row_to_dict(obj, emp_name)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Leave request fetched successfully.", extra=data).http_response()


# ─── GET ATTACHMENT ───────────────────────────────────────────────────────────

@emp_leave_router.get(
    "/attachment/{leave_id}",
    summary="Download leave request attachment (binary)",
    responses={
        200: {"content": {"application/octet-stream": {}}},
        404: _404,
    },
)
async def get_leave_attachment(leave_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(EmpLeaveRequest).where(EmpLeaveRequest.id == leave_id))).scalar_one_or_none()
    if obj is None or obj.attachments is None:
        return Result(code=404, message="Attachment not found.", extra={}).http_response()
    return Response(content=obj.attachments, media_type="application/octet-stream")


# ─── UPDATE ───────────────────────────────────────────────────────────────────

@emp_leave_router.put(
    "/update/{leave_id}",
    summary="Update a leave request",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Leave request updated successfully.", "result": _EXAMPLE}}}},
        404: _404,
    },
)
async def update_leave_request(
    leave_id:   int,
    payload:    EmpLeaveRequestUpdate,
    attachment: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    obj = (await db.execute(select(EmpLeaveRequest).where(EmpLeaveRequest.id == leave_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Leave request not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    if attachment is not None:
        obj.attachments = await attachment.read()

    await db.commit()
    await db.refresh(obj)

    emp_name = await _get_emp_name(db, obj.emp_id)
    data = _row_to_dict(obj, emp_name)
    await cache.set(_item_key(leave_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("emp_leave_request:list:*")
    return Result(code=200, message="Leave request updated successfully.", extra=data).http_response()


# ─── APPROVE / REJECT shortcuts ───────────────────────────────────────────────

@emp_leave_router.patch(
    "/approve/{leave_id}",
    summary="Approve a leave request",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Leave request approved.", "result": _EXAMPLE}}}},
        404: _404,
    },
)
async def approve_leave_request(leave_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(EmpLeaveRequest).where(EmpLeaveRequest.id == leave_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Leave request not found.", extra={}).http_response()

    obj.status = LeaveStatusEnum.approved
    await db.commit()
    await db.refresh(obj)

    emp_name = await _get_emp_name(db, obj.emp_id)
    data = _row_to_dict(obj, emp_name)
    await cache.set(_item_key(leave_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("emp_leave_request:list:*")
    return Result(code=200, message="Leave request approved.", extra=data).http_response()


@emp_leave_router.patch(
    "/reject/{leave_id}",
    summary="Reject a leave request",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Leave request rejected.", "result": _EXAMPLE}}}},
        404: _404,
    },
)
async def reject_leave_request(leave_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(EmpLeaveRequest).where(EmpLeaveRequest.id == leave_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Leave request not found.", extra={}).http_response()

    obj.status = LeaveStatusEnum.rejected
    await db.commit()
    await db.refresh(obj)

    emp_name = await _get_emp_name(db, obj.emp_id)
    data = _row_to_dict(obj, emp_name)
    await cache.set(_item_key(leave_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("emp_leave_request:list:*")
    return Result(code=200, message="Leave request rejected.", extra=data).http_response()


# ─── DELETE ───────────────────────────────────────────────────────────────────

@emp_leave_router.delete(
    "/delete/{leave_id}",
    summary="Delete a leave request",
    responses={
        200: {"content": {"application/json": {"example": {"code": 200, "message": "Leave request deleted successfully.", "result": {"id": 1}}}}},
        404: _404,
    },
)
async def delete_leave_request(leave_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(EmpLeaveRequest).where(EmpLeaveRequest.id == leave_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Leave request not found.", extra={}).http_response()

    await db.delete(obj)
    await db.commit()

    await cache.delete(_item_key(leave_id))
    await cache.delete_pattern("emp_leave_request:list:*")
    return Result(code=200, message="Leave request deleted successfully.", extra={"id": leave_id}).http_response()
