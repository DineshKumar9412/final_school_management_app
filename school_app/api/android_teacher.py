# api/android_teacher.py
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, or_, and_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from models.announcement_models import Announcement
from models.assignment_models import Assignment, AssignmentSubmission
from models.attendance_models import StudentAttendance
from models.auth_models import Session
from models.chat_models import ChatMessage
from models.custom_alarm_models import CustomAlarm
from models.emp_leave_request_models import EmpLeaveRequest, LeaveTypeEnum
from models.micro_schedule_models import MicroSchedule
from models.employee_models import Employee, EmployeeClassMapping
from models.exam_models import Exam, ExamTimetable, StudentMarks, Grade
from models.holiday_models import Holiday
from models.school_stream_models import SchoolStreamClass, SchoolStreamClassSection, SchoolStreamSubject
from models.student_models import Student, StudentClassMapping
from models.timetable_models import TimeTable
from response.result import Result
from schemas.android_teacher_schemas import (
    AttendanceEntry, BulkAttendanceRequest,
    AnnouncementCreateRequest, AnnouncementUpdateRequest,
    DailyTaskCreateRequest,
    MarkEntry, BulkMarksSubmitRequest,
    LeaveApplyRequest,
    SendMessageRequest,
    MicroScheduleCreateRequest, MicroScheduleUpdateRequest,
    AssignmentCreateRequest, AssignmentUpdateRequest,
)
from security.valid_session import valid_session

android_teacher_router = APIRouter(tags=["ANDROID APIS TEACHER"])

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ── Shared helpers ─────────────────────────────────────────────────────────────

async def _get_teacher_context(session: Session, db: AsyncSession):
    """Returns (employee, emp_mappings) or (None, [])."""
    if not session.user_id:
        return None, []

    teacher_id = int(session.user_id)

    emp_result = await db.execute(
        select(Employee).where(Employee.id == teacher_id)
    )
    employee = emp_result.scalar_one_or_none()
    if not employee:
        return None, []

    # EmployeeClassMapping.emp_id stores employee.emp_id (the staff ID string),
    # NOT employee.id (the DB primary key). Use employee.emp_id here.
    mappings_result = await db.execute(
        select(EmployeeClassMapping).where(EmployeeClassMapping.emp_id == employee.emp_id)
    )
    mappings = mappings_result.scalars().all()

    return employee, mappings


def _class_section_filter(mappings):
    """OR filter across all class/section pairs the teacher is mapped to."""
    if not mappings:
        return None
    return or_(*[
        and_(
            StudentClassMapping.class_id   == m.class_id,
            StudentClassMapping.section_id == m.section_id,
        )
        for m in mappings
    ])


def _attendance_class_filter(mappings):
    """OR filter for StudentAttendance across teacher's class/section pairs."""
    if not mappings:
        return None
    return or_(*[
        and_(
            StudentAttendance.class_id   == m.class_id,
            StudentAttendance.section_id == m.section_id,
        )
        for m in mappings
    ])


def _slot_status(start_time, end_time) -> str:
    now = datetime.now().time()
    if start_time <= now <= end_time:
        return "Live"
    if now < start_time:
        return "Upcoming"
    return "Completed"


# ── Timetable query for teacher ────────────────────────────────────────────────

async def _query_teacher_timetable(db: AsyncSession, emp_id, day: Optional[str] = None):
    """
    emp_id: employee.emp_id (staff number string e.g. "2026003"), NOT employee.id.
    day:    3-letter abbreviation matching DB column ("Mon", "Tue", …).
    """
    stmt = (
        select(
            TimeTable,
            SchoolStreamSubject.subject_name,
            SchoolStreamClass.class_name,
            SchoolStreamClassSection.section_name,
        )
        .join(
            EmployeeClassMapping,
            and_(
                EmployeeClassMapping.class_id   == TimeTable.class_id,
                EmployeeClassMapping.section_id == TimeTable.section_id,
                EmployeeClassMapping.subject_id == TimeTable.subject_id,
                EmployeeClassMapping.emp_id     == emp_id,
            ),
        )
        .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == TimeTable.subject_id)
        .outerjoin(SchoolStreamClass,   SchoolStreamClass.class_id     == TimeTable.class_id)
        .outerjoin(SchoolStreamClassSection, SchoolStreamClassSection.section_id == TimeTable.section_id)
        .order_by(TimeTable.start_time)
    )
    if day:
        stmt = stmt.where(TimeTable.day == day)

    result = await db.execute(stmt)
    return result.all()


def _tt_row(tt, subject_name, class_name, section_name, include_status: bool = False) -> dict:
    start_str = tt.start_time.strftime("%I:%M %p").lstrip("0") if tt.start_time else None
    end_str   = tt.end_time.strftime("%I:%M %p").lstrip("0")   if tt.end_time   else None
    row = {
        "id":           tt.id,
        "subject":      subject_name,
        "class_name":   class_name,
        "section_name": section_name,
        "start_time":   start_str,
        "end_time":     end_str,
    }
    if include_status:
        row["status"] = _slot_status(tt.start_time, tt.end_time) if tt.start_time and tt.end_time else None
    return row


# ── GET /dashboard/ ────────────────────────────────────────────────────────────

@android_teacher_router.get("/dashboard/")
async def teacher_dashboard(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    employee, mappings = await _get_teacher_context(session, db)

    if not employee:
        return Result(code=404, message="Teacher not found.").http_response()

    today_abbr = datetime.now().strftime("%a")   # "Mon", "Tue", … — matches DB day column
    today_date = date.today()

    # ── Total students in teacher's classes ──
    total_students = 0
    if mappings:
        cs_filter = _class_section_filter(mappings)
        count_result = await db.execute(
            select(func.count(func.distinct(StudentClassMapping.student_id)))
            .where(cs_filter, StudentClassMapping.is_active == True)
        )
        total_students = count_result.scalar_one() or 0

    # ── Timetable today ──
    tt_rows = await _query_teacher_timetable(db, employee.emp_id, day=today_abbr)
    timetable_today = [
        _tt_row(tt, subj, cls, sec, include_status=True)
        for tt, subj, cls, sec in tt_rows
    ]

    # ── Announcement (latest 1 preview) ──
    class_ids = list({m.class_id for m in mappings if m.class_id})
    ann_filter = or_(
        Announcement.class_id.in_(class_ids) if class_ids else Announcement.class_id.is_(None),
        Announcement.class_id.is_(None),
    )
    ann_result = await db.execute(
        select(Announcement)
        .where(ann_filter)
        .order_by(Announcement.created_at.desc())
        .limit(3)
    )
    announcements = [
        {
            "id":       a.id,
            "category": a.category,
            "title":    a.title,
            "date":     a.created_at.strftime("%b %d, %Y"),
        }
        for a in ann_result.scalars().all()
    ]

    # ── Leaves — absent students today ──
    absent_students = []
    if mappings:
        att_filter = _attendance_class_filter(mappings)
        leaves_result = await db.execute(
            select(StudentAttendance, Student.first_name, Student.last_name, Student.student_roll_id)
            .join(Student, Student.student_id == StudentAttendance.student_id)
            .where(
                att_filter,
                StudentAttendance.attendance_dt == today_date,
                StudentAttendance.status.in_(["A", "L"]),
            )
            .order_by(Student.first_name)
        )
        absent_students = [
            {
                "student_id":  sa.student_id,
                "name":        f"{fn or ''} {ln or ''}".strip(),
                "roll_number": roll,
                "status":      sa.status,   # "A" or "L"
            }
            for sa, fn, ln, roll in leaves_result.all()
        ]

    # ── Upcoming holidays (next 3) ──
    holidays_result = await db.execute(
        select(Holiday)
        .where(Holiday.holiday_date >= today_date)
        .order_by(Holiday.holiday_date)
        .limit(3)
    )
    holidays = [
        {
            "id":           h.id,
            "title":        h.title,
            "description":  h.description,
            "date":         str(h.holiday_date),
            "day":          h.holiday_date.strftime("%d"),
            "month":        h.holiday_date.strftime("%b"),
        }
        for h in holidays_result.scalars().all()
    ]

    return Result(
        code=200,
        message="Dashboard fetched.",
        extra={
            "teacher": {
                "name":   f"{employee.first_name or ''} {employee.last_name or ''}".strip(),
                "emp_id": employee.emp_id,
            },
            "total_students":  total_students,
            "timetable_today": timetable_today,
            "announcements":   announcements,
            "leaves": {
                "absent_count":    len(absent_students),
                "absent_students": absent_students[:3],   # preview 3
                "everyone_present": len(absent_students) == 0,
            },
            "holidays": holidays,
        },
    ).http_response()


# ── GET /timetable/ (View All) ─────────────────────────────────────────────────

@android_teacher_router.get("/timetable/")
async def teacher_timetable(
    day: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    employee, _ = await _get_teacher_context(session, db)
    if not employee:
        return Result(code=404, message="Teacher not found.").http_response()

    rows = await _query_teacher_timetable(db, employee.emp_id, day=day)

    grouped: dict = {}
    today_abbr = datetime.now().strftime("%a")   # "Mon", "Tue", … — matches DB
    for tt, subj, cls, sec in rows:
        d = tt.day or "Unknown"
        grouped.setdefault(d, []).append(
            _tt_row(tt, subj, cls, sec, include_status=(d == today_abbr))
        )

    sorted_timetable = {d: grouped[d] for d in DAY_ORDER if d in grouped}
    for d in grouped:
        if d not in sorted_timetable:
            sorted_timetable[d] = grouped[d]

    return Result(
        code=200,
        message="Timetable fetched.",
        extra={"timetable": sorted_timetable},
    ).http_response()


# ── GET /announcements/ (View More) ───────────────────────────────────────────

@android_teacher_router.get("/announcements/")
async def teacher_announcements(
    page:      int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    _, mappings = await _get_teacher_context(session, db)

    class_ids = list({m.class_id for m in mappings if m.class_id})
    ann_filter = or_(
        Announcement.class_id.in_(class_ids) if class_ids else Announcement.class_id.is_(None),
        Announcement.class_id.is_(None),
    )

    total_result = await db.execute(
        select(func.count()).select_from(Announcement).where(ann_filter)
    )
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Announcement)
        .where(ann_filter)
        .order_by(Announcement.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    announcements = [
        {
            "id":          a.id,
            "category":    a.category,
            "title":       a.title,
            "description": a.description,
            "url":         a.url,
            "date":        a.created_at.strftime("%b %d, %Y"),
        }
        for a in result.scalars().all()
    ]

    return Result(
        code=200,
        message="Announcements fetched.",
        extra={
            "total":         total,
            "page":          page,
            "page_size":     page_size,
            "announcements": announcements,
        },
    ).http_response()


# ── GET /leaves/ (View More) ───────────────────────────────────────────────────

@android_teacher_router.get("/leaves/")
async def teacher_leaves(
    leave_date: Optional[date] = None,
    page:       int = 1,
    page_size:  int = 10,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    Returns absent students for the given date (default: today).
    """
    _, mappings = await _get_teacher_context(session, db)

    if not mappings:
        return Result(code=200, message="No class mapping found.", extra={"absent": [], "total": 0}).http_response()

    query_date = leave_date or date.today()
    att_filter = _attendance_class_filter(mappings)

    total_result = await db.execute(
        select(func.count())
        .select_from(StudentAttendance)
        .where(att_filter, StudentAttendance.attendance_dt == query_date, StudentAttendance.status == "A")
    )
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(StudentAttendance, Student.first_name, Student.last_name, Student.student_roll_id,
               SchoolStreamClass.class_name, SchoolStreamClassSection.section_name)
        .join(Student, Student.student_id == StudentAttendance.student_id)
        .outerjoin(SchoolStreamClass, SchoolStreamClass.class_id == StudentAttendance.class_id)
        .outerjoin(SchoolStreamClassSection, SchoolStreamClassSection.section_id == StudentAttendance.section_id)
        .where(att_filter, StudentAttendance.attendance_dt == query_date, StudentAttendance.status == "A")
        .order_by(Student.first_name)
        .offset(offset)
        .limit(page_size)
    )
    absent = [
        {
            "student_id":   sa.student_id,
            "name":         f"{fn or ''} {ln or ''}".strip(),
            "roll_number":  roll,
            "class_name":   cls,
            "section_name": sec,
        }
        for sa, fn, ln, roll, cls, sec in result.all()
    ]

    return Result(
        code=200,
        message="Absent students fetched.",
        extra={
            "date":      str(query_date),
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "everyone_present": total == 0,
            "absent":    absent,
        },
    ).http_response()


# ── GET /holidays/ (View More) ─────────────────────────────────────────────────

@android_teacher_router.get("/holidays/")
async def teacher_holidays(
    page:      int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    today_date = date.today()

    total_result = await db.execute(
        select(func.count()).select_from(Holiday).where(Holiday.holiday_date >= today_date)
    )
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Holiday)
        .where(Holiday.holiday_date >= today_date)
        .order_by(Holiday.holiday_date)
        .offset(offset)
        .limit(page_size)
    )
    holidays = [
        {
            "id":          h.id,
            "title":       h.title,
            "description": h.description,
            "date":        str(h.holiday_date),
            "day":         h.holiday_date.strftime("%d"),
            "month":       h.holiday_date.strftime("%b"),
        }
        for h in result.scalars().all()
    ]

    return Result(
        code=200,
        message="Holidays fetched.",
        extra={
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "holidays":  holidays,
        },
    ).http_response()


# ── GET /students/ (View Students) ────────────────────────────────────────────

@android_teacher_router.get("/students/")
async def teacher_students(
    class_id:   Optional[int] = None,
    section_id: Optional[int] = None,
    page:       int = 1,
    page_size:  int = 10,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    Returns students in the teacher's classes.
    Optionally filter by class_id or section_id.
    """
    _, mappings = await _get_teacher_context(session, db)

    if not mappings:
        return Result(code=200, message="No class mapping found.", extra={"students": [], "total": 0}).http_response()

    # Build filter: teacher's class/section pairs, optionally narrowed
    cs_filter = _class_section_filter(mappings)

    stmt_base = (
        select(Student, SchoolStreamClass.class_name, SchoolStreamClassSection.section_name)
        .join(StudentClassMapping, StudentClassMapping.student_id == Student.student_id)
        .outerjoin(SchoolStreamClass, SchoolStreamClass.class_id == StudentClassMapping.class_id)
        .outerjoin(SchoolStreamClassSection, SchoolStreamClassSection.section_id == StudentClassMapping.section_id)
        .where(cs_filter, StudentClassMapping.is_active == True)
    )
    if class_id is not None:
        stmt_base = stmt_base.where(StudentClassMapping.class_id == class_id)
    if section_id is not None:
        stmt_base = stmt_base.where(StudentClassMapping.section_id == section_id)

    total_result = await db.execute(
        select(func.count()).select_from(stmt_base.subquery())
    )
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        stmt_base.order_by(Student.first_name).offset(offset).limit(page_size)
    )
    students = [
        {
            "student_id":   s.student_id,
            "name":         f"{s.first_name or ''} {s.last_name or ''}".strip(),
            "roll_number":  s.student_roll_id,
            "class_name":   cls,
            "section_name": sec,
        }
        for s, cls, sec in result.all()
    ]

    return Result(
        code=200,
        message="Students fetched.",
        extra={
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "students":  students,
        },
    ).http_response()


# ── GET /students/{student_id}/ (Student Detail) ──────────────────────────────

@android_teacher_router.get("/students/{student_id}/")
async def teacher_student_detail(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """Returns full profile for a single student."""
    _, mappings = await _get_teacher_context(session, db)

    if not mappings:
        return Result(code=403, message="No class mapping.").http_response()

    cs_filter = _class_section_filter(mappings)

    result = await db.execute(
        select(Student, StudentClassMapping, SchoolStreamClass.class_name, SchoolStreamClassSection.section_name)
        .join(StudentClassMapping, StudentClassMapping.student_id == Student.student_id)
        .outerjoin(SchoolStreamClass, SchoolStreamClass.class_id == StudentClassMapping.class_id)
        .outerjoin(SchoolStreamClassSection, SchoolStreamClassSection.section_id == StudentClassMapping.section_id)
        .where(
            Student.student_id == student_id,
            cs_filter,
            StudentClassMapping.is_active == True,
        )
    )
    row = result.first()

    if not row:
        return Result(code=404, message="Student not found.").http_response()

    s, mapping, cls_name, sec_name = row
    return Result(
        code=200,
        message="Student detail fetched.",
        extra={
            "student_id":    s.student_id,
            "roll_number":   s.student_roll_id,
            "first_name":    s.first_name,
            "last_name":     s.last_name,
            "gender":        s.gender,
            "dob":           str(s.dob) if s.dob else None,
            "age":           s.age,
            "email":         s.email,
            "phone":         s.phone,
            "blood_group":   s.blood_group,
            "class_name":    cls_name,
            "section_name":  sec_name,
            "guardian": {
                "name":   f"{s.guardian_first_name or ''} {s.guardian_last_name or ''}".strip() or None,
                "phone":  s.guardian_phone,
                "email":  s.guardian_email,
                "gender": s.guardian_gender,
            },
        },
    ).http_response()


# ── GET /attendance/students/ (List students for attendance) ─────────────────

@android_teacher_router.get("/attendance/students/")
async def teacher_attendance_students(
    class_id:   int,
    section_id: int,
    att_date:   Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    Returns all students in a class/section with today's (or given date's)
    attendance status so the teacher can mark/view attendance.
    """
    _, mappings = await _get_teacher_context(session, db)

    if not mappings:
        return Result(code=403, message="No class mapping.").http_response()

    # Verify teacher has access to this class/section
    allowed = any(m.class_id == class_id and m.section_id == section_id for m in mappings)
    if not allowed:
        return Result(code=403, message="Access denied for this class/section.").http_response()

    query_date = att_date or date.today()

    # Fetch students in this class/section
    students_result = await db.execute(
        select(Student, StudentClassMapping)
        .join(StudentClassMapping, StudentClassMapping.student_id == Student.student_id)
        .where(
            StudentClassMapping.class_id   == class_id,
            StudentClassMapping.section_id == section_id,
            StudentClassMapping.is_active  == True,
        )
        .order_by(Student.first_name)
    )
    student_rows = students_result.all()

    if not student_rows:
        return Result(code=200, message="No students found.", extra={"students": [], "date": str(query_date)}).http_response()

    student_ids = [s.student_id for s, _ in student_rows]

    # Fetch existing attendance for the date
    att_result = await db.execute(
        select(StudentAttendance)
        .where(
            StudentAttendance.class_id   == class_id,
            StudentAttendance.section_id == section_id,
            StudentAttendance.attendance_dt == query_date,
            StudentAttendance.student_id.in_(student_ids),
        )
    )
    att_map = {a.student_id: a.status for a in att_result.scalars().all()}

    students_list = [
        {
            "student_id":  s.student_id,
            "name":        f"{s.first_name or ''} {s.last_name or ''}".strip(),
            "roll_number": s.student_roll_id,
            "status":      att_map.get(s.student_id, None),  # None = not marked yet
        }
        for s, _ in student_rows
    ]

    return Result(
        code=200,
        message="Attendance list fetched.",
        extra={
            "class_id":   class_id,
            "section_id": section_id,
            "date":       str(query_date),
            "students":   students_list,
        },
    ).http_response()


# ── POST /attendance/ (Mark / update attendance bulk) ────────────────────────

@android_teacher_router.post("/attendance/")
async def teacher_mark_attendance(
    body: BulkAttendanceRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    Upsert attendance for all students in a class/section for a given date.
    Pass records=[{student_id, status}] where status is "P" or "A".
    """
    _, mappings = await _get_teacher_context(session, db)

    if not mappings:
        return Result(code=403, message="No class mapping.").http_response()

    allowed = any(m.class_id == body.class_id and m.section_id == body.section_id for m in mappings)
    if not allowed:
        return Result(code=403, message="Access denied for this class/section.").http_response()

    # Delete existing attendance rows for this class/section/date, then re-insert
    await db.execute(
        delete(StudentAttendance).where(
            StudentAttendance.class_id   == body.class_id,
            StudentAttendance.section_id == body.section_id,
            StudentAttendance.attendance_dt == body.date,
        )
    )

    for entry in body.records:
        if entry.status not in ("P", "A", "L"):
            continue
        db.add(StudentAttendance(
            class_id      = body.class_id,
            section_id    = body.section_id,
            student_id    = entry.student_id,
            attendance_dt = body.date,
            status        = entry.status,
        ))

    await db.commit()

    return Result(
        code=200,
        message=f"Attendance saved for {len(body.records)} students.",
        extra={"date": str(body.date), "count": len(body.records)},
    ).http_response()


# ── GET /attendance/ (Teacher's class attendance history) ─────────────────────

@android_teacher_router.get("/attendance/")
async def teacher_attendance_summary(
    class_id:   Optional[int] = None,
    section_id: Optional[int] = None,
    month:      Optional[int] = None,
    year:       Optional[int] = None,
    page:       int = 1,
    page_size:  int = 30,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """Attendance records across teacher's classes, grouped by date."""
    _, mappings = await _get_teacher_context(session, db)

    if not mappings:
        return Result(code=200, message="No class mapping.", extra={"records": []}).http_response()

    att_filter = _attendance_class_filter(mappings)

    stmt = (
        select(
            StudentAttendance.attendance_dt,
            func.count().label("total"),
            func.sum(func.IF(StudentAttendance.status == "P", 1, 0)).label("present"),
            func.sum(func.IF(StudentAttendance.status == "A", 1, 0)).label("absent"),
            func.sum(func.IF(StudentAttendance.status == "L", 1, 0)).label("leave"),
        )
        .where(att_filter)
        .group_by(StudentAttendance.attendance_dt)
        .order_by(StudentAttendance.attendance_dt.desc())
    )

    if class_id is not None:
        stmt = stmt.where(StudentAttendance.class_id == class_id)
    if section_id is not None:
        stmt = stmt.where(StudentAttendance.section_id == section_id)
    if month is not None:
        stmt = stmt.where(func.month(StudentAttendance.attendance_dt) == month)
    if year is not None:
        stmt = stmt.where(func.year(StudentAttendance.attendance_dt) == year)

    offset = (page - 1) * page_size
    result = await db.execute(stmt.offset(offset).limit(page_size))
    records = [
        {
            "date":    str(row.attendance_dt),
            "total":   int(row.total or 0),
            "present": int(row.present or 0),
            "absent":  int(row.absent or 0),
            "leave":   int(row.leave or 0),
        }
        for row in result.all()
    ]

    return Result(
        code=200,
        message="Attendance summary fetched.",
        extra={"page": page, "page_size": page_size, "records": records},
    ).http_response()


# ── GET /assignments/ — list assignments created by this teacher ───────────────

@android_teacher_router.get("/assignments/")
async def teacher_assignments(
    class_id:   Optional[int] = None,
    section_id: Optional[int] = None,
    page:       int = 1,
    page_size:  int = 10,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    employee, mappings = await _get_teacher_context(session, db)
    if not employee:
        return Result(code=404, message="Teacher not found.").http_response()

    stmt = (
        select(Assignment, SchoolStreamSubject.subject_name)
        .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == Assignment.subject_id)
        .where(Assignment.emp_id == employee.id)
    )
    if class_id is not None:
        stmt = stmt.where(Assignment.class_id == class_id)
    if section_id is not None:
        stmt = stmt.where(Assignment.section_id == section_id)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    rows = await db.execute(
        stmt.order_by(Assignment.created_at.desc()).offset(offset).limit(page_size)
    )
    rows = rows.all()

    # Submission counts per assignment
    assignment_ids = [a.id for a, _ in rows]
    sub_counts: dict = {}
    if assignment_ids:
        cnt_result = await db.execute(
            select(AssignmentSubmission.assignment_id, func.count().label("cnt"))
            .where(
                AssignmentSubmission.assignment_id.in_(assignment_ids),
                AssignmentSubmission.status == "submitted",
            )
            .group_by(AssignmentSubmission.assignment_id)
        )
        sub_counts = {r.assignment_id: r.cnt for r in cnt_result.all()}

    assignments = [
        {
            "id":               a.id,
            "title":            a.title,
            "description":      a.description,
            "subject":          subj,
            "class_id":         a.class_id,
            "section_id":       a.section_id,
            "group_name":       a.group_name,
            "due_date":         str(a.due_date) if a.due_date else None,
            "submitted_count":  sub_counts.get(a.id, 0),
            "created_at":       a.created_at.strftime("%Y-%m-%d"),
        }
        for a, subj in rows
    ]

    return Result(
        code=200,
        message="Assignments fetched.",
        extra={"total": total, "page": page, "page_size": page_size, "assignments": assignments},
    ).http_response()


# ── POST /assignments/ — create assignment ────────────────────────────────────

@android_teacher_router.post("/assignments/")
async def teacher_create_assignment(
    body: AssignmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    employee, mappings = await _get_teacher_context(session, db)
    if not employee:
        return Result(code=404, message="Teacher not found.").http_response()
    if not mappings:
        return Result(code=403, message="No class mapping.").http_response()

    allowed = any(m.class_id == body.class_id and m.section_id == body.section_id for m in mappings)
    if not allowed:
        return Result(code=403, message="Access denied for this class/section.").http_response()

    assignment = Assignment(
        title       = body.title,
        description = body.description,
        class_id    = body.class_id,
        section_id  = body.section_id,
        subject_id  = body.subject_id,
        group_name  = body.group_name,
        emp_id      = employee.id,
        due_date    = body.due_date,
        status      = 1,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    return Result(
        code=200,
        message="Assignment created.",
        extra={
            "id":          assignment.id,
            "title":       assignment.title,
            "class_id":    assignment.class_id,
            "section_id":  assignment.section_id,
            "due_date":    str(assignment.due_date) if assignment.due_date else None,
            "created_at":  assignment.created_at.strftime("%Y-%m-%d"),
        },
    ).http_response()


# ── PUT /assignments/{id}/ — edit assignment ──────────────────────────────────

@android_teacher_router.put("/assignments/{assignment_id}/")
async def teacher_update_assignment(
    assignment_id: int,
    body: AssignmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    employee, _ = await _get_teacher_context(session, db)
    if not employee:
        return Result(code=404, message="Teacher not found.").http_response()

    result = await db.execute(
        select(Assignment).where(Assignment.id == assignment_id, Assignment.emp_id == employee.id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        return Result(code=404, message="Assignment not found.").http_response()

    if body.title       is not None: assignment.title       = body.title
    if body.description is not None: assignment.description = body.description
    if body.class_id    is not None: assignment.class_id    = body.class_id
    if body.section_id  is not None: assignment.section_id  = body.section_id
    if body.subject_id  is not None: assignment.subject_id  = body.subject_id
    if body.group_name  is not None: assignment.group_name  = body.group_name
    if body.due_date    is not None: assignment.due_date     = body.due_date
    if body.status      is not None: assignment.status       = body.status

    await db.commit()
    return Result(code=200, message="Assignment updated.").http_response()


# ── DELETE /assignments/{id}/ — delete assignment ─────────────────────────────

@android_teacher_router.delete("/assignments/{assignment_id}/")
async def teacher_delete_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    employee, _ = await _get_teacher_context(session, db)
    if not employee:
        return Result(code=404, message="Teacher not found.").http_response()

    result = await db.execute(
        select(Assignment).where(Assignment.id == assignment_id, Assignment.emp_id == employee.id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        return Result(code=404, message="Assignment not found.").http_response()

    await db.delete(assignment)
    await db.commit()
    return Result(code=200, message="Assignment deleted.").http_response()


# ── GET /exams/ (Exam schedule for teacher's classes) ─────────────────────────

@android_teacher_router.get("/exams/")
async def teacher_exams(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """Returns exam schedule for all classes the teacher is mapped to."""
    _, mappings = await _get_teacher_context(session, db)

    if not mappings:
        return Result(code=200, message="No class mapping.", extra={"exams": []}).http_response()

    class_ids = list({m.class_id for m in mappings if m.class_id})

    result = await db.execute(
        select(ExamTimetable, Exam, SchoolStreamSubject.subject_name, SchoolStreamClass.class_name)
        .join(Exam, Exam.exam_id == ExamTimetable.exam_id)
        .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == ExamTimetable.subject_id)
        .outerjoin(SchoolStreamClass, SchoolStreamClass.class_id == ExamTimetable.class_id)
        .where(
            ExamTimetable.class_id.in_(class_ids),
            Exam.is_active == True,
            ExamTimetable.is_active == True,
        )
        .order_by(ExamTimetable.exam_start_date)
    )

    exams = [
        {
            "timetable_id": et.timetable_id,
            "exam_name":    ex.exam_name,
            "subject":      subj,
            "class_name":   cls,
            "start_date":   str(et.exam_start_date.date()) if et.exam_start_date else None,
            "end_date":     str(et.exam_end_date.date())   if et.exam_end_date   else None,
            "total_marks":  float(et.total_marks) if et.total_marks else None,
            "pass_mark":    float(et.pass_mark)   if et.pass_mark   else None,
        }
        for et, ex, subj, cls in result.all()
    ]

    return Result(
        code=200,
        message="Exam schedule fetched.",
        extra={"exams": exams},
    ).http_response()


# ── GET /exams/results/ (Student marks for teacher's classes) ─────────────────

@android_teacher_router.get("/exams/results/")
async def teacher_exam_results(
    class_id:   Optional[int] = None,
    section_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    page:       int = 1,
    page_size:  int = 20,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """Returns student marks across teacher's classes."""
    _, mappings = await _get_teacher_context(session, db)

    if not mappings:
        return Result(code=200, message="No class mapping.", extra={"results": []}).http_response()

    class_ids = list({m.class_id for m in mappings if m.class_id})

    stmt = (
        select(
            StudentMarks,
            Student.first_name,
            Student.last_name,
            Student.student_roll_id,
            SchoolStreamSubject.subject_name,
            Grade.grade,
        )
        .join(Student, Student.student_id == StudentMarks.student_id)
        .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == StudentMarks.subject_id)
        .outerjoin(
            Grade,
            and_(
                Grade.start_range <= StudentMarks.mark,
                Grade.end_range   >= StudentMarks.mark,
                Grade.is_active   == True,
            ),
        )
        .where(StudentMarks.class_id.in_(class_ids))
    )

    if class_id is not None:
        stmt = stmt.where(StudentMarks.class_id == class_id)
    if subject_id is not None:
        stmt = stmt.where(StudentMarks.subject_id == subject_id)
    if section_id is not None:
        # filter via StudentClassMapping
        subq = (
            select(StudentClassMapping.student_id)
            .where(
                StudentClassMapping.section_id == section_id,
                StudentClassMapping.is_active  == True,
            )
            .scalar_subquery()
        )
        stmt = stmt.where(StudentMarks.student_id.in_(subq))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(stmt.order_by(Student.first_name).offset(offset).limit(page_size))

    results = [
        {
            "student_id":  sm.student_id,
            "name":        f"{fn or ''} {ln or ''}".strip(),
            "roll_number": roll,
            "subject":     subj,
            "mark":        float(sm.mark) if sm.mark is not None else None,
            "grade":       gr,
        }
        for sm, fn, ln, roll, subj, gr in result.all()
    ]

    return Result(
        code=200,
        message="Exam results fetched.",
        extra={"total": total, "page": page, "page_size": page_size, "results": results},
    ).http_response()


# ── GET /exams/{timetable_id}/result-entry/ ───────────────────────────────────

@android_teacher_router.get("/exams/{timetable_id}/result-entry/")
async def teacher_exam_result_entry(
    timetable_id: int,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    Returns exam header info + all students in the class with their current mark.
    Powers the "Submit Results" screen (roll list with score inputs).
    """
    _, mappings = await _get_teacher_context(session, db)
    if not mappings:
        return Result(code=403, message="No class mapping.").http_response()

    # Fetch exam timetable row
    et_result = await db.execute(
        select(ExamTimetable, Exam, SchoolStreamSubject.subject_name, SchoolStreamClass.class_name)
        .join(Exam, Exam.exam_id == ExamTimetable.exam_id)
        .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == ExamTimetable.subject_id)
        .outerjoin(SchoolStreamClass, SchoolStreamClass.class_id == ExamTimetable.class_id)
        .where(ExamTimetable.timetable_id == timetable_id)
    )
    et_row = et_result.first()
    if not et_row:
        return Result(code=404, message="Exam timetable entry not found.").http_response()

    et, exam, subject_name, class_name = et_row

    # Check teacher is mapped to this class
    allowed = any(m.class_id == et.class_id for m in mappings)
    if not allowed:
        return Result(code=403, message="Access denied for this exam.").http_response()

    # Fetch students in this class
    students_result = await db.execute(
        select(Student, StudentClassMapping)
        .join(StudentClassMapping, StudentClassMapping.student_id == Student.student_id)
        .where(
            StudentClassMapping.class_id  == et.class_id,
            StudentClassMapping.is_active == True,
        )
        .order_by(Student.student_roll_id, Student.first_name)
    )
    student_rows = students_result.all()
    student_ids = [s.student_id for s, _ in student_rows]

    # Fetch existing marks for this subject + class
    marks_result = await db.execute(
        select(StudentMarks)
        .where(
            StudentMarks.class_id   == et.class_id,
            StudentMarks.subject_id == et.subject_id,
            StudentMarks.student_id.in_(student_ids),
        )
    )
    marks_map = {m.student_id: float(m.mark) for m in marks_result.scalars().all() if m.mark is not None}

    students_list = [
        {
            "student_id":  s.student_id,
            "roll_number": s.student_roll_id,
            "name":        f"{s.first_name or ''} {s.last_name or ''}".strip(),
            "mark":        marks_map.get(s.student_id, None),
        }
        for s, _ in student_rows
    ]

    return Result(
        code=200,
        message="Result entry data fetched.",
        extra={
            "timetable_id": timetable_id,
            "exam_name":    exam.exam_name,
            "subject":      subject_name,
            "class_name":   class_name,
            "max_marks":    float(et.total_marks) if et.total_marks else None,
            "pass_mark":    float(et.pass_mark)   if et.pass_mark   else None,
            "students":     students_list,
        },
    ).http_response()


# ── POST /exams/results/submit/ (Bulk save marks) ─────────────────────────────

@android_teacher_router.post("/exams/results/submit/")
async def teacher_submit_exam_results(
    body: BulkMarksSubmitRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    Upsert marks for all students for a given exam timetable entry.
    Pass records=[{student_id, mark}].
    """
    _, mappings = await _get_teacher_context(session, db)
    if not mappings:
        return Result(code=403, message="No class mapping.").http_response()

    et_result = await db.execute(
        select(ExamTimetable).where(ExamTimetable.timetable_id == body.timetable_id)
    )
    et = et_result.scalar_one_or_none()
    if not et:
        return Result(code=404, message="Exam timetable entry not found.").http_response()

    allowed = any(m.class_id == et.class_id for m in mappings)
    if not allowed:
        return Result(code=403, message="Access denied for this exam.").http_response()

    for entry in body.records:
        existing = await db.execute(
            select(StudentMarks).where(
                StudentMarks.student_id == entry.student_id,
                StudentMarks.class_id   == et.class_id,
                StudentMarks.subject_id == et.subject_id,
            )
        )
        mark_row = existing.scalar_one_or_none()
        if mark_row:
            mark_row.mark = entry.mark
        else:
            db.add(StudentMarks(
                student_id = entry.student_id,
                class_id   = et.class_id,
                subject_id = et.subject_id,
                mark       = entry.mark,
            ))

    await db.commit()
    return Result(
        code=200,
        message=f"Marks saved for {len(body.records)} students.",
        extra={"count": len(body.records)},
    ).http_response()


# ── POST /announcements/ (Create announcement) ───────────────────────────────

@android_teacher_router.post("/announcements/")
async def teacher_create_announcement(
    body: AnnouncementCreateRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    _, mappings = await _get_teacher_context(session, db)
    if not mappings:
        return Result(code=403, message="No class mapping.").http_response()

    # If class_id provided, verify teacher is mapped to it
    if body.class_id is not None:
        allowed = any(m.class_id == body.class_id for m in mappings)
        if not allowed:
            return Result(code=403, message="Access denied for this class.").http_response()

    ann = Announcement(
        class_id    = body.class_id,
        section_id  = body.section_id,
        title       = body.title,
        description = body.description,
        url         = body.url,
        category    = body.category,
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)

    return Result(
        code=200,
        message="Announcement created.",
        extra={
            "id":          ann.id,
            "title":       ann.title,
            "class_id":    ann.class_id,
            "section_id":  ann.section_id,
            "category":    ann.category,
            "date":        ann.created_at.strftime("%b %d, %Y"),
        },
    ).http_response()


# ── PUT /announcements/{id}/ (Edit announcement) ─────────────────────────────

@android_teacher_router.put("/announcements/{ann_id}/")
async def teacher_update_announcement(
    ann_id: int,
    body: AnnouncementUpdateRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    _, mappings = await _get_teacher_context(session, db)
    if not mappings:
        return Result(code=403, message="No class mapping.").http_response()

    result = await db.execute(select(Announcement).where(Announcement.id == ann_id))
    ann = result.scalar_one_or_none()
    if not ann:
        return Result(code=404, message="Announcement not found.").http_response()

    if body.class_id is not None:
        ann.class_id = body.class_id
    if body.section_id is not None:
        ann.section_id = body.section_id
    if body.title is not None:
        ann.title = body.title
    if body.description is not None:
        ann.description = body.description
    if body.url is not None:
        ann.url = body.url
    if body.category is not None:
        ann.category = body.category

    await db.commit()
    return Result(code=200, message="Announcement updated.").http_response()


# ── DELETE /announcements/{id}/ (Delete announcement) ────────────────────────

@android_teacher_router.delete("/announcements/{ann_id}/")
async def teacher_delete_announcement(
    ann_id: int,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    _, mappings = await _get_teacher_context(session, db)
    if not mappings:
        return Result(code=403, message="No class mapping.").http_response()

    result = await db.execute(select(Announcement).where(Announcement.id == ann_id))
    ann = result.scalar_one_or_none()
    if not ann:
        return Result(code=404, message="Announcement not found.").http_response()

    await db.delete(ann)
    await db.commit()
    return Result(code=200, message="Announcement deleted.").http_response()


# ── GET /tasks/ (Teacher's daily tasks / alarms) ─────────────────────────────

@android_teacher_router.get("/tasks/")
async def teacher_tasks(
    class_id:   Optional[int]  = None,
    section_id: Optional[int]  = None,
    task_date:  Optional[date] = None,
    page:       int = 1,
    page_size:  int = 10,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """Returns custom alarm / daily tasks for teacher's classes."""
    _, mappings = await _get_teacher_context(session, db)
    if not mappings:
        return Result(code=200, message="No class mapping.", extra={"tasks": [], "total": 0}).http_response()

    class_ids = list({m.class_id for m in mappings if m.class_id})

    stmt = select(CustomAlarm).where(CustomAlarm.class_id.in_(class_ids))
    if class_id is not None:
        stmt = stmt.where(CustomAlarm.class_id == class_id)
    if section_id is not None:
        stmt = stmt.where(CustomAlarm.section_id == section_id)
    if task_date is not None:
        stmt = stmt.where(CustomAlarm.alarm_date == task_date)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(stmt.order_by(CustomAlarm.alarm_date.desc()).offset(offset).limit(page_size))

    tasks = [
        {
            "id":         t.id,
            "class_id":   t.class_id,
            "section_id": t.section_id,
            "message":    t.message,
            "alarm_date": str(t.alarm_date),
            "slot_time":  t.slot_time,
        }
        for t in result.scalars().all()
    ]

    return Result(
        code=200,
        message="Tasks fetched.",
        extra={"total": total, "page": page, "page_size": page_size, "tasks": tasks},
    ).http_response()


# ── POST /tasks/ (Create daily task / alarm) ─────────────────────────────────

@android_teacher_router.post("/tasks/")
async def teacher_create_task(
    body: DailyTaskCreateRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    Creates a custom alarm / daily task for teacher's class.
    title + message are combined in the message field.
    slot_time accepts any time string (e.g. "09:34").
    """
    _, mappings = await _get_teacher_context(session, db)
    if not mappings:
        return Result(code=403, message="No class mapping.").http_response()

    if body.class_id is not None:
        allowed = any(m.class_id == body.class_id for m in mappings)
        if not allowed:
            return Result(code=403, message="Access denied for this class.").http_response()

    combined_msg = body.title or ""
    if body.message:
        combined_msg = f"{combined_msg}\n{body.message}".strip() if combined_msg else body.message

    task = CustomAlarm(
        class_id   = body.class_id,
        section_id = body.section_id,
        message    = combined_msg or None,
        alarm_date = body.alarm_date,
        slot_time  = body.slot_time,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return Result(
        code=200,
        message="Task created.",
        extra={
            "id":         task.id,
            "class_id":   task.class_id,
            "section_id": task.section_id,
            "message":    task.message,
            "alarm_date": str(task.alarm_date),
            "slot_time":  task.slot_time,
        },
    ).http_response()


# ── GET /profile/ (Teacher profile) ─────────────────────────────────────────

@android_teacher_router.get("/profile/")
async def teacher_profile(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    employee, _ = await _get_teacher_context(session, db)
    if not employee:
        return Result(code=404, message="Teacher not found.").http_response()

    return Result(
        code=200,
        message="Profile fetched.",
        extra={
            "name":          f"{employee.first_name or ''} {employee.last_name or ''}".strip(),
            "first_name":    employee.first_name,
            "last_name":     employee.last_name,
            "emp_id":        employee.emp_id,
            "email":         employee.email,
            "mobile":        employee.mobile,
            "gender":        employee.gender,
            "qualification": employee.qualification,
            "joining_dt":    str(employee.joining_dt) if employee.joining_dt else None,
        },
    ).http_response()


# ── POST /leaves/apply/ (Apply for leave) ────────────────────────────────────

@android_teacher_router.post("/leaves/apply/")
async def teacher_apply_leave(
    body: LeaveApplyRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    if not session.user_id:
        return Result(code=401, message="Session missing user info.").http_response()

    teacher_id = int(session.user_id)

    leave_type = None
    if body.type:
        try:
            leave_type = LeaveTypeEnum(body.type)
        except ValueError:
            return Result(code=400, message=f"Invalid leave type. Use: Full, First Half, Second Half.").http_response()

    leave = EmpLeaveRequest(
        emp_id   = teacher_id,
        reason   = body.reason,
        from_dt  = body.from_dt,
        to_date  = body.to_date,
        type     = leave_type,
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)

    return Result(
        code=200,
        message="Leave request submitted.",
        extra={
            "id":       leave.id,
            "reason":   leave.reason,
            "from_dt":  str(leave.from_dt),
            "to_date":  str(leave.to_date),
            "type":     leave.type,
            "status":   leave.status,
        },
    ).http_response()


# ── GET /leaves/my/ (View own leave requests) ─────────────────────────────────

@android_teacher_router.get("/leaves/my/")
async def teacher_my_leaves(
    page:      int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    if not session.user_id:
        return Result(code=401, message="Session missing user info.").http_response()

    teacher_id = int(session.user_id)

    total_result = await db.execute(
        select(func.count()).select_from(EmpLeaveRequest).where(EmpLeaveRequest.emp_id == teacher_id)
    )
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(EmpLeaveRequest)
        .where(EmpLeaveRequest.emp_id == teacher_id)
        .order_by(EmpLeaveRequest.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    leaves = [
        {
            "id":       l.id,
            "reason":   l.reason,
            "from_dt":  str(l.from_dt),
            "to_date":  str(l.to_date),
            "type":     l.type,
            "status":   l.status,
            "applied":  l.created_at.strftime("%b %d, %Y"),
        }
        for l in result.scalars().all()
    ]

    return Result(
        code=200,
        message="Leave requests fetched.",
        extra={"total": total, "page": page, "page_size": page_size, "leaves": leaves},
    ).http_response()


# ── GET /chat/staff/ (List all staff to start a chat) ────────────────────────

@android_teacher_router.get("/chat/staff/")
async def teacher_chat_staff(
    page:      int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """Returns all active employees (excluding self) as chat contacts."""
    if not session.user_id:
        return Result(code=401, message="Session missing user info.").http_response()

    teacher_id = int(session.user_id)

    total_result = await db.execute(
        select(func.count()).select_from(Employee)
        .where(Employee.id != teacher_id, Employee.is_active == True)
    )
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Employee)
        .where(Employee.id != teacher_id, Employee.is_active == True)
        .order_by(Employee.first_name)
        .offset(offset)
        .limit(page_size)
    )
    staff = [
        {
            "emp_id":     e.id,
            "name":       f"{e.first_name or ''} {e.last_name or ''}".strip(),
            "email":      e.email,
            "mobile":     e.mobile,
        }
        for e in result.scalars().all()
    ]

    return Result(
        code=200,
        message="Staff list fetched.",
        extra={"total": total, "page": page, "page_size": page_size, "staff": staff},
    ).http_response()


# ── GET /chat/conversations/ (Chat inbox — last message per contact) ──────────

@android_teacher_router.get("/chat/conversations/")
async def teacher_chat_conversations(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    Returns all unique conversation partners with their last message preview.
    """
    if not session.user_id:
        return Result(code=401, message="Session missing user info.").http_response()

    teacher_id = int(session.user_id)

    # Get all messages where I am sender or receiver
    result = await db.execute(
        select(ChatMessage)
        .where(
            or_(
                ChatMessage.sender_id   == teacher_id,
                ChatMessage.receiver_id == teacher_id,
            )
        )
        .order_by(ChatMessage.created_at.desc())
    )
    all_msgs = result.scalars().all()

    # Build unique conversation map: other_emp_id → last message
    seen: dict = {}
    for msg in all_msgs:
        other = msg.receiver_id if msg.sender_id == teacher_id else msg.sender_id
        if other not in seen:
            seen[other] = msg

    if not seen:
        return Result(code=200, message="No conversations.", extra={"conversations": []}).http_response()

    # Fetch employee names for conversation partners
    partner_ids = list(seen.keys())
    emp_result = await db.execute(
        select(Employee).where(Employee.id.in_(partner_ids))
    )
    emp_map = {e.id: e for e in emp_result.scalars().all()}

    conversations = []
    for other_id, last_msg in seen.items():
        emp = emp_map.get(other_id)
        conversations.append({
            "emp_id":       other_id,
            "name":         f"{emp.first_name or ''} {emp.last_name or ''}".strip() if emp else str(other_id),
            "last_message": last_msg.message or "Attachment",
            "time":         last_msg.created_at.strftime("%I:%M %p"),
            "is_read":      last_msg.is_read or last_msg.sender_id == teacher_id,
        })

    return Result(
        code=200,
        message="Conversations fetched.",
        extra={"conversations": conversations},
    ).http_response()


# ── GET /chat/messages/{emp_id}/ (Conversation thread) ───────────────────────

@android_teacher_router.get("/chat/messages/{other_emp_id}/")
async def teacher_chat_messages(
    other_emp_id: int,
    page:         int = 1,
    page_size:    int = 30,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """Returns paginated messages between teacher and another staff member."""
    if not session.user_id:
        return Result(code=401, message="Session missing user info.").http_response()

    teacher_id = int(session.user_id)

    thread_filter = or_(
        and_(ChatMessage.sender_id == teacher_id,   ChatMessage.receiver_id == other_emp_id),
        and_(ChatMessage.sender_id == other_emp_id, ChatMessage.receiver_id == teacher_id),
    )

    total_result = await db.execute(select(func.count()).select_from(ChatMessage).where(thread_filter))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(ChatMessage)
        .where(thread_filter)
        .order_by(ChatMessage.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    messages = [
        {
            "id":          m.id,
            "sender_id":   m.sender_id,
            "receiver_id": m.receiver_id,
            "message":     m.message,
            "is_mine":     m.sender_id == teacher_id,
            "is_read":     m.is_read,
            "time":        m.created_at.strftime("%I:%M %p"),
            "date":        m.created_at.strftime("%b %d, %Y"),
        }
        for m in result.scalars().all()
    ]

    # Mark unread messages as read
    await db.execute(
        update(ChatMessage)
        .where(
            ChatMessage.sender_id   == other_emp_id,
            ChatMessage.receiver_id == teacher_id,
            ChatMessage.is_read     == False,
        )
        .values(is_read=True)
    )
    await db.commit()

    return Result(
        code=200,
        message="Messages fetched.",
        extra={"total": total, "page": page, "page_size": page_size, "messages": messages},
    ).http_response()


# ── POST /chat/messages/{emp_id}/ (Send message) ─────────────────────────────

@android_teacher_router.post("/chat/messages/{other_emp_id}/")
async def teacher_send_message(
    other_emp_id: int,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    if not session.user_id:
        return Result(code=401, message="Session missing user info.").http_response()

    teacher_id = int(session.user_id)

    msg = ChatMessage(
        sender_id   = teacher_id,
        receiver_id = other_emp_id,
        message     = body.message,
        is_read     = False,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    return Result(
        code=200,
        message="Message sent.",
        extra={
            "id":      msg.id,
            "message": msg.message,
            "time":    msg.created_at.strftime("%I:%M %p"),
        },
    ).http_response()


# ── GET /micro-schedule/ (List teacher's lesson plans) ────────────────────────

@android_teacher_router.get("/micro-schedule/")
async def teacher_micro_schedule_list(
    class_id:    Optional[int]  = None,
    section_id:  Optional[int]  = None,
    subject_id:  Optional[int]  = None,
    schedule_dt: Optional[date] = None,
    page:        int = 1,
    page_size:   int = 10,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """Returns micro schedule / lesson plans created by this teacher."""
    if not session.user_id:
        return Result(code=401, message="Session missing user info.").http_response()

    teacher_id = int(session.user_id)

    stmt = (
        select(MicroSchedule, SchoolStreamSubject.subject_name,
               SchoolStreamClass.class_name, SchoolStreamClassSection.section_name)
        .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == MicroSchedule.subject_id)
        .outerjoin(SchoolStreamClass,   SchoolStreamClass.class_id     == MicroSchedule.class_id)
        .outerjoin(SchoolStreamClassSection, SchoolStreamClassSection.section_id == MicroSchedule.section_id)
        .where(MicroSchedule.emp_id == teacher_id)
    )
    if class_id is not None:
        stmt = stmt.where(MicroSchedule.class_id == class_id)
    if section_id is not None:
        stmt = stmt.where(MicroSchedule.section_id == section_id)
    if subject_id is not None:
        stmt = stmt.where(MicroSchedule.subject_id == subject_id)
    if schedule_dt is not None:
        stmt = stmt.where(MicroSchedule.schedule_dt == schedule_dt)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        stmt.order_by(MicroSchedule.schedule_dt.desc()).offset(offset).limit(page_size)
    )

    schedules = [
        {
            "id":           ms.id,
            "title":        ms.title,
            "description":  ms.description,
            "class_name":   cls,
            "section_name": sec,
            "subject":      subj,
            "schedule_dt":  str(ms.schedule_dt),
        }
        for ms, subj, cls, sec in result.all()
    ]

    return Result(
        code=200,
        message="Micro schedules fetched.",
        extra={"total": total, "page": page, "page_size": page_size, "schedules": schedules},
    ).http_response()


# ── POST /micro-schedule/ (Create lesson plan) ────────────────────────────────

@android_teacher_router.post("/micro-schedule/")
async def teacher_micro_schedule_create(
    body: MicroScheduleCreateRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    if not session.user_id:
        return Result(code=401, message="Session missing user info.").http_response()

    teacher_id = int(session.user_id)

    ms = MicroSchedule(
        emp_id      = teacher_id,
        class_id    = body.class_id,
        section_id  = body.section_id,
        subject_id  = body.subject_id,
        title       = body.title,
        description = body.description,
        schedule_dt = body.schedule_dt,
    )
    db.add(ms)
    await db.commit()
    await db.refresh(ms)

    return Result(
        code=200,
        message="Micro schedule created.",
        extra={
            "id":          ms.id,
            "title":       ms.title,
            "schedule_dt": str(ms.schedule_dt),
        },
    ).http_response()


# ── PUT /micro-schedule/{id}/ (Update lesson plan) ────────────────────────────

@android_teacher_router.put("/micro-schedule/{ms_id}/")
async def teacher_micro_schedule_update(
    ms_id: int,
    body: MicroScheduleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    if not session.user_id:
        return Result(code=401, message="Session missing user info.").http_response()

    teacher_id = int(session.user_id)

    result = await db.execute(
        select(MicroSchedule).where(MicroSchedule.id == ms_id, MicroSchedule.emp_id == teacher_id)
    )
    ms = result.scalar_one_or_none()
    if not ms:
        return Result(code=404, message="Micro schedule not found.").http_response()

    if body.class_id    is not None: ms.class_id    = body.class_id
    if body.section_id  is not None: ms.section_id  = body.section_id
    if body.subject_id  is not None: ms.subject_id  = body.subject_id
    if body.title       is not None: ms.title       = body.title
    if body.description is not None: ms.description = body.description
    if body.schedule_dt is not None: ms.schedule_dt = body.schedule_dt

    await db.commit()
    return Result(code=200, message="Micro schedule updated.").http_response()


# ── DELETE /micro-schedule/{id}/ (Delete lesson plan) ────────────────────────

@android_teacher_router.delete("/micro-schedule/{ms_id}/")
async def teacher_micro_schedule_delete(
    ms_id: int,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    if not session.user_id:
        return Result(code=401, message="Session missing user info.").http_response()

    teacher_id = int(session.user_id)

    result = await db.execute(
        select(MicroSchedule).where(MicroSchedule.id == ms_id, MicroSchedule.emp_id == teacher_id)
    )
    ms = result.scalar_one_or_none()
    if not ms:
        return Result(code=404, message="Micro schedule not found.").http_response()

    await db.delete(ms)
    await db.commit()
    return Result(code=200, message="Micro schedule deleted.").http_response()
