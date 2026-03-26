# api/routers.py
from api.auth import auth_router

ROUTERS = [
    (auth_router, "/api/auth"),
]
