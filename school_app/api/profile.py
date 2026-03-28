# api/profile.py
from fastapi import APIRouter, Depends

from security.dependencies import validate_session
from response.result import Result

profile_router = APIRouter(tags=["PROFILE"])


@profile_router.get("/", summary="Get current logged-in user profile")
async def get_profile(
    session: dict = Depends(validate_session),
):
    user = session.get("user_id")

    if not user:
        return Result(code=401, message="Not logged in.", extra={}).http_response()

    return Result(
        code=200,
        message="Profile fetched successfully.",
        extra={
            "role":    session.get("role"),
            "profile": user,
        },
    ).http_response()

