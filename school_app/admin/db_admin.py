# admin/db_admin.py
from sqladmin import ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

# ══════════════════════════════════════════════
# ADMIN CREDENTIALS
# ══════════════════════════════════════════════

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin@1234"
SECRET_KEY     = "db_admin_secret_key_school_2026"


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            request.session.update({"db_admin_token": SECRET_KEY})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("db_admin_token")
        return token == SECRET_KEY


authentication_backend = AdminAuth(secret_key=SECRET_KEY)

from models.school_stream_models import School, SchoolGroup, SchoolStreamClass, SchoolStreamClassSection, SchoolStreamSubject
from models.student_models import Student, StudentClassMapping
from models.employee_models import Employee, Role
from models.attendance_models import StudentAttendance, EmployeeAttendance
from models.exam_models import Grade, Exam, ExamTimetable, StudentMarks, OnlineExam, OnlineClass
from models.announcement_models import Announcement
from models.notification_models import Notification
from models.holiday_models import Holiday
from models.timetable_models import TimeTable
from models.transport_models import VehicleDetails, TransportationStudent
from models.emp_leave_request_models import EmpLeaveRequest
from models.student_diary_models import StudentDiary
from models.gallery_banner_models import SchoolGallery, SchoolBanner


# ══════════════════════════════════════════════
# SCHOOL
# ══════════════════════════════════════════════

class SchoolAdmin(ModelView, model=School):
    name                 = "School"
    name_plural          = "Schools"
    icon                 = "fa-solid fa-school"
    column_list          = [School.school_id, School.school_name, School.city, School.status]
    column_searchable_list = [School.school_name, School.city]
    column_sortable_list   = [School.school_id, School.school_name]


class SchoolGroupAdmin(ModelView, model=SchoolGroup):
    name                 = "School Group"
    name_plural          = "School Groups"
    icon                 = "fa-solid fa-layer-group"
    column_list          = [SchoolGroup.school_group_id, SchoolGroup.group_name, SchoolGroup.school_id, SchoolGroup.status]
    column_searchable_list = [SchoolGroup.group_name]
    column_sortable_list   = [SchoolGroup.school_group_id, SchoolGroup.group_name]


# ══════════════════════════════════════════════
# CLASS / SECTION / SUBJECT
# ══════════════════════════════════════════════

class SchoolStreamClassAdmin(ModelView, model=SchoolStreamClass):
    name                 = "Class"
    name_plural          = "Classes"
    icon                 = "fa-solid fa-chalkboard"
    column_list          = [SchoolStreamClass.class_id, SchoolStreamClass.class_name, SchoolStreamClass.class_code, SchoolStreamClass.school_group_id, SchoolStreamClass.status]
    column_searchable_list = [SchoolStreamClass.class_name, SchoolStreamClass.class_code]
    column_sortable_list   = [SchoolStreamClass.class_id, SchoolStreamClass.class_code]


class SchoolStreamClassSectionAdmin(ModelView, model=SchoolStreamClassSection):
    name                 = "Section"
    name_plural          = "Sections"
    icon                 = "fa-solid fa-sitemap"
    column_list          = [SchoolStreamClassSection.section_id, SchoolStreamClassSection.section_name, SchoolStreamClassSection.section_code, SchoolStreamClassSection.class_id, SchoolStreamClassSection.status]
    column_searchable_list = [SchoolStreamClassSection.section_name, SchoolStreamClassSection.section_code]
    column_sortable_list   = [SchoolStreamClassSection.section_id]


class SchoolStreamSubjectAdmin(ModelView, model=SchoolStreamSubject):
    name                 = "Subject"
    name_plural          = "Subjects"
    icon                 = "fa-solid fa-book"
    column_list          = [SchoolStreamSubject.subject_id, SchoolStreamSubject.subject_name, SchoolStreamSubject.class_id, SchoolStreamSubject.status]
    column_searchable_list = [SchoolStreamSubject.subject_name]
    column_sortable_list   = [SchoolStreamSubject.subject_id, SchoolStreamSubject.subject_name]


# ══════════════════════════════════════════════
# EMPLOYEE
# ══════════════════════════════════════════════

class RoleAdmin(ModelView, model=Role):
    name                 = "Role"
    name_plural          = "Roles"
    icon                 = "fa-solid fa-user-tag"
    column_list          = [Role.role_id, Role.role_name]
    column_searchable_list = [Role.role_name]
    column_sortable_list   = [Role.role_id, Role.role_name]


class EmployeeAdmin(ModelView, model=Employee):
    name                 = "Employee"
    name_plural          = "Employees"
    icon                 = "fa-solid fa-user-tie"
    column_list          = [Employee.id, Employee.emp_id, Employee.first_name, Employee.last_name, Employee.email, Employee.is_active]
    column_searchable_list = [Employee.first_name, Employee.last_name, Employee.email, Employee.emp_id]
    column_sortable_list   = [Employee.id, Employee.first_name, Employee.last_name]


# ══════════════════════════════════════════════
# STUDENT
# ══════════════════════════════════════════════

class StudentAdmin(ModelView, model=Student):
    name                 = "Student"
    name_plural          = "Students"
    icon                 = "fa-solid fa-user-graduate"
    column_list          = [Student.student_id, Student.first_name, Student.last_name, Student.student_roll_id, Student.gender, Student.status]
    column_searchable_list = [Student.first_name, Student.last_name, Student.student_roll_id, Student.email]
    column_sortable_list   = [Student.student_id, Student.first_name, Student.last_name]


class StudentClassMappingAdmin(ModelView, model=StudentClassMapping):
    name                 = "Student Class Mapping"
    name_plural          = "Student Class Mappings"
    icon                 = "fa-solid fa-arrows-left-right"
    column_list          = [StudentClassMapping.id, StudentClassMapping.student_id, StudentClassMapping.class_id, StudentClassMapping.section_id, StudentClassMapping.status, StudentClassMapping.is_active]
    column_sortable_list   = [StudentClassMapping.id, StudentClassMapping.student_id]


# ══════════════════════════════════════════════
# ATTENDANCE
# ══════════════════════════════════════════════

class StudentAttendanceAdmin(ModelView, model=StudentAttendance):
    name                 = "Student Attendance"
    name_plural          = "Student Attendance"
    icon                 = "fa-solid fa-calendar-check"
    column_list          = [StudentAttendance.att_id, StudentAttendance.student_id, StudentAttendance.attendance_dt, StudentAttendance.status]
    column_sortable_list   = [StudentAttendance.att_id, StudentAttendance.attendance_dt]


class EmployeeAttendanceAdmin(ModelView, model=EmployeeAttendance):
    name                 = "Employee Attendance"
    name_plural          = "Employee Attendance"
    icon                 = "fa-solid fa-calendar-day"
    column_list          = [EmployeeAttendance.att_id, EmployeeAttendance.emp_id, EmployeeAttendance.attendance_dt, EmployeeAttendance.status]
    column_sortable_list   = [EmployeeAttendance.att_id, EmployeeAttendance.attendance_dt]


# ══════════════════════════════════════════════
# EXAM
# ══════════════════════════════════════════════

class GradeAdmin(ModelView, model=Grade):
    name                 = "Grade"
    name_plural          = "Grades"
    icon                 = "fa-solid fa-star"
    column_list          = [Grade.grade_id, Grade.grade, Grade.start_range, Grade.end_range, Grade.is_active]
    column_sortable_list   = [Grade.grade_id, Grade.start_range]


class ExamAdmin(ModelView, model=Exam):
    name                 = "Exam"
    name_plural          = "Exams"
    icon                 = "fa-solid fa-file-pen"
    column_list          = [Exam.exam_id, Exam.exam_name, Exam.class_id, Exam.section_id, Exam.session_yr, Exam.is_active]
    column_searchable_list = [Exam.exam_name, Exam.session_yr]
    column_sortable_list   = [Exam.exam_id, Exam.exam_name]


class ExamTimetableAdmin(ModelView, model=ExamTimetable):
    name                 = "Exam Timetable"
    name_plural          = "Exam Timetables"
    icon                 = "fa-solid fa-table-list"
    column_list          = [ExamTimetable.timetable_id, ExamTimetable.exam_id, ExamTimetable.class_id, ExamTimetable.section_id, ExamTimetable.subject_id, ExamTimetable.total_marks, ExamTimetable.pass_mark]
    column_sortable_list   = [ExamTimetable.timetable_id]


class StudentMarksAdmin(ModelView, model=StudentMarks):
    name                 = "Student Marks"
    name_plural          = "Student Marks"
    icon                 = "fa-solid fa-percent"
    column_list          = [StudentMarks.id, StudentMarks.student_id, StudentMarks.class_id, StudentMarks.section_id, StudentMarks.subject_id, StudentMarks.mark]
    column_sortable_list   = [StudentMarks.id, StudentMarks.student_id]


class OnlineExamAdmin(ModelView, model=OnlineExam):
    name                 = "Online Exam"
    name_plural          = "Online Exams"
    icon                 = "fa-solid fa-laptop-file"
    column_list          = [OnlineExam.id, OnlineExam.title, OnlineExam.class_id, OnlineExam.section_id, OnlineExam.subject_id, OnlineExam.start_date, OnlineExam.end_date]
    column_searchable_list = [OnlineExam.title, OnlineExam.exam_code]
    column_sortable_list   = [OnlineExam.id]


class OnlineClassAdmin(ModelView, model=OnlineClass):
    name                 = "Online Class"
    name_plural          = "Online Classes"
    icon                 = "fa-solid fa-video"
    column_list          = [OnlineClass.id, OnlineClass.title, OnlineClass.class_id, OnlineClass.section_id, OnlineClass.subject_id, OnlineClass.start_date, OnlineClass.end_date]
    column_searchable_list = [OnlineClass.title]
    column_sortable_list   = [OnlineClass.id]


# ══════════════════════════════════════════════
# COMMUNICATION
# ══════════════════════════════════════════════

class AnnouncementAdmin(ModelView, model=Announcement):
    name                 = "Announcement"
    name_plural          = "Announcements"
    icon                 = "fa-solid fa-bullhorn"
    column_list          = [Announcement.id, Announcement.title, Announcement.class_id, Announcement.section_id, Announcement.category, Announcement.created_at]
    column_searchable_list = [Announcement.title]
    column_sortable_list   = [Announcement.id, Announcement.created_at]


class NotificationAdmin(ModelView, model=Notification):
    name                 = "Notification"
    name_plural          = "Notifications"
    icon                 = "fa-solid fa-bell"
    column_list          = [Notification.id, Notification.title, Notification.role_id, Notification.created_at]
    column_searchable_list = [Notification.title]
    column_sortable_list   = [Notification.id, Notification.created_at]


class HolidayAdmin(ModelView, model=Holiday):
    name                 = "Holiday"
    name_plural          = "Holidays"
    icon                 = "fa-solid fa-umbrella-beach"
    column_list          = [Holiday.id, Holiday.title, Holiday.holiday_date, Holiday.description]
    column_searchable_list = [Holiday.title]
    column_sortable_list   = [Holiday.id, Holiday.holiday_date]


# ══════════════════════════════════════════════
# TIMETABLE
# ══════════════════════════════════════════════

class TimeTableAdmin(ModelView, model=TimeTable):
    name                 = "Timetable"
    name_plural          = "Timetables"
    icon                 = "fa-solid fa-clock"
    column_list          = [TimeTable.id, TimeTable.class_id, TimeTable.section_id, TimeTable.subject_id, TimeTable.day, TimeTable.start_time, TimeTable.end_time]
    column_sortable_list   = [TimeTable.id, TimeTable.day]


# ══════════════════════════════════════════════
# TRANSPORT
# ══════════════════════════════════════════════

class VehicleAdmin(ModelView, model=VehicleDetails):
    name                 = "Vehicle"
    name_plural          = "Vehicles"
    icon                 = "fa-solid fa-bus"
    column_list          = [VehicleDetails.id, VehicleDetails.vehicle_no, VehicleDetails.vehicle_capacity, VehicleDetails.status]
    column_searchable_list = [VehicleDetails.vehicle_no]
    column_sortable_list   = [VehicleDetails.id]


class TransportationStudentAdmin(ModelView, model=TransportationStudent):
    name                 = "Transport Student"
    name_plural          = "Transport Students"
    icon                 = "fa-solid fa-bus-simple"
    column_list          = [TransportationStudent.id, TransportationStudent.student_id, TransportationStudent.vehicle_id]
    column_sortable_list   = [TransportationStudent.id]


# ══════════════════════════════════════════════
# LEAVE / DIARY / GALLERY
# ══════════════════════════════════════════════

class EmpLeaveRequestAdmin(ModelView, model=EmpLeaveRequest):
    name                 = "Employee Leave"
    name_plural          = "Employee Leaves"
    icon                 = "fa-solid fa-calendar-xmark"
    column_list          = [EmpLeaveRequest.id, EmpLeaveRequest.emp_id, EmpLeaveRequest.from_dt, EmpLeaveRequest.to_date, EmpLeaveRequest.type, EmpLeaveRequest.status]
    column_sortable_list   = [EmpLeaveRequest.id, EmpLeaveRequest.from_dt]


class StudentDiaryAdmin(ModelView, model=StudentDiary):
    name                 = "Student Diary"
    name_plural          = "Student Diaries"
    icon                 = "fa-solid fa-book-open"
    column_list          = [StudentDiary.id, StudentDiary.student_id, StudentDiary.class_id, StudentDiary.subject_id, StudentDiary.dairy_date]
    column_sortable_list   = [StudentDiary.id, StudentDiary.dairy_date]


class GalleryAdmin(ModelView, model=SchoolGallery):
    name                 = "Gallery"
    name_plural          = "Gallery"
    icon                 = "fa-solid fa-images"
    column_list          = [SchoolGallery.id, SchoolGallery.school_id, SchoolGallery.bannerlink, SchoolGallery.status]
    column_sortable_list   = [SchoolGallery.id]


class BannerAdmin(ModelView, model=SchoolBanner):
    name                 = "Banner"
    name_plural          = "Banners"
    icon                 = "fa-solid fa-image"
    column_list          = [SchoolBanner.id, SchoolBanner.school_id, SchoolBanner.bannerlink, SchoolBanner.status]
    column_sortable_list   = [SchoolBanner.id]


# ══════════════════════════════════════════════
# ALL VIEWS — imported in main.py
# ══════════════════════════════════════════════

ALL_VIEWS = [
    SchoolAdmin,
    SchoolGroupAdmin,
    SchoolStreamClassAdmin,
    SchoolStreamClassSectionAdmin,
    SchoolStreamSubjectAdmin,
    RoleAdmin,
    EmployeeAdmin,
    StudentAdmin,
    StudentClassMappingAdmin,
    StudentAttendanceAdmin,
    EmployeeAttendanceAdmin,
    GradeAdmin,
    ExamAdmin,
    ExamTimetableAdmin,
    StudentMarksAdmin,
    OnlineExamAdmin,
    OnlineClassAdmin,
    AnnouncementAdmin,
    NotificationAdmin,
    HolidayAdmin,
    TimeTableAdmin,
    VehicleAdmin,
    TransportationStudentAdmin,
    EmpLeaveRequestAdmin,
    StudentDiaryAdmin,
    GalleryAdmin,
    BannerAdmin,
]
