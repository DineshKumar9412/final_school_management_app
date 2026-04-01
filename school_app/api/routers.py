# api/routers.py
from api.auth import auth_router
from api.web_login import web_login_router
from api.profile import profile_router
from api.android_login import android_router
from api.school_group import school_group_router
from api.school_stream import school_stream_router
from api.school_stream_class import school_stream_class_router
from api.school_stream_class_section import school_stream_section_router
from api.school_stream_subject import school_stream_subject_router
from api.student import student_router
from api.employee import employee_router

ROUTERS = [
    (auth_router,                  "/api/auth"),
    (web_login_router,             "/api/auth"),
    (profile_router,               "/api/auth"),
    (android_router,               "/api/auth"),
    (school_group_router,          "/api/school_group"),
    (school_stream_router,         "/api/school_stream"),
    (school_stream_class_router,   "/api/school_stream_class"),
    (school_stream_section_router, "/api/school_stream_section"),
    (school_stream_subject_router, "/api/school_stream_subject"),
    (student_router,               "/api/student"),
    (employee_router,              "/api/employee"),
]
