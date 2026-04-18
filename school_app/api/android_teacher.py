# api/android_teacher.py
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from models.announcement_models import Announcement
from models.attendance_models import StudentAttendance
from models.auth_models import Session
from models.employee_models import Employee, EmployeeClassMapping
from models.holiday_models import Holiday
from models.school_stream_models import SchoolStreamClass, SchoolStreamClassSection, SchoolStreamSubject
from models.student_models import Student, StudentClassMapping
from models.timetable_models import TimeTable
from response.result import Result
from security.valid_session import valid_session

android_teacher_router = APIRouter(tags=["ANDROID APIS TEACHER"])

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


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

    mappings_result = await db.execute(
        select(EmployeeClassMapping).where(EmployeeClassMapping.emp_id == teacher_id)
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

async def _query_teacher_timetable(db: AsyncSession, teacher_id: int, day: Optional[str] = None):
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
                EmployeeClassMapping.emp_id     == teacher_id,
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

    teacher_id = int(session.user_id)
    today_name = datetime.now().strftime("%A")
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
    tt_rows = await _query_teacher_timetable(db, teacher_id, day=today_name)
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
                StudentAttendance.status == "A",
            )
            .order_by(Student.first_name)
        )
        absent_students = [
            {
                "student_id":  sa.student_id,
                "name":        f"{fn or ''} {ln or ''}".strip(),
                "roll_number": roll,
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
    if not session.user_id:
        return Result(code=401, message="Session missing user info.").http_response()

    teacher_id = int(session.user_id)
    rows = await _query_teacher_timetable(db, teacher_id, day=day)

    grouped: dict = {}
    today_name = datetime.now().strftime("%A")
    for tt, subj, cls, sec in rows:
        d = tt.day or "Unknown"
        grouped.setdefault(d, []).append(
            _tt_row(tt, subj, cls, sec, include_status=(d == today_name))
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
