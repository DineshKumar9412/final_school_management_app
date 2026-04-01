# api/login.py
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.redis_cache import cache
from database.session import get_db
from models.auth_models import Session
from models.employee_models import Employee, Role
from response.result import Result
from schemas.auth_schemas import WebLoginRequest

login_router = APIRouter(tags=["SCHOOL AUTH"])

SESSION_TTL_HOURS = 24 * 3          # 3 days


# ── helpers ────────────────────────────────────────────────────────────────────

def verify_password(password: str, hashed: str) -> bool:
    return password == hashed


# ── web login ──────────────────────────────────────────────────────────────────

@login_router.post("/web/login/")
async def web_login(
    payload: WebLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Employee).where(
            Employee.mobile == payload.mobile,
            Employee.is_active == True,
        )
    )
    employee = result.scalar_one_or_none()

    if not employee or not employee.password:
        return Result(code=401, message="Invalid credentials").http_response()

    role_name = None
    if employee.role_id is not None:
        role_result = await db.execute(
            select(Role).where(Role.role_id == employee.role_id)
        )
        role = role_result.scalar_one_or_none()
        role_name = role.role_name if role else None

    if role_name != "admin":
        return Result(code=403, message="Admin only allowed").http_response()

    if not verify_password(payload.password, employee.password):
        return Result(code=401, message="Invalid credentials").http_response()
    
    user_id    = str(employee.id)
    role_str   = role_name                              
    client_key = str(uuid4())
    valid_till = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)

    old_result = await db.execute(
        select(Session).where(Session.user_id == user_id)
    )
    old_sessions = old_result.scalars().all()

    for old in old_sessions:
        await cache.delete(f"session:{old.client_key}")
        await db.delete(old)

    await db.flush()

    new_session = Session(
        user_id    = user_id,
        role       = role_str,
        client_key = client_key,
        valid_till = valid_till,
    )
    db.add(new_session)
    await db.commit()

    await cache.set(
        key    = f"session:{client_key}",
        value  = {
            "user_id"    : user_id,
            "role"       : role_str,
            "emp_id"     : employee.emp_id,
            "first_name" : employee.first_name,
            "last_name"  : employee.last_name,
        },
        expire = SESSION_TTL_HOURS * 3600,
    )

    response.set_cookie(
        key      = "client_key",
        value    = client_key,
        httponly = True,
        secure   = False,
        samesite = "lax",
        max_age  = SESSION_TTL_HOURS * 3600,
    )

    return Result(
        code    = 200,
        message = "Login successful",
        extra   = {
            "user_id"    : user_id,
            "name"       : f"{employee.first_name} {employee.last_name}",
            "role"       : role_str,
            "valid_till" : valid_till.isoformat(),
        },
    ).http_response()
