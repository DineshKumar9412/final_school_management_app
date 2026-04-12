# api/profile.py
from fastapi import APIRouter, Cookie, Depends, Header, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.redis_cache import cache
from database.session import get_db
from models.auth_models import Session
from models.employee_models import Employee
from response.result import Result
from security.valid_session import valid_session

profile_router = APIRouter(tags=["SCHOOL AUTH"])


@profile_router.get("/profile/")
async def get_profile(
    session: Session = Depends(valid_session),
    db: AsyncSession = Depends(get_db),
):
    
    if not session.user_id:
        return Result(code=401, message="Session missing user info.").http_response()

    result = await db.execute(
        select(Employee).where(
            Employee.id == int(session.user_id),
            Employee.is_active == True,
        )
    )
    employee = result.scalar_one_or_none()

    if not employee:
        return Result(code=404, message="Employee not found").http_response()

    return Result(
        code=200,
        message="Profile fetched",
        extra={
            "user_id"       : session.user_id,
            "emp_id"        : employee.emp_id,
            "first_name"    : employee.first_name,
            "last_name"     : employee.last_name,
            "email"         : employee.email,
            "mobile"        : employee.mobile,
            "role"          : session.role,
            "gender"        : employee.gender,
            "qualification" : employee.qualification,
            "joining_dt"    : str(employee.joining_dt) if employee.joining_dt else None,
            "valid_till"    : session.valid_till.isoformat(),
        },
    ).http_response()


# ── Logout ─────────────────────────────────────────────────────────────────────

@profile_router.post("/logout/")
async def logout(
    response: Response,
    cookie_key: str = Cookie(default=None, alias="client_key"),
    header_key: str = Header(default=None, alias="client_key"),
    db: AsyncSession = Depends(get_db),
):
    
    key = cookie_key or header_key

    if key:
        await cache.delete(f"session:{key}")
        result = await db.execute(select(Session).where(Session.client_key == key))
        session = result.scalar_one_or_none()
        if session:
            await db.delete(session)
            await db.commit()
    response.delete_cookie(key="client_key")

    return Result(code=200, message="Logged out successfully").http_response()
