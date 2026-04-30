# api/android_student.py
from datetime import datetime, date
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, File, Form, UploadFile
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from models.announcement_models import Announcement
from models.assignment_models import Assignment, AssignmentSubmission
from models.attendance_models import StudentAttendance
from models.auth_models import Session
from models.employee_models import Employee, EmployeeClassMapping
from models.exam_models import Exam, ExamTimetable, Grade, OnlineClass, StudentMarks
from models.holiday_models import Holiday
from models.school_stream_models import SchoolStreamClass, SchoolStreamClassSection, SchoolStreamSubject, StatusEnum
from models.student_diary_models import StudentDiary
from models.student_models import Student, StudentClassMapping
from models.timetable_models import TimeTable
from models.chapter_models import Chapter
from models.micro_schedule_models import MicroSchedule
from models.transport_models import Routes, TransportationStudent, VehicleDetails, VehicleRoutesMap
from api.gallery_banner import _save_image
from response.result import Result
from security.valid_session import valid_session

android_student_router = APIRouter(tags=["ANDROID APIS STUDENT"])

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ── Shared helper ──────────────────────────────────────────────────────────────

async def _get_student_context(session: Session, db: AsyncSession):
    """Returns (student, mapping, class_obj, section_obj) or raises on error."""
    if not session.user_id:
        return None, None, None, None

    student_id = int(session.user_id)

    student_result = await db.execute(
        select(Student).where(Student.student_id == student_id)
    )
    student = student_result.scalar_one_or_none()

    mapping_result = await db.execute(
        select(StudentClassMapping).where(
            StudentClassMapping.student_id == student_id,
            StudentClassMapping.is_active == True,
        )
    )
    mapping = mapping_result.scalar_one_or_none()

    if not mapping:
        return student, None, None, None

    class_result = await db.execute(
        select(SchoolStreamClass).where(SchoolStreamClass.class_id == mapping.class_id)
    )
    class_obj = class_result.scalar_one_or_none()

    section_result = await db.execute(
        select(SchoolStreamClassSection).where(SchoolStreamClassSection.section_id == mapping.section_id)
    )
    section_obj = section_result.scalar_one_or_none()

    return student, mapping, class_obj, section_obj


# ── Slot status badge ──────────────────────────────────────────────────────────

def _slot_status(start_time, end_time) -> str:
    now = datetime.now().time()
    if start_time <= now <= end_time:
        return "Live"
    if now < start_time:
        return "Upcoming"
    return "Completed"


# ── Timetable row dict ─────────────────────────────────────────────────────────

def _timetable_row(tt, subject_name, first_name, last_name, include_status: bool = False) -> dict:
    teacher = f"{first_name or ''} {last_name or ''}".strip() or None
    start_str = tt.start_time.strftime("%I:%M %p").lstrip("0") if tt.start_time else None
    end_str   = tt.end_time.strftime("%I:%M %p").lstrip("0")   if tt.end_time   else None
    row = {
        "id":         tt.id,
        "subject":    subject_name,
        "teacher":    teacher,
        "start_time": start_str,
        "end_time":   end_str,
    }
    if include_status:
        row["status"] = _slot_status(tt.start_time, tt.end_time) if tt.start_time and tt.end_time else None
    return row


# ── Timetable query ────────────────────────────────────────────────────────────

async def _query_timetable(db: AsyncSession, class_id: int, section_id: int, day: Optional[str] = None):
    # Subquery to get one emp mapping per timetable slot (avoids duplicate rows)
    from sqlalchemy import literal_column
    emp_subq = (
        select(
            EmployeeClassMapping.class_id,
            EmployeeClassMapping.section_id,
            EmployeeClassMapping.subject_id,
            func.min(EmployeeClassMapping.emp_id).label("emp_id"),
        )
        .group_by(
            EmployeeClassMapping.class_id,
            EmployeeClassMapping.section_id,
            EmployeeClassMapping.subject_id,
        )
        .subquery()
    )

    stmt = (
        select(
            TimeTable,
            SchoolStreamSubject.subject_name,
            Employee.first_name,
            Employee.last_name,
        )
        .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == TimeTable.subject_id)
        .outerjoin(
            emp_subq,
            and_(
                emp_subq.c.class_id   == TimeTable.class_id,
                emp_subq.c.section_id == TimeTable.section_id,
                emp_subq.c.subject_id == TimeTable.subject_id,
            ),
        )
        .outerjoin(Employee, Employee.emp_id == emp_subq.c.emp_id)
        .where(
            TimeTable.class_id   == class_id,
            TimeTable.section_id == section_id,
        )
        .order_by(TimeTable.start_time)
    )
    if day:
        stmt = stmt.where(TimeTable.day == day)

    result = await db.execute(stmt)
    return result.all()


# ── GET /dashboard/ ────────────────────────────────────────────────────────────

@android_student_router.get("/dashboard/")
async def student_dashboard(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    student, mapping, class_obj, section_obj = await _get_student_context(session, db)

    if not student:
        return Result(code=404, message="Student not found.").http_response()
    if not mapping:
        return Result(code=404, message="No active class mapping found.").http_response()

    today_name = datetime.now().strftime("%a")  # "Mon", "Tue" etc — matches DB format
    today_date = date.today()

    # ── Timetable today ──
    tt_rows = await _query_timetable(db, mapping.class_id, mapping.section_id, day=today_name)

    classes_today = [
        _timetable_row(tt, subj, fn, ln, include_status=True)
        for tt, subj, fn, ln in tt_rows
    ]
    timetable_preview = [
        {
            "time":    tt.start_time.strftime("%H:%M") if tt.start_time else None,
            "subject": subj,
            "teacher": f"{fn or ''} {ln or ''}".strip() or None,
        }
        for tt, subj, fn, ln in tt_rows[:5]
    ]

    # ── Notices (latest 3) ──
    notice_result = await db.execute(
        select(Announcement)
        .where(
            or_(
                Announcement.class_id == mapping.class_id,
                Announcement.class_id.is_(None),
            )
        )
        .order_by(Announcement.created_at.desc())
        .limit(3)
    )
    notices_raw = notice_result.scalars().all()
    notices = [
        {
            "id":       n.id,
            "category": n.category,
            "title":    n.title,
            "date":     n.created_at.strftime("%b %d, %Y"),
        }
        for n in notices_raw
    ]

    # ── Online classes ──
    oc_result = await db.execute(
        select(OnlineClass, SchoolStreamSubject.subject_name)
        .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == OnlineClass.subject_id)
        .where(
            OnlineClass.class_id == mapping.class_id,
            OnlineClass.end_date >= today_date,
        )
        .order_by(OnlineClass.start_date)
    )
    online_classes = [
        {
            "id":         oc.id,
            "title":      oc.title,
            "subject":    subj,
            "url":        oc.url,
            "start_date": str(oc.start_date),
            "end_date":   str(oc.end_date),
        }
        for oc, subj in oc_result.all()
    ]

    return Result(
        code=200,
        message="Dashboard fetched.",
        extra={
            "student": {
                "name":         f"{student.first_name or ''} {student.last_name or ''}".strip(),
                "class_name":   class_obj.class_code if class_obj else None,
                "section_name": section_obj.section_code if section_obj else None,
                "roll_number":  student.student_roll_id,
            },
            "classes_today":  classes_today,
            "timetable":      timetable_preview,
            "notices":        notices,
            "online_classes": online_classes,
        },
    ).http_response()


# ── GET /notices/ (View All) ───────────────────────────────────────────────────

@android_student_router.get("/notices/")
async def student_notices(
    page:      int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    _, mapping, _, _ = await _get_student_context(session, db)

    if not mapping:
        return Result(code=404, message="No active class mapping found.").http_response()

    base_filter = or_(
        Announcement.class_id == mapping.class_id,
        Announcement.class_id.is_(None),
    )

    total_result = await db.execute(
        select(func.count()).select_from(Announcement).where(base_filter)
    )
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    notices_result = await db.execute(
        select(Announcement)
        .where(base_filter)
        .order_by(Announcement.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    notices = [
        {
            "id":          n.id,
            "category":    n.category,
            "title":       n.title,
            "description": n.description,
            "url":         n.url,
            "date":        n.created_at.strftime("%b %d, %Y"),
        }
        for n in notices_result.scalars().all()
    ]

    return Result(
        code=200,
        message="Notices fetched.",
        extra={
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "notices":   notices,
        },
    ).http_response()


# ── GET /timetable/ (View All) ─────────────────────────────────────────────────

@android_student_router.get("/timetable/")
async def student_timetable(
    day: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    Returns full timetable grouped by day.
    Pass ?day=Monday to filter to a single day.
    Omit to get the full week.
    """
    _, mapping, _, _ = await _get_student_context(session, db)

    if not mapping:
        return Result(code=404, message="No active class mapping found.").http_response()

    rows = await _query_timetable(db, mapping.class_id, mapping.section_id, day=day)

    grouped: dict = {}
    for tt, subj, fn, ln in rows:
        d = tt.day or "Unknown"
        grouped.setdefault(d, []).append(
            _timetable_row(tt, subj, fn, ln, include_status=(d == datetime.now().strftime("%a")))
        )

    # Sort days in week order
    sorted_timetable = {
        d: grouped[d]
        for d in DAY_ORDER
        if d in grouped
    }
    # Include any non-standard day keys at the end
    for d in grouped:
        if d not in sorted_timetable:
            sorted_timetable[d] = grouped[d]

    return Result(
        code=200,
        message="Timetable fetched.",
        extra={"timetable": sorted_timetable},
    ).http_response()


# ── GET /academics/ ────────────────────────────────────────────────────────────

@android_student_router.get("/academics/")
async def student_academics(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """Returns the subject grid for the student's class."""
    _, mapping, _, _ = await _get_student_context(session, db)

    if not mapping:
        return Result(code=404, message="No active class mapping found.").http_response()

    result = await db.execute(
        select(SchoolStreamSubject)
        .where(
            SchoolStreamSubject.class_id == mapping.class_id,
            SchoolStreamSubject.status   == StatusEnum.active,
        )
        .order_by(SchoolStreamSubject.subject_name)
    )
    subjects = [
        {"subject_id": s.subject_id, "subject_name": s.subject_name, "image_link": s.image_link}
        for s in result.scalars().all()
    ]

    return Result(code=200, message="Subjects fetched.", extra={"subjects": subjects}).http_response()


# ── GET /academics/{subject_id}/chapters/ ─────────────────────────────────────

@android_student_router.get("/academics/{subject_id}/chapters/")
async def student_subject_chapters(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    _, mapping, _, _ = await _get_student_context(session, db)

    if not mapping:
        return Result(code=404, message="No active class mapping found.").http_response()

    result = await db.execute(
        select(Chapter)
        .where(
            Chapter.subject_id == subject_id,
            Chapter.class_id   == mapping.class_id,
        )
        .order_by(Chapter.order, Chapter.id)
    )
    chapters = [
        {
            "id":          c.id,
            "title":       c.title,
            "description": c.description,
            "order":       c.order,
        }
        for c in result.scalars().all()
    ]

    return Result(code=200, message="Chapters fetched.", extra={"subject_id": subject_id, "chapters": chapters}).http_response()


# ── GET /academics/{subject_id}/micro-schedule/ ───────────────────────────────

@android_student_router.get("/academics/{subject_id}/micro-schedule/")
async def student_subject_micro_schedule(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    _, mapping, _, _ = await _get_student_context(session, db)

    if not mapping:
        return Result(code=404, message="No active class mapping found.").http_response()

    result = await db.execute(
        select(MicroSchedule)
        .where(
            MicroSchedule.subject_id  == subject_id,
            MicroSchedule.class_id    == mapping.class_id,
            MicroSchedule.section_id  == mapping.section_id,
        )
        .order_by(MicroSchedule.schedule_dt)
    )
    schedules = [
        {
            "id":          m.id,
            "title":       m.title,
            "description": m.description,
            "date":        str(m.schedule_dt),
        }
        for m in result.scalars().all()
    ]

    return Result(code=200, message="Micro schedule fetched.", extra={"subject_id": subject_id, "micro_schedule": schedules}).http_response()


# ── GET /assignments/ ─────────────────────────────────────────────────────────

@android_student_router.get("/assignments/")
async def student_assignments(
    type:      str = "assigned",   # "assigned" | "submitted"
    page:      int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    Assigned  → assignments for student's class/section not yet submitted.
    Submitted → assignments this student has already submitted.
    """
    student, mapping, _, _ = await _get_student_context(session, db)

    if not student:
        return Result(code=404, message="Student not found.").http_response()
    if not mapping:
        return Result(code=404, message="No active class mapping.").http_response()

    if type == "submitted":
        # JOIN with submission where status = 'submitted'
        stmt = (
            select(Assignment, SchoolStreamSubject.subject_name, AssignmentSubmission)
            .join(
                AssignmentSubmission,
                and_(
                    AssignmentSubmission.assignment_id == Assignment.id,
                    AssignmentSubmission.student_id    == student.student_id,
                    AssignmentSubmission.status        == "submitted",
                ),
            )
            .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == Assignment.subject_id)
            .where(
                Assignment.class_id   == mapping.class_id,
                Assignment.section_id == mapping.section_id,
                Assignment.status     == 1,
            )
            .order_by(AssignmentSubmission.submitted_at.desc())
        )

        total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
        total = total_result.scalar_one()
        offset = (page - 1) * page_size
        rows = (await db.execute(stmt.offset(offset).limit(page_size))).all()

        assignments = [
            {
                "id":           a.id,
                "title":        a.title,
                "subject":      subj,
                "due_date":     str(a.due_date) if a.due_date else None,
                "submitted_at": sub.submitted_at.strftime("%Y-%m-%d %H:%M") if sub.submitted_at else None,
                "image_url":    sub.image_url,
                "description":  sub.description,
            }
            for a, subj, sub in rows
        ]
    else:
        # Assigned: exclude assignments student already submitted
        submitted_subq = (
            select(AssignmentSubmission.assignment_id)
            .where(
                AssignmentSubmission.student_id == student.student_id,
                AssignmentSubmission.status     == "submitted",
            )
            .scalar_subquery()
        )
        stmt = (
            select(Assignment, SchoolStreamSubject.subject_name)
            .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == Assignment.subject_id)
            .where(
                Assignment.class_id   == mapping.class_id,
                Assignment.section_id == mapping.section_id,
                Assignment.status     == 1,
                Assignment.id.not_in(submitted_subq),
            )
            .order_by(Assignment.created_at.desc())
        )

        total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
        total = total_result.scalar_one()
        offset = (page - 1) * page_size
        rows = (await db.execute(stmt.offset(offset).limit(page_size))).all()

        assignments = [
            {
                "id":          a.id,
                "title":       a.title,
                "subject":     subj,
                "description": a.description,
                "due_date":    str(a.due_date) if a.due_date else None,
                "created_at":  a.created_at.strftime("%Y-%m-%d"),
            }
            for a, subj in rows
        ]

    return Result(
        code=200,
        message="Assignments fetched.",
        extra={"type": type, "total": total, "page": page, "page_size": page_size, "assignments": assignments},
    ).http_response()


# ── POST /assignments/{id}/submit/ — student submits an assignment ─────────────

@android_student_router.post("/assignments/{assignment_id}/submit/")
async def student_submit_assignment(
    assignment_id: int,
    description:   Optional[str]         = Form(None),
    file:          Optional[UploadFile]   = File(None),
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    Student submits an assignment.
    - description (optional text)
    - file        (optional image upload)
    Calling again updates the existing submission.
    """
    student, mapping, _, _ = await _get_student_context(session, db)

    if not student:
        return Result(code=404, message="Student not found.").http_response()
    if not mapping:
        return Result(code=404, message="No active class mapping.").http_response()

    # Verify the assignment belongs to student's class/section
    a_result = await db.execute(
        select(Assignment).where(
            Assignment.id         == assignment_id,
            Assignment.class_id   == mapping.class_id,
            Assignment.section_id == mapping.section_id,
            Assignment.status     == 1,
        )
    )
    assignment = a_result.scalar_one_or_none()
    if not assignment:
        return Result(code=404, message="Assignment not found.").http_response()

    # Save uploaded image if provided
    image_url = None
    if file and file.filename:
        image_url = await _save_image(file)

    # Upsert submission
    sub_result = await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id    == student.student_id,
        )
    )
    submission = sub_result.scalar_one_or_none()
    now = datetime.now()

    if submission:
        if description is not None:
            submission.description = description
        if image_url:
            submission.image_url = image_url
        submission.status       = "submitted"
        submission.submitted_at = now
    else:
        submission = AssignmentSubmission(
            assignment_id = assignment_id,
            student_id    = student.student_id,
            description   = description,
            image_url     = image_url,
            status        = "submitted",
            submitted_at  = now,
        )
        db.add(submission)

    await db.commit()
    await db.refresh(submission)

    return Result(
        code=200,
        message="Assignment submitted successfully.",
        extra={
            "id":           submission.id,
            "assignment_id": submission.assignment_id,
            "image_url":    submission.image_url,
            "description":  submission.description,
            "status":       "submitted",
            "submitted_at": submission.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
        },
    ).http_response()


# ── GET /guardian/ ─────────────────────────────────────────────────────────────

@android_student_router.get("/guardian/")
async def student_guardian(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    student, _, _, _ = await _get_student_context(session, db)

    if not student:
        return Result(code=404, message="Student not found.").http_response()

    name = f"{student.guardian_first_name or ''} {student.guardian_last_name or ''}".strip() or None

    return Result(
        code=200,
        message="Guardian details fetched.",
        extra={
            "name":   name,
            "phone":  student.guardian_phone,
            "email":  student.guardian_email,
            "gender": student.guardian_gender.value if student.guardian_gender else None,
        },
    ).http_response()


# ── GET /attendance/ ───────────────────────────────────────────────────────────

@android_student_router.get("/attendance/")
async def student_attendance(
    month:     Optional[int] = None,
    year:      Optional[int] = None,
    page:      int = 1,
    page_size: int = 30,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    student, mapping, _, _ = await _get_student_context(session, db)

    if not student:
        return Result(code=404, message="Student not found.").http_response()

    stmt = select(StudentAttendance).where(
        StudentAttendance.student_id == student.student_id
    )
    if mapping:
        stmt = stmt.where(
            StudentAttendance.class_id   == mapping.class_id,
            StudentAttendance.section_id == mapping.section_id,
        )
    if month:
        stmt = stmt.where(func.month(StudentAttendance.attendance_dt) == month)
    if year:
        stmt = stmt.where(func.year(StudentAttendance.attendance_dt) == year)

    # Summary counts
    all_rows = (await db.execute(stmt)).scalars().all()
    present = sum(1 for r in all_rows if r.status and r.status.value == "P")
    absent  = sum(1 for r in all_rows if r.status and r.status.value == "A")

    # Paginated records
    offset = (page - 1) * page_size
    paged = await db.execute(
        stmt.order_by(StudentAttendance.attendance_dt.desc()).offset(offset).limit(page_size)
    )
    records = [
        {"date": str(r.attendance_dt), "status": r.status.value if r.status else None}
        for r in paged.scalars().all()
    ]

    return Result(
        code=200,
        message="Attendance fetched.",
        extra={
            "summary": {"present": present, "absent": absent, "total": len(all_rows)},
            "page":      page,
            "page_size": page_size,
            "records":   records,
        },
    ).http_response()


# ── GET /exams/ ────────────────────────────────────────────────────────────────

@android_student_router.get("/exams/")
async def student_exams(
    type: str = "all",   # "ongoing" | "upcoming" | "all"
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    type=ongoing  → OnlineExam where start_date <= today <= end_date (Active status)
    type=upcoming → OnlineExam where start_date > today
    type=all      → Exam list (for the result pills / All Exams tab)
    """
    _, mapping, class_obj, _ = await _get_student_context(session, db)

    if not mapping:
        return Result(code=404, message="No active class mapping found.").http_response()

    today_date = date.today()

    if type in ("ongoing", "upcoming"):
        from models.exam_models import OnlineExam
        stmt = (
            select(OnlineExam, SchoolStreamSubject.subject_name)
            .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == OnlineExam.subject_id)
            .where(OnlineExam.class_id == mapping.class_id)
        )
        if type == "ongoing":
            stmt = stmt.where(OnlineExam.start_date <= today_date, OnlineExam.end_date >= today_date)
        else:
            stmt = stmt.where(OnlineExam.start_date > today_date)

        result = await db.execute(stmt.order_by(OnlineExam.start_date))
        exams = [
            {
                "id":         oe.id,
                "title":      oe.title,
                "subject":    subj,
                "exam_code":  oe.exam_code,
                "url":        oe.url,
                "duration":   oe.duration,
                "start_date": str(oe.start_date),
                "end_date":   str(oe.end_date),
                "status":     "Active" if oe.start_date <= today_date <= oe.end_date else "Pending",
            }
            for oe, subj in result.all()
        ]
        return Result(code=200, message="Exams fetched.", extra={"type": type, "exams": exams}).http_response()

    # type == "all" → return distinct Exam list from ExamTimetable for this stream
    stream_id = class_obj.school_stream_id if class_obj else None
    if not stream_id:
        return Result(code=200, message="No stream linked to class.", extra={"exams": []}).http_response()

    result = await db.execute(
        select(Exam)
        .join(ExamTimetable, ExamTimetable.exam_id == Exam.exam_id)
        .where(
            ExamTimetable.school_stream_id == stream_id,
            ExamTimetable.is_active        == True,
            Exam.is_active                 == True,
        )
        .distinct()
        .order_by(Exam.exam_name)
    )
    exams = [
        {"exam_id": e.exam_id, "exam_name": e.exam_name, "session_yr": e.session_yr}
        for e in result.scalars().all()
    ]
    return Result(code=200, message="Exams fetched.", extra={"type": "all", "exams": exams}).http_response()


# ── GET /exams/result/ ─────────────────────────────────────────────────────────

@android_student_router.get("/exams/result/")
async def student_exam_result(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """
    Returns per-subject marks for the student in a specific exam.
    Total marks = sum of ExamTimetable.total_marks for that exam.
    Obtained marks = sum of StudentMarks.mark for matching subjects.
    """
    student, mapping, _, _ = await _get_student_context(session, db)

    if not student:
        return Result(code=404, message="Student not found.").http_response()

    # Fetch exam timetable (subjects + total_marks for this exam)
    et_result = await db.execute(
        select(ExamTimetable, SchoolStreamSubject.subject_name)
        .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == ExamTimetable.subject_id)
        .where(ExamTimetable.exam_id == exam_id, ExamTimetable.is_active == True)
    )
    et_rows = et_result.all()

    if not et_rows:
        return Result(code=404, message="Exam not found.").http_response()

    subject_ids = [et.subject_id for et, _ in et_rows if et.subject_id]

    # Fetch student marks for those subjects
    marks_result = await db.execute(
        select(StudentMarks)
        .where(
            StudentMarks.student_id == student.student_id,
            StudentMarks.subject_id.in_(subject_ids),
        )
    )
    marks_map = {sm.subject_id: sm.mark for sm in marks_result.scalars().all()}

    subjects = []
    total_marks    = 0.0
    obtained_marks = 0.0

    for et, subj_name in et_rows:
        tm = float(et.total_marks) if et.total_marks else 0.0
        ob = float(marks_map.get(et.subject_id, 0) or 0)
        total_marks    += tm
        obtained_marks += ob
        subjects.append({
            "subject":      subj_name,
            "total_marks":  tm,
            "obtained":     ob,
            "pass_mark":    float(et.pass_mark) if et.pass_mark else None,
        })

    # Compute overall grade
    grade_val = None
    if total_marks > 0:
        percentage = (obtained_marks / total_marks) * 100
        grade_result = await db.execute(
            select(Grade.grade)
            .where(
                Grade.start_range <= percentage,
                Grade.end_range   >= percentage,
                Grade.is_active   == True,
            )
        )
        grade_val = grade_result.scalar_one_or_none()

    return Result(
        code=200,
        message="Exam result fetched.",
        extra={
            "student_name":    f"{student.first_name or ''} {student.last_name or ''}".strip(),
            "total_marks":     total_marks,
            "obtained_marks":  obtained_marks,
            "grade":           grade_val,
            "subjects":        subjects,
        },
    ).http_response()


# ── GET /result/ ───────────────────────────────────────────────────────────────

@android_student_router.get("/result/")
async def student_result(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    student, _, _, _ = await _get_student_context(session, db)

    if not student:
        return Result(code=404, message="Student not found.").http_response()

    result = await db.execute(
        select(StudentMarks, SchoolStreamSubject.subject_name, Grade.grade)
        .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == StudentMarks.subject_id)
        .outerjoin(
            Grade,
            and_(
                Grade.start_range <= StudentMarks.mark,
                Grade.end_range   >= StudentMarks.mark,
                Grade.is_active   == True,
            ),
        )
        .where(StudentMarks.student_id == student.student_id)
        .order_by(SchoolStreamSubject.subject_name)
    )
    results = [
        {
            "subject": subj,
            "mark":    float(sm.mark) if sm.mark is not None else None,
            "grade":   grade,
        }
        for sm, subj, grade in result.all()
    ]

    return Result(
        code=200,
        message="Results fetched.",
        extra={"student_id": student.student_id, "results": results},
    ).http_response()


# ── POST /diary/ (My Diary — create entry) ────────────────────────────────────

@android_student_router.post("/diary/")
async def create_diary_entry(
    task_title: str  = Body(...),
    subject_id: Optional[int]  = Body(None),
    diary_date: Optional[date] = Body(None),
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """Student creates a new diary/assignment entry (My Diary tab)."""
    student, mapping, _, _ = await _get_student_context(session, db)

    if not student:
        return Result(code=404, message="Student not found.").http_response()

    entry = StudentDiary(
        student_id = student.student_id,
        class_id   = mapping.class_id   if mapping else None,
        section_id = mapping.section_id if mapping else None,
        subject_id = subject_id,
        task_title = task_title,
        dairy_date = diary_date or date.today(),
        status     = "P",   # Pending
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return Result(
        code=201,
        message="Diary entry created.",
        extra={
            "id":         entry.id,
            "task_title": entry.task_title,
            "diary_date": str(entry.dairy_date),
            "status":     "Pending",
        },
    ).http_response()


# ── GET /diary/ (View Diary — list entries) ────────────────────────────────────

@android_student_router.get("/diary/")
async def student_diary(
    page:      int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    """View Diary tab — all diary entries for this student."""
    student, _, _, _ = await _get_student_context(session, db)

    if not student:
        return Result(code=404, message="Student not found.").http_response()

    base = (
        select(StudentDiary, SchoolStreamSubject.subject_name)
        .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == StudentDiary.subject_id)
        .where(StudentDiary.student_id == student.student_id)
    )

    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    rows = await db.execute(
        base.order_by(StudentDiary.dairy_date.desc()).offset(offset).limit(page_size)
    )

    def _status_label(raw: Optional[str]) -> str:
        if raw == "C":
            return "Completed"
        return "Pending"

    diary = [
        {
            "id":           d.id,
            "task_title":   d.task_title,
            "subject":      subj,
            "diary_date":   str(d.dairy_date) if d.dairy_date else None,
            "status":       _status_label(d.status),
            "submitted_on": d.updated_at.strftime("%d-%m-%Y") if d.updated_at else None,
        }
        for d, subj in rows.all()
    ]

    return Result(
        code=200,
        message="Diary fetched.",
        extra={"total": total, "page": page, "page_size": page_size, "diary": diary},
    ).http_response()


# ── GET /transport/ ────────────────────────────────────────────────────────────

@android_student_router.get("/transport/")
async def student_transport(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(valid_session),
):
    student, mapping, class_obj, section_obj = await _get_student_context(session, db)

    if not student:
        return Result(code=404, message="Student not found.").http_response()

    result = await db.execute(
        select(VehicleDetails, Routes, VehicleRoutesMap)
        .join(TransportationStudent, TransportationStudent.vehicle_id == VehicleDetails.id)
        .outerjoin(VehicleRoutesMap, VehicleRoutesMap.vehicle_id == VehicleDetails.id)
        .outerjoin(Routes, Routes.id == VehicleRoutesMap.route_id)
        .where(TransportationStudent.student_id == student.student_id)
        .limit(1)
    )
    row = result.first()

    if not row:
        return Result(code=404, message="No transport assigned.").http_response()

    veh, route, vrm = row

    def fmt_time(t):
        return t.strftime("%I:%M %p").lstrip("0") if t else None

    class_section = None
    if class_obj and section_obj:
        class_section = f"{class_obj.class_name} - {section_obj.section_name}"

    return Result(
        code=200,
        message="Transport info fetched.",
        extra={
            "student_name":  f"{student.first_name or ''} {student.last_name or ''}".strip(),
            "class_section": class_section,
            "bus_info": {
                "vehicle_no":    veh.vehicle_no,
                "driver_name":   vrm.driver_name   if vrm else None,
                "driver_mobile": vrm.driver_mob_no  if vrm else veh.driver_mob_no,
                "helper_name":   vrm.helper_name   if vrm else None,
                "helper_mobile": vrm.helper_mob_no  if vrm else veh.helper_mob_no,
            },
            "route": {
                "route_name":      route.name              if route else None,
                "pick_start_time": fmt_time(route.pick_start_time) if route else None,
                "pick_end_time":   fmt_time(route.pick_end_time)   if route else None,
                "drop_start_time": fmt_time(route.drop_start_time) if route else None,
                "drop_end_time":   fmt_time(route.drop_end_time)   if route else None,
            },
            # Live tracking fields — update these via a separate tracking service
            "tracking": {
                "starting_point":    None,
                "current_location":  None,
                "destination":       route.name if route else None,
            },
        },
    ).http_response()


# ── GET /holidays/ ─────────────────────────────────────────────────────────────

@android_student_router.get("/holidays/")
async def student_holidays(
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
        extra={"total": total, "page": page, "page_size": page_size, "holidays": holidays},
    ).http_response()
