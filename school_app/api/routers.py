# api/routers.py
from api.auth import auth_router
from api.login import login_router
from api.school_group import school_group_router
from api.profile import profile_router

ROUTERS = [
    (auth_router,         "/api/auth"),
    (login_router,        "/api/auth/login"),
    (school_group_router, "/api/school-group"),
    (profile_router,      "/api/profile"),
]
