# api/routers.py
from api.auth import auth_router
from api.login import login_router
from api.profile import profile_router
from api.android_login import android_router

ROUTERS = [
    (auth_router, "/api/auth"),
    (login_router, "/api/auth"),
    (profile_router, "/api/auth"),
    (android_router, "/api/auth"),
]
