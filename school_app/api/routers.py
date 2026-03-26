# api/routers.py
from api.auth import auth_router
from api.school_group import school_group_router

ROUTERS = [
    (auth_router,         "/api/auth"),
    (school_group_router, "/api/school-group"),
]
