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
from api.exam import exam_router
from api.class_teacher import class_teacher_router
from api.attendance import attendance_router
from api.timetable import timetable_router
from api.notification import notification_router
from api.holiday import holiday_router
from api.announcement import announcement_router
from api.student_diary import student_diary_router
from api.transport import transport_router
from api.emp_leave_request import emp_leave_router
from api.custom_alarm import custom_alarm_router
from api.dashboard import dashboard_router
from api.android_student import android_student_router
from api.android_teacher import android_teacher_router

ROUTERS = [
    (auth_router,                  "/api/auth"),
    (dashboard_router,              "/api/dashboard"),
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
    (exam_router,                  "/api/exam"),
    (class_teacher_router,         "/api/teacher"),
    (attendance_router,              "/api/attendance"),
    (timetable_router,               "/api"),
    (notification_router,           "/api/notification"),
    (holiday_router,                "/api/holiday"),
    (announcement_router,           "/api/announcement"),
    (student_diary_router,          "/api/student_diary"),
    (transport_router,              "/api/transport"),
    (emp_leave_router,              "/api/emp_leave"),
    (custom_alarm_router,           "/api/custom_alarm"),
    (android_student_router,        "/api/android/student"),
    (android_teacher_router,        "/api/android/teacher"),
]
