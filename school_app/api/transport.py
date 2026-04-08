# api/transport.py
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.session import get_db
from database.redis_cache import cache
from models.transport_models import VehicleDetails, Routes, VehicleRoutesMap, TransportationStudent, VehicleExpenses
from models.school_stream_models import SchoolStreamClass, SchoolStreamClassSection, SchoolGroup
from models.student_models import Student
from schemas.transport_schemas import (
    VehicleDetailsCreate, VehicleDetailsUpdate,
    RoutesCreate, RoutesUpdate,
    VehicleRoutesMapCreate, VehicleRoutesMapUpdate,
    TransportationStudentCreate, TransportationStudentUpdate,
    VehicleExpensesCreate, VehicleExpensesUpdate,
)
from security.valid_session import valid_session
from response.result import Result

transport_router = APIRouter(tags=["TRANSPORT"], dependencies=[Depends(valid_session)])

CACHE_TTL = 86400


# ─── shared helper ────────────────────────────────────────────────────────────

def clean_search(s: str | None) -> str | None:
    if s is None:
        return None
    return s.strip().strip('"').strip("'").strip() or None


# ══════════════════════════════════════════════════════════════════════════════
# VEHICLE DETAILS
# ══════════════════════════════════════════════════════════════════════════════

def _vd_key(vid: int)  -> str: return f"vehicle_details:{vid}"
def _vd_list_key(page, limit, search, status) -> str:
    return f"vehicle_details:list:{page}:{limit}:{search}:{status}"

def _vd_to_dict(v: VehicleDetails) -> dict:
    return {
        "id": v.id, "vehicle_no": v.vehicle_no,
        "vehicle_capacity": v.vehicle_capacity, "vehicle_reg_no": v.vehicle_reg_no,
        "status": v.status, "driver_mob_no": v.driver_mob_no,
        "helper_mob_no": v.helper_mob_no,
        "created_at": v.created_at.isoformat(), "updated_at": v.updated_at.isoformat(),
    }

_VD_EX = {"id": 1, "vehicle_no": "TN01AB1234", "vehicle_capacity": 40,
           "vehicle_reg_no": "REG001", "status": "A",
           "driver_mob_no": "9876543210", "helper_mob_no": "9876543211",
           "created_at": "2024-01-01T10:00:00", "updated_at": "2024-01-01T10:00:00"}
_VD_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Vehicle not found.", "result": {}}}}}


@transport_router.post("/vehicle/create", summary="Create a vehicle",
    responses={201: {"content": {"application/json": {"example": {"code": 201, "message": "Vehicle created successfully.", "result": _VD_EX}}}}})
async def create_vehicle(payload: VehicleDetailsCreate, db: AsyncSession = Depends(get_db)):
    obj = VehicleDetails(**payload.model_dump())
    db.add(obj); await db.commit(); await db.refresh(obj)
    data = _vd_to_dict(obj)
    await cache.set(_vd_key(obj.id), data, expire=CACHE_TTL)
    await cache.delete_pattern("vehicle_details:list:*")
    return Result(code=201, message="Vehicle created successfully.", extra=data).http_response()


@transport_router.get("/vehicle/list", summary="List vehicles (paginated)",
    responses={200: {"content": {"application/json": {"example": {"code": 200, "message": "Vehicles fetched successfully.", "result": {"total": 1, "page": 1, "limit": 10, "data": [_VD_EX]}}}}}})
async def list_vehicles(
    page:   int        = Query(1,  ge=1),
    limit:  int        = Query(10, ge=1, le=100),
    search: str | None = Query(None, description="Search by vehicle_no or vehicle_reg_no"),
    status: str | None = Query(None, description="Filter by status e.g. A / I"),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key    = _vd_list_key(page, limit, search, status)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Vehicles fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt   = select(VehicleDetails)
    if status:
        stmt = stmt.where(VehicleDetails.status == status)
    if search:
        stmt = stmt.where(
            VehicleDetails.vehicle_no.like(f"%{search}%") |
            VehicleDetails.vehicle_reg_no.like(f"%{search}%")
        )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await db.execute(stmt.order_by(VehicleDetails.id.desc()).offset(offset).limit(limit))).scalars().all()
    data  = {"total": total, "page": page, "limit": limit, "data": [_vd_to_dict(v) for v in rows]}
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Vehicles fetched successfully.", extra=data).http_response()


@transport_router.get("/vehicle/get/{vehicle_id}", summary="Get vehicle by ID", responses={404: _VD_404})
async def get_vehicle(vehicle_id: int, db: AsyncSession = Depends(get_db)):
    key = _vd_key(vehicle_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Vehicle fetched successfully (cache).", extra=cached).http_response()
    obj = (await db.execute(select(VehicleDetails).where(VehicleDetails.id == vehicle_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Vehicle not found.", extra={}).http_response()
    data = _vd_to_dict(obj)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Vehicle fetched successfully.", extra=data).http_response()


@transport_router.put("/vehicle/update/{vehicle_id}", summary="Update a vehicle", responses={404: _VD_404})
async def update_vehicle(vehicle_id: int, payload: VehicleDetailsUpdate, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(VehicleDetails).where(VehicleDetails.id == vehicle_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Vehicle not found.", extra={}).http_response()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit(); await db.refresh(obj)
    data = _vd_to_dict(obj)
    await cache.set(_vd_key(vehicle_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("vehicle_details:list:*")
    return Result(code=200, message="Vehicle updated successfully.", extra=data).http_response()


@transport_router.delete("/vehicle/delete/{vehicle_id}", summary="Delete a vehicle", responses={404: _VD_404})
async def delete_vehicle(vehicle_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(VehicleDetails).where(VehicleDetails.id == vehicle_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Vehicle not found.", extra={}).http_response()
    await db.delete(obj); await db.commit()
    await cache.delete(_vd_key(vehicle_id))
    await cache.delete_pattern("vehicle_details:list:*")
    return Result(code=200, message="Vehicle deleted successfully.", extra={"id": vehicle_id}).http_response()


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

def _rt_key(rid: int) -> str: return f"routes:{rid}"
def _rt_list_key(page, limit, search, status) -> str:
    return f"routes:list:{page}:{limit}:{search}:{status}"

def _rt_to_dict(r: Routes) -> dict:
    return {
        "id": r.id, "name": r.name, "vehicle_no": r.vehicle_no,
        "distance": r.distance, "status": r.status,
        "pick_start_time":  str(r.pick_start_time),
        "pick_end_time":    str(r.pick_end_time),
        "drop_start_time":  str(r.drop_start_time),
        "drop_end_time":    str(r.drop_end_time),
        "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat(),
    }

_RT_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Route not found.", "result": {}}}}}


@transport_router.post("/route/create", summary="Create a route",
    responses={201: {"content": {"application/json": {"example": {"code": 201, "message": "Route created successfully."}}}}})
async def create_route(payload: RoutesCreate, db: AsyncSession = Depends(get_db)):
    obj = Routes(**payload.model_dump())
    db.add(obj); await db.commit(); await db.refresh(obj)
    data = _rt_to_dict(obj)
    await cache.set(_rt_key(obj.id), data, expire=CACHE_TTL)
    await cache.delete_pattern("routes:list:*")
    return Result(code=201, message="Route created successfully.", extra=data).http_response()


@transport_router.get("/route/list", summary="List routes (paginated)")
async def list_routes(
    page:   int        = Query(1,  ge=1),
    limit:  int        = Query(10, ge=1, le=100),
    search: str | None = Query(None, description="Search by route name"),
    status: str | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    search = clean_search(search)
    key    = _rt_list_key(page, limit, search, status)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Routes fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt   = select(Routes)
    if status:
        stmt = stmt.where(Routes.status == status)
    if search:
        stmt = stmt.where(Routes.name.like(f"%{search}%"))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await db.execute(stmt.order_by(Routes.id.desc()).offset(offset).limit(limit))).scalars().all()
    data  = {"total": total, "page": page, "limit": limit, "data": [_rt_to_dict(r) for r in rows]}
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Routes fetched successfully.", extra=data).http_response()


@transport_router.get("/route/get/{route_id}", summary="Get route by ID", responses={404: _RT_404})
async def get_route(route_id: int, db: AsyncSession = Depends(get_db)):
    key = _rt_key(route_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Route fetched successfully (cache).", extra=cached).http_response()
    obj = (await db.execute(select(Routes).where(Routes.id == route_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Route not found.", extra={}).http_response()
    data = _rt_to_dict(obj)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Route fetched successfully.", extra=data).http_response()


@transport_router.put("/route/update/{route_id}", summary="Update a route", responses={404: _RT_404})
async def update_route(route_id: int, payload: RoutesUpdate, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Routes).where(Routes.id == route_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Route not found.", extra={}).http_response()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit(); await db.refresh(obj)
    data = _rt_to_dict(obj)
    await cache.set(_rt_key(route_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("routes:list:*")
    return Result(code=200, message="Route updated successfully.", extra=data).http_response()


@transport_router.delete("/route/delete/{route_id}", summary="Delete a route", responses={404: _RT_404})
async def delete_route(route_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Routes).where(Routes.id == route_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Route not found.", extra={}).http_response()
    await db.delete(obj); await db.commit()
    await cache.delete(_rt_key(route_id))
    await cache.delete_pattern("routes:list:*")
    return Result(code=200, message="Route deleted successfully.", extra={"id": route_id}).http_response()


# ══════════════════════════════════════════════════════════════════════════════
# VEHICLE ROUTES MAP
# ══════════════════════════════════════════════════════════════════════════════

def _vrm_key(mid: int) -> str: return f"vehicle_routes_map:{mid}"
def _vrm_list_key(page, limit, route_id, vehicle_id) -> str:
    return f"vehicle_routes_map:list:{page}:{limit}:{route_id}:{vehicle_id}"

def _vrm_to_dict(m: VehicleRoutesMap, route_name: str | None, vehicle_no: str | None) -> dict:
    return {
        "id": m.id, "route_id": m.route_id, "route_name": route_name,
        "vehicle_id": m.vehicle_id, "vehicle_no": vehicle_no,
        "driver_name": m.driver_name, "helper_name": m.helper_name,
        "driver_mob_no": m.driver_mob_no, "helper_mob_no": m.helper_mob_no,
        "created_at": m.created_at.isoformat(), "updated_at": m.updated_at.isoformat(),
    }

async def _vrm_labels(db, route_id, vehicle_id):
    route_name = vehicle_no = None
    if route_id:
        row = (await db.execute(select(Routes.name).where(Routes.id == route_id))).scalar_one_or_none()
        route_name = row
    if vehicle_id:
        row = (await db.execute(select(VehicleDetails.vehicle_no).where(VehicleDetails.id == vehicle_id))).scalar_one_or_none()
        vehicle_no = row
    return route_name, vehicle_no

_VRM_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Vehicle route map not found.", "result": {}}}}}


@transport_router.post("/vehicle_route_map/create", summary="Create a vehicle-route mapping",
    responses={201: {"content": {"application/json": {"example": {"code": 201, "message": "Mapping created successfully."}}}}})
async def create_vehicle_route_map(payload: VehicleRoutesMapCreate, db: AsyncSession = Depends(get_db)):
    obj = VehicleRoutesMap(**payload.model_dump())
    db.add(obj); await db.commit(); await db.refresh(obj)
    route_name, vehicle_no = await _vrm_labels(db, obj.route_id, obj.vehicle_id)
    data = _vrm_to_dict(obj, route_name, vehicle_no)
    await cache.set(_vrm_key(obj.id), data, expire=CACHE_TTL)
    await cache.delete_pattern("vehicle_routes_map:list:*")
    return Result(code=201, message="Mapping created successfully.", extra=data).http_response()


@transport_router.get("/vehicle_route_map/list", summary="List vehicle-route mappings (paginated)")
async def list_vehicle_route_maps(
    page:       int        = Query(1,  ge=1),
    limit:      int        = Query(10, ge=1, le=100),
    route_id:   int | None = Query(None, description="Filter by route ID"),
    vehicle_id: int | None = Query(None, description="Filter by vehicle ID"),
    db: AsyncSession = Depends(get_db),
):
    key = _vrm_list_key(page, limit, route_id, vehicle_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Mappings fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt   = select(VehicleRoutesMap)
    if route_id:
        stmt = stmt.where(VehicleRoutesMap.route_id == route_id)
    if vehicle_id:
        stmt = stmt.where(VehicleRoutesMap.vehicle_id == vehicle_id)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await db.execute(stmt.order_by(VehicleRoutesMap.id.desc()).offset(offset).limit(limit))).scalars().all()

    # batch labels
    r_ids = {m.route_id   for m in rows if m.route_id}
    v_ids = {m.vehicle_id for m in rows if m.vehicle_id}
    route_map   = {}
    vehicle_map = {}
    if r_ids:
        r_rows = (await db.execute(select(Routes.id, Routes.name).where(Routes.id.in_(r_ids)))).all()
        route_map = {r.id: r.name for r in r_rows}
    if v_ids:
        v_rows = (await db.execute(select(VehicleDetails.id, VehicleDetails.vehicle_no).where(VehicleDetails.id.in_(v_ids)))).all()
        vehicle_map = {v.id: v.vehicle_no for v in v_rows}

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [_vrm_to_dict(m, route_map.get(m.route_id), vehicle_map.get(m.vehicle_id)) for m in rows],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Mappings fetched successfully.", extra=data).http_response()


@transport_router.get("/vehicle_route_map/get/{map_id}", summary="Get vehicle-route map by ID", responses={404: _VRM_404})
async def get_vehicle_route_map(map_id: int, db: AsyncSession = Depends(get_db)):
    key = _vrm_key(map_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Mapping fetched successfully (cache).", extra=cached).http_response()
    obj = (await db.execute(select(VehicleRoutesMap).where(VehicleRoutesMap.id == map_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Vehicle route map not found.", extra={}).http_response()
    route_name, vehicle_no = await _vrm_labels(db, obj.route_id, obj.vehicle_id)
    data = _vrm_to_dict(obj, route_name, vehicle_no)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Mapping fetched successfully.", extra=data).http_response()


@transport_router.put("/vehicle_route_map/update/{map_id}", summary="Update a vehicle-route mapping", responses={404: _VRM_404})
async def update_vehicle_route_map(map_id: int, payload: VehicleRoutesMapUpdate, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(VehicleRoutesMap).where(VehicleRoutesMap.id == map_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Vehicle route map not found.", extra={}).http_response()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit(); await db.refresh(obj)
    route_name, vehicle_no = await _vrm_labels(db, obj.route_id, obj.vehicle_id)
    data = _vrm_to_dict(obj, route_name, vehicle_no)
    await cache.set(_vrm_key(map_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("vehicle_routes_map:list:*")
    return Result(code=200, message="Mapping updated successfully.", extra=data).http_response()


@transport_router.delete("/vehicle_route_map/delete/{map_id}", summary="Delete a vehicle-route mapping", responses={404: _VRM_404})
async def delete_vehicle_route_map(map_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(VehicleRoutesMap).where(VehicleRoutesMap.id == map_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Vehicle route map not found.", extra={}).http_response()
    await db.delete(obj); await db.commit()
    await cache.delete(_vrm_key(map_id))
    await cache.delete_pattern("vehicle_routes_map:list:*")
    return Result(code=200, message="Mapping deleted successfully.", extra={"id": map_id}).http_response()


# ══════════════════════════════════════════════════════════════════════════════
# TRANSPORTATION STUDENT
# ══════════════════════════════════════════════════════════════════════════════

def _ts_key(tid: int) -> str: return f"transportation_student:{tid}"
def _ts_list_key(page, limit, vehicle_id, class_id, section_id, student_id, group_id, session_yr) -> str:
    return f"transportation_student:list:{page}:{limit}:{vehicle_id}:{class_id}:{section_id}:{student_id}:{group_id}:{session_yr}"

def _ts_to_dict(t: TransportationStudent, vehicle_no, class_code, section_name, student_name, group_name) -> dict:
    return {
        "id": t.id,
        "vehicle_id": t.vehicle_id, "vehicle_no": vehicle_no,
        "class_id":   t.class_id,   "class_code": class_code,
        "section_id": t.section_id, "section_name": section_name,
        "student_id": t.student_id, "student_name": student_name,
        "group_id":   t.group_id,   "group_name": group_name,
        "session_yr": t.session_yr,
        "created_at": t.created_at.isoformat(), "updated_at": t.updated_at.isoformat(),
    }

_TS_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Transportation student not found.", "result": {}}}}}


@transport_router.post("/transportation_student/create", summary="Assign student to vehicle",
    responses={201: {"content": {"application/json": {"example": {"code": 201, "message": "Transportation student created successfully."}}}}})
async def create_transportation_student(payload: TransportationStudentCreate, db: AsyncSession = Depends(get_db)):
    obj = TransportationStudent(**payload.model_dump())
    db.add(obj); await db.commit(); await db.refresh(obj)

    vehicle_no = class_code = section_name = student_name = group_name = None
    if obj.vehicle_id:
        vehicle_no = (await db.execute(select(VehicleDetails.vehicle_no).where(VehicleDetails.id == obj.vehicle_id))).scalar_one_or_none()
    if obj.class_id:
        class_code = (await db.execute(select(SchoolStreamClass.class_code).where(SchoolStreamClass.class_id == obj.class_id))).scalar_one_or_none()
    if obj.section_id:
        section_name = (await db.execute(select(SchoolStreamClassSection.section_name).where(SchoolStreamClassSection.section_id == obj.section_id))).scalar_one_or_none()
    if obj.student_id:
        row = (await db.execute(select(Student.first_name, Student.last_name).where(Student.student_id == obj.student_id))).one_or_none()
        student_name = f"{row.first_name} {row.last_name}".strip() if row else None
    if obj.group_id:
        group_name = (await db.execute(select(SchoolGroup.group_name).where(SchoolGroup.school_group_id == obj.group_id))).scalar_one_or_none()

    data = _ts_to_dict(obj, vehicle_no, class_code, section_name, student_name, group_name)
    await cache.set(_ts_key(obj.id), data, expire=CACHE_TTL)
    await cache.delete_pattern("transportation_student:list:*")
    return Result(code=201, message="Transportation student created successfully.", extra=data).http_response()


@transport_router.get("/transportation_student/list", summary="List transportation students (paginated)")
async def list_transportation_students(
    page:       int        = Query(1,  ge=1),
    limit:      int        = Query(10, ge=1, le=100),
    vehicle_id: int | None = Query(None),
    class_id:   int | None = Query(None),
    section_id: int | None = Query(None),
    student_id: int | None = Query(None),
    group_id:   int | None = Query(None),
    session_yr: str | None = Query(None, description="Filter by session year e.g. 2024-25"),
    db: AsyncSession = Depends(get_db),
):
    key = _ts_list_key(page, limit, vehicle_id, class_id, section_id, student_id, group_id, session_yr)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Transportation students fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt   = select(TransportationStudent)
    if vehicle_id:  stmt = stmt.where(TransportationStudent.vehicle_id  == vehicle_id)
    if class_id:    stmt = stmt.where(TransportationStudent.class_id    == class_id)
    if section_id:  stmt = stmt.where(TransportationStudent.section_id  == section_id)
    if student_id:  stmt = stmt.where(TransportationStudent.student_id  == student_id)
    if group_id:    stmt = stmt.where(TransportationStudent.group_id    == group_id)
    if session_yr:  stmt = stmt.where(TransportationStudent.session_yr  == session_yr)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await db.execute(stmt.order_by(TransportationStudent.id.desc()).offset(offset).limit(limit))).scalars().all()

    # batch labels
    v_ids   = {t.vehicle_id  for t in rows if t.vehicle_id}
    c_ids   = {t.class_id    for t in rows if t.class_id}
    sec_ids = {t.section_id  for t in rows if t.section_id}
    s_ids   = {t.student_id  for t in rows if t.student_id}
    g_ids   = {t.group_id    for t in rows if t.group_id}

    v_map = s_map = c_map = sec_map = g_map = {}
    if v_ids:
        v_map = {r.id: r.vehicle_no for r in (await db.execute(select(VehicleDetails.id, VehicleDetails.vehicle_no).where(VehicleDetails.id.in_(v_ids)))).all()}
    if c_ids:
        c_map = {r.class_id: r.class_code for r in (await db.execute(select(SchoolStreamClass.class_id, SchoolStreamClass.class_code).where(SchoolStreamClass.class_id.in_(c_ids)))).all()}
    if sec_ids:
        sec_map = {r.section_id: r.section_name for r in (await db.execute(select(SchoolStreamClassSection.section_id, SchoolStreamClassSection.section_name).where(SchoolStreamClassSection.section_id.in_(sec_ids)))).all()}
    if s_ids:
        s_map = {r.student_id: f"{r.first_name} {r.last_name}".strip() for r in (await db.execute(select(Student.student_id, Student.first_name, Student.last_name).where(Student.student_id.in_(s_ids)))).all()}
    if g_ids:
        g_map = {r.school_group_id: r.group_name for r in (await db.execute(select(SchoolGroup.school_group_id, SchoolGroup.group_name).where(SchoolGroup.school_group_id.in_(g_ids)))).all()}

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [_ts_to_dict(t, v_map.get(t.vehicle_id), c_map.get(t.class_id), sec_map.get(t.section_id), s_map.get(t.student_id), g_map.get(t.group_id)) for t in rows],
    }
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Transportation students fetched successfully.", extra=data).http_response()


@transport_router.get("/transportation_student/get/{ts_id}", summary="Get transportation student by ID", responses={404: _TS_404})
async def get_transportation_student(ts_id: int, db: AsyncSession = Depends(get_db)):
    key = _ts_key(ts_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Transportation student fetched successfully (cache).", extra=cached).http_response()
    obj = (await db.execute(select(TransportationStudent).where(TransportationStudent.id == ts_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Transportation student not found.", extra={}).http_response()

    vehicle_no = class_code = section_name = student_name = group_name = None
    if obj.vehicle_id:
        vehicle_no = (await db.execute(select(VehicleDetails.vehicle_no).where(VehicleDetails.id == obj.vehicle_id))).scalar_one_or_none()
    if obj.class_id:
        class_code = (await db.execute(select(SchoolStreamClass.class_code).where(SchoolStreamClass.class_id == obj.class_id))).scalar_one_or_none()
    if obj.section_id:
        section_name = (await db.execute(select(SchoolStreamClassSection.section_name).where(SchoolStreamClassSection.section_id == obj.section_id))).scalar_one_or_none()
    if obj.student_id:
        row = (await db.execute(select(Student.first_name, Student.last_name).where(Student.student_id == obj.student_id))).one_or_none()
        student_name = f"{row.first_name} {row.last_name}".strip() if row else None
    if obj.group_id:
        group_name = (await db.execute(select(SchoolGroup.group_name).where(SchoolGroup.school_group_id == obj.group_id))).scalar_one_or_none()

    data = _ts_to_dict(obj, vehicle_no, class_code, section_name, student_name, group_name)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Transportation student fetched successfully.", extra=data).http_response()


@transport_router.put("/transportation_student/update/{ts_id}", summary="Update transportation student", responses={404: _TS_404})
async def update_transportation_student(ts_id: int, payload: TransportationStudentUpdate, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(TransportationStudent).where(TransportationStudent.id == ts_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Transportation student not found.", extra={}).http_response()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit(); await db.refresh(obj)

    vehicle_no = class_code = section_name = student_name = group_name = None
    if obj.vehicle_id:
        vehicle_no = (await db.execute(select(VehicleDetails.vehicle_no).where(VehicleDetails.id == obj.vehicle_id))).scalar_one_or_none()
    if obj.class_id:
        class_code = (await db.execute(select(SchoolStreamClass.class_code).where(SchoolStreamClass.class_id == obj.class_id))).scalar_one_or_none()
    if obj.section_id:
        section_name = (await db.execute(select(SchoolStreamClassSection.section_name).where(SchoolStreamClassSection.section_id == obj.section_id))).scalar_one_or_none()
    if obj.student_id:
        row = (await db.execute(select(Student.first_name, Student.last_name).where(Student.student_id == obj.student_id))).one_or_none()
        student_name = f"{row.first_name} {row.last_name}".strip() if row else None
    if obj.group_id:
        group_name = (await db.execute(select(SchoolGroup.group_name).where(SchoolGroup.school_group_id == obj.group_id))).scalar_one_or_none()

    data = _ts_to_dict(obj, vehicle_no, class_code, section_name, student_name, group_name)
    await cache.set(_ts_key(ts_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("transportation_student:list:*")
    return Result(code=200, message="Transportation student updated successfully.", extra=data).http_response()


@transport_router.delete("/transportation_student/delete/{ts_id}", summary="Delete transportation student", responses={404: _TS_404})
async def delete_transportation_student(ts_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(TransportationStudent).where(TransportationStudent.id == ts_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Transportation student not found.", extra={}).http_response()
    await db.delete(obj); await db.commit()
    await cache.delete(_ts_key(ts_id))
    await cache.delete_pattern("transportation_student:list:*")
    return Result(code=200, message="Transportation student deleted successfully.", extra={"id": ts_id}).http_response()


# ══════════════════════════════════════════════════════════════════════════════
# VEHICLE EXPENSES
# ══════════════════════════════════════════════════════════════════════════════

def _ve_key(eid: int) -> str: return f"vehicle_expenses:{eid}"
def _ve_list_key(page, limit, vehicle_id, session_yr) -> str:
    return f"vehicle_expenses:list:{page}:{limit}:{vehicle_id}:{session_yr}"

def _ve_to_dict(e: VehicleExpenses, vehicle_no: str | None) -> dict:
    return {
        "id": e.id, "vehicle_id": e.vehicle_id, "vehicle_no": vehicle_no,
        "session_yr": e.session_yr,
        "amount": str(e.amount) if e.amount is not None else None,
        "date": e.date.isoformat() if e.date else None,
        "has_image": e.image is not None,
        "description": e.description,
        "created_at": e.created_at.isoformat(), "updated_at": e.updated_at.isoformat(),
    }

_VE_404 = {"content": {"application/json": {"example": {"code": 404, "message": "Vehicle expense not found.", "result": {}}}}}


@transport_router.post("/vehicle_expense/create", summary="Create a vehicle expense (with optional image)",
    responses={201: {"content": {"application/json": {"example": {"code": 201, "message": "Vehicle expense created successfully."}}}}})
async def create_vehicle_expense(
    payload: VehicleExpensesCreate,
    image:   UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    obj = VehicleExpenses(**payload.model_dump(), image=await image.read() if image else None)
    db.add(obj); await db.commit(); await db.refresh(obj)
    vehicle_no = (await db.execute(select(VehicleDetails.vehicle_no).where(VehicleDetails.id == obj.vehicle_id))).scalar_one_or_none() if obj.vehicle_id else None
    data = _ve_to_dict(obj, vehicle_no)
    await cache.set(_ve_key(obj.id), data, expire=CACHE_TTL)
    await cache.delete_pattern("vehicle_expenses:list:*")
    return Result(code=201, message="Vehicle expense created successfully.", extra=data).http_response()


@transport_router.get("/vehicle_expense/list", summary="List vehicle expenses (paginated)")
async def list_vehicle_expenses(
    page:       int        = Query(1,  ge=1),
    limit:      int        = Query(10, ge=1, le=100),
    vehicle_id: int | None = Query(None, description="Filter by vehicle ID"),
    session_yr: str | None = Query(None, description="Filter by session year e.g. 2024-25"),
    db: AsyncSession = Depends(get_db),
):
    key = _ve_list_key(page, limit, vehicle_id, session_yr)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Vehicle expenses fetched successfully (cache).", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt   = select(VehicleExpenses)
    if vehicle_id:  stmt = stmt.where(VehicleExpenses.vehicle_id == vehicle_id)
    if session_yr:  stmt = stmt.where(VehicleExpenses.session_yr == session_yr)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await db.execute(stmt.order_by(VehicleExpenses.id.desc()).offset(offset).limit(limit))).scalars().all()

    v_ids = {e.vehicle_id for e in rows if e.vehicle_id}
    v_map = {}
    if v_ids:
        v_map = {r.id: r.vehicle_no for r in (await db.execute(select(VehicleDetails.id, VehicleDetails.vehicle_no).where(VehicleDetails.id.in_(v_ids)))).all()}

    data = {"total": total, "page": page, "limit": limit, "data": [_ve_to_dict(e, v_map.get(e.vehicle_id)) for e in rows]}
    if total > 0:
        await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Vehicle expenses fetched successfully.", extra=data).http_response()


@transport_router.get("/vehicle_expense/get/{expense_id}", summary="Get vehicle expense by ID", responses={404: _VE_404})
async def get_vehicle_expense(expense_id: int, db: AsyncSession = Depends(get_db)):
    key = _ve_key(expense_id)
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Vehicle expense fetched successfully (cache).", extra=cached).http_response()
    obj = (await db.execute(select(VehicleExpenses).where(VehicleExpenses.id == expense_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Vehicle expense not found.", extra={}).http_response()
    vehicle_no = (await db.execute(select(VehicleDetails.vehicle_no).where(VehicleDetails.id == obj.vehicle_id))).scalar_one_or_none() if obj.vehicle_id else None
    data = _ve_to_dict(obj, vehicle_no)
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Vehicle expense fetched successfully.", extra=data).http_response()


@transport_router.get("/vehicle_expense/image/{expense_id}", summary="Get vehicle expense image (binary)")
async def get_vehicle_expense_image(expense_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(VehicleExpenses).where(VehicleExpenses.id == expense_id))).scalar_one_or_none()
    if obj is None or obj.image is None:
        return Result(code=404, message="Image not found.", extra={}).http_response()
    return Response(content=obj.image, media_type="image/jpeg")


@transport_router.put("/vehicle_expense/update/{expense_id}", summary="Update a vehicle expense", responses={404: _VE_404})
async def update_vehicle_expense(
    expense_id: int,
    payload: VehicleExpensesUpdate,
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    obj = (await db.execute(select(VehicleExpenses).where(VehicleExpenses.id == expense_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Vehicle expense not found.", extra={}).http_response()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    if image:
        obj.image = await image.read()
    await db.commit(); await db.refresh(obj)
    vehicle_no = (await db.execute(select(VehicleDetails.vehicle_no).where(VehicleDetails.id == obj.vehicle_id))).scalar_one_or_none() if obj.vehicle_id else None
    data = _ve_to_dict(obj, vehicle_no)
    await cache.set(_ve_key(expense_id), data, expire=CACHE_TTL)
    await cache.delete_pattern("vehicle_expenses:list:*")
    return Result(code=200, message="Vehicle expense updated successfully.", extra=data).http_response()


@transport_router.delete("/vehicle_expense/delete/{expense_id}", summary="Delete a vehicle expense", responses={404: _VE_404})
async def delete_vehicle_expense(expense_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(VehicleExpenses).where(VehicleExpenses.id == expense_id))).scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Vehicle expense not found.", extra={}).http_response()
    await db.delete(obj); await db.commit()
    await cache.delete(_ve_key(expense_id))
    await cache.delete_pattern("vehicle_expenses:list:*")
    return Result(code=200, message="Vehicle expense deleted successfully.", extra={"id": expense_id}).http_response()
