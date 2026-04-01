# api/employee.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update

from database.session import get_db
from database.redis_cache import cache
from models.employee_models import Role, Employee, EmployeeClassMapping
from models.school_stream_models import SchoolStreamClass, SchoolStreamSubject
from schemas.employee_schemas import (
    RoleCreate,
    RoleUpdate,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeMappingCreate,
    EmployeeMappingUpdate,
)
from response.result import Result

employee_router = APIRouter(tags=["EMPLOYEE"])

CACHE_TTL = 86400
STATUS_VALUES = {"active", "inactive"}

EMPLOYEE_ALLOWED_UPDATE_FIELDS = {
    "role_id", "first_name", "last_name", "DOB", "gender",
    "qualification", "mobile", "address", "email",
    "salary", "session_yr", "joining_dt", "status", "is_active",
}

# ─── CREATE ROLE ──────────────────────────────

@employee_router.post("/role/create", summary="Create a new role")
async def create_role(payload: RoleCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(Role.role_id).where(Role.role_name == payload.role_name)
    )
    if exists.scalar_one_or_none():
        return Result(code=409, message=f"Role '{payload.role_name}' already exists.", extra={}).http_response()

    obj = Role(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    await cache.delete("roles:all")
    return Result(code=201, message="Role created successfully.", extra={
        "role_id": obj.role_id, "role_name": obj.role_name
    }).http_response()


# ─── GET ALL ROLES ────────────────────────────

@employee_router.get("/role/list", summary="List all roles")
async def list_roles(db: AsyncSession = Depends(get_db)):
    cached = await cache.get("roles:all")
    if cached:
        return Result(code=200, message="Roles fetched successfully.", extra=cached).http_response()

    rows = (await db.execute(select(Role).where(Role.is_active == True).order_by(Role.role_id))).scalars().all()
    data = [{"role_id": r.role_id, "role_name": r.role_name, "is_active": r.is_active} for r in rows]

    await cache.set("roles:all", data, expire=CACHE_TTL)
    return Result(code=200, message="Roles fetched successfully.", extra=data).http_response()


# ─── UPDATE ROLE ──────────────────────────────

@employee_router.put("/role/update/{role_id}", summary="Update a role")
async def update_role(role_id: int, payload: RoleUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Role).where(Role.role_id == role_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Role not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)

    await cache.delete("roles:all")
    return Result(code=200, message="Role updated successfully.", extra={
        "role_id": obj.role_id, "role_name": obj.role_name
    }).http_response()


# ══════════════════════════════════════════════
# EMPLOYEE
# ══════════════════════════════════════════════

def _emp_row_to_dict(emp, role_name=None) -> dict:
    return {
        "id":            emp.id,
        "emp_id":        emp.emp_id,
        "role_id":       emp.role_id,
        "role_name":     role_name,
        "first_name":    emp.first_name,
        "last_name":     emp.last_name,
        "gender":        emp.gender,
        "mobile":        emp.mobile,
        "email":         emp.email,
        "qualification": emp.qualification,
        "status":        emp.status,
        "is_active":     emp.is_active,
        "joining_dt":    str(emp.joining_dt) if emp.joining_dt else None,
    }


# ─── CREATE EMPLOYEE ──────────────────────────

@employee_router.post("/employee/create", summary="Create a new employee")
async def create_employee(payload: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    # duplicate check by emp_id
    if payload.emp_id:
        exists = await db.execute(
            select(Employee.id).where(Employee.emp_id == payload.emp_id)
        )
        if exists.scalar_one_or_none():
            return Result(code=409, message=f"Employee with emp_id '{payload.emp_id}' already exists.", extra={}).http_response()

    obj = Employee(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    await cache.delete_pattern("employee:list:*")
    await cache.delete_pattern("employee:dropdown:*")
    return Result(code=201, message="Employee created successfully.", extra={
        "id": obj.id, "emp_id": obj.emp_id, "first_name": obj.first_name,
    }).http_response()


# ─── GET EMPLOYEE BY ID ───────────────────────

@employee_router.get("/employee/get_id/{emp_db_id}", summary="Get employee by DB ID")
async def get_employee(emp_db_id: int, db: AsyncSession = Depends(get_db)):
    key = f"employee:{emp_db_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Employee fetched successfully.", extra=cached).http_response()

    stmt = (
        select(Employee, Role.role_name)
        .outerjoin(Role, Employee.role_id == Role.role_id)
        .where(Employee.id == emp_db_id)
    )
    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        return Result(code=404, message="Employee not found.", extra={}).http_response()

    emp, role_name = row
    data = _emp_row_to_dict(emp, role_name)
    # include full details
    data.update({
        "DOB":          str(emp.DOB) if emp.DOB else None,
        "address":      emp.address,
        "salary":       float(emp.salary) if emp.salary else None,
        "session_yr":   emp.session_yr,
    })

    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Employee fetched successfully.", extra=data).http_response()


# ─── GET EMPLOYEE LIST (paginated) ────────────

@employee_router.get("/employee/list", summary="List employees (paginated)")
async def list_employees(
    page:      int          = Query(1,    ge=1),
    limit:     int          = Query(10,   ge=1, le=100),
    search:    str | None   = Query(None, description="Search by name, mobile, email, or type 'active'/'inactive'"),
    role_id:   int | None   = Query(None),
    db: AsyncSession = Depends(get_db),
):
    key = f"employee:list:{page}:{limit}:{search}:{role_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Employees fetched successfully.", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt = (
        select(Employee, Role.role_name)
        .outerjoin(Role, Employee.role_id == Role.role_id)
    )

    if role_id is not None:
        stmt = stmt.where(Employee.role_id == role_id)

    if search is not None and search.lower() in STATUS_VALUES:
        stmt = stmt.where(Employee.is_active == (search.lower() == "active"))
    elif search is not None:
        stmt = stmt.where(or_(
            Employee.first_name.like(f"%{search}%"),
            Employee.last_name.like(f"%{search}%"),
            Employee.mobile.like(f"%{search}%"),
            Employee.email.like(f"%{search}%"),
        ))
    else:
        stmt = stmt.where(Employee.is_active == True)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await db.execute(stmt.order_by(Employee.id.desc()).offset(offset).limit(limit))

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [_emp_row_to_dict(emp, role_name) for emp, role_name in rows.all()],
    }
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Employees fetched successfully.", extra=data).http_response()


# ─── GET EMPLOYEE DROPDOWN ────────────────────

@employee_router.get("/employee/all", summary="Dropdown: Employees")
async def dropdown_employees(
    role_id: int | None = Query(None),
    search:  str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    key = f"employee:dropdown:{role_id}:{search}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Dropdown fetched.", extra=cached).http_response()

    stmt = select(Employee.id, Employee.emp_id, Employee.first_name, Employee.last_name).where(Employee.is_active == True)
    if role_id:
        stmt = stmt.where(Employee.role_id == role_id)
    if search:
        stmt = stmt.where(or_(
            Employee.first_name.like(f"%{search}%"),
            Employee.last_name.like(f"%{search}%"),
        ))

    rows = await db.execute(stmt.order_by(Employee.first_name))
    data = [
        {"id": r.id, "emp_id": r.emp_id, "name": f"{r.first_name} {r.last_name}".strip()}
        for r in rows.all()
    ]
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Dropdown fetched.", extra=data).http_response()


# ─── UPDATE EMPLOYEE ──────────────────────────

@employee_router.put("/employee/update/{emp_db_id}", summary="Update employee")
async def update_employee(emp_db_id: int, payload: EmployeeUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employee).where(Employee.id == emp_db_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Employee not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in EMPLOYEE_ALLOWED_UPDATE_FIELDS:
            setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)

    await cache.delete(f"employee:{emp_db_id}")
    await cache.delete_pattern("employee:list:*")
    await cache.delete_pattern("employee:dropdown:*")
    return Result(code=200, message="Employee updated successfully.", extra={
        "id": obj.id, "emp_id": obj.emp_id, "first_name": obj.first_name,
    }).http_response()


# ─── DELETE EMPLOYEE (soft) ───────────────────

@employee_router.delete("/employee/delete/{emp_db_id}", summary="Soft delete employee")
async def delete_employee(emp_db_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employee).where(Employee.id == emp_db_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Employee not found.", extra={}).http_response()

    obj.is_active = False
    await db.commit()

    await cache.delete(f"employee:{emp_db_id}")
    await cache.delete_pattern("employee:list:*")
    await cache.delete_pattern("employee:dropdown:*")
    return Result(code=200, message="Employee deleted successfully.", extra={"id": emp_db_id}).http_response()


# ══════════════════════════════════════════════
# EMPLOYEE CLASS MAPPING
# ══════════════════════════════════════════════

# ─── CREATE MAPPING ───────────────────────────

@employee_router.post("/employee/mapping/create", summary="Assign employee to class + subject")
async def create_mapping(payload: EmployeeMappingCreate, db: AsyncSession = Depends(get_db)):
    # verify employee exists
    emp = (await db.execute(select(Employee.id).where(Employee.id == payload.emp_id))).scalar_one_or_none()
    if emp is None:
        return Result(code=404, message="Employee not found.", extra={}).http_response()

    # duplicate check
    exists = await db.execute(
        select(EmployeeClassMapping.map_id).where(
            EmployeeClassMapping.emp_id == payload.emp_id,
            EmployeeClassMapping.class_id == payload.class_id,
            EmployeeClassMapping.subject_id == payload.subject_id,
        )
    )
    if exists.scalar_one_or_none():
        return Result(code=409, message="Mapping already exists for this employee, class, and subject.", extra={}).http_response()

    obj = EmployeeClassMapping(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    await cache.delete_pattern("emp_mapping:list:*")
    return Result(code=201, message="Employee mapping created successfully.", extra={
        "map_id": obj.map_id, "emp_id": obj.emp_id,
        "class_id": obj.class_id, "subject_id": obj.subject_id,
    }).http_response()


# ─── GET MAPPING LIST ─────────────────────────

@employee_router.get("/employee/mapping/list", summary="List employee class mappings (paginated)")
async def list_mappings(
    page:       int        = Query(1,    ge=1),
    limit:      int        = Query(10,   ge=1, le=100),
    emp_id:     int | None = Query(None),
    class_id:   int | None = Query(None),
    subject_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    key = f"emp_mapping:list:{page}:{limit}:{emp_id}:{class_id}:{subject_id}"
    cached = await cache.get(key)
    if cached:
        return Result(code=200, message="Mappings fetched successfully.", extra=cached).http_response()

    offset = (page - 1) * limit
    stmt = (
        select(
            EmployeeClassMapping.map_id,
            EmployeeClassMapping.emp_id,
            EmployeeClassMapping.class_id,
            EmployeeClassMapping.subject_id,
            Employee.first_name,
            Employee.last_name,
            Employee.emp_id.label("employee_emp_id"),
            SchoolStreamClass.class_code,
            SchoolStreamSubject.subject_name,
        )
        .join(Employee,          EmployeeClassMapping.emp_id     == Employee.id)
        .join(SchoolStreamClass, EmployeeClassMapping.class_id   == SchoolStreamClass.class_id)
        .join(SchoolStreamSubject, EmployeeClassMapping.subject_id == SchoolStreamSubject.subject_id)
    )

    if emp_id is not None:
        stmt = stmt.where(EmployeeClassMapping.emp_id == emp_id)
    if class_id is not None:
        stmt = stmt.where(EmployeeClassMapping.class_id == class_id)
    if subject_id is not None:
        stmt = stmt.where(EmployeeClassMapping.subject_id == subject_id)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await db.execute(stmt.order_by(EmployeeClassMapping.map_id.desc()).offset(offset).limit(limit))

    data = {
        "total": total, "page": page, "limit": limit,
        "data": [
            {
                "map_id":       r.map_id,
                "emp_id":       r.emp_id,
                "employee_emp_id": r.employee_emp_id,
                "emp_name":     f"{r.first_name} {r.last_name}".strip(),
                "class_id":     r.class_id,
                "class_code":   r.class_code,
                "subject_id":   r.subject_id,
                "subject_name": r.subject_name,
            }
            for r in rows.all()
        ],
    }
    await cache.set(key, data, expire=CACHE_TTL)
    return Result(code=200, message="Mappings fetched successfully.", extra=data).http_response()


# ─── UPDATE MAPPING ───────────────────────────

@employee_router.put("/employee/mapping/update/{map_id}", summary="Update employee mapping")
async def update_mapping(map_id: int, payload: EmployeeMappingUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmployeeClassMapping).where(EmployeeClassMapping.map_id == map_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Mapping not found.", extra={}).http_response()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()

    await cache.delete_pattern("emp_mapping:list:*")
    return Result(code=200, message="Mapping updated successfully.", extra={
        "map_id": obj.map_id, "class_id": obj.class_id, "subject_id": obj.subject_id,
    }).http_response()


# ─── DELETE MAPPING ───────────────────────────

@employee_router.delete("/employee/mapping/delete/{map_id}", summary="Delete employee mapping")
async def delete_mapping(map_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmployeeClassMapping).where(EmployeeClassMapping.map_id == map_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return Result(code=404, message="Mapping not found.", extra={}).http_response()

    await db.delete(obj)
    await db.commit()

    await cache.delete_pattern("emp_mapping:list:*")
    return Result(code=200, message="Mapping deleted successfully.", extra={"map_id": map_id}).http_response()
