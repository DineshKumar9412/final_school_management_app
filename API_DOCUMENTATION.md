# School Management App — Android API Documentation

## Base Information

| Item | Value |
|------|-------|
| Base URL | `http://<your-server>` |
| Student prefix | `/api/android/student` |
| Teacher prefix | `/api/android/teacher` |
| Auth Header | `client_key: <session_key>` |
| Content-Type | `application/json` |

### Standard Response Envelope
Every endpoint returns:
```json
{
  "code": 200,
  "message": "Success message",
  "data": { }
}
```

### Error Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request / invalid input |
| 401 | Missing or expired session key |
| 403 | Access denied |
| 404 | Resource not found |

---

---

# STUDENT APP

---

## 1. Dashboard

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/dashboard/` |
| **Auth** | `client_key` header required |
| **Description** | Home screen — student info, today's classes, timetable preview, notices, online classes |

**Request Example**
```
GET /api/android/student/dashboard/
client_key: abc123xyz
```

**Response Example**
```json
{
  "code": 200,
  "message": "Dashboard fetched.",
  "data": {
    "student": {
      "name": "Arun Kumar",
      "class_name": "10th Std",
      "section_name": "Sec A",
      "roll_number": "101"
    },
    "classes_today": [
      {
        "id": 1,
        "subject": "Mathematics",
        "teacher": "John Smith",
        "start_time": "8:00 AM",
        "end_time": "9:00 AM",
        "status": "Live"
      }
    ],
    "timetable": [
      { "time": "08:00", "subject": "Mathematics", "teacher": "John Smith" }
    ],
    "notices": [
      { "id": 1, "category": "EVENTS", "title": "Annual Sports Meet", "date": "Feb 14, 2026" }
    ],
    "online_classes": [
      {
        "id": 1,
        "title": "Physics Live Session",
        "subject": "Physics",
        "url": "https://meet.google.com/xyz",
        "start_date": "2026-02-14",
        "end_date": "2026-02-14"
      }
    ]
  }
}
```

**Status field values**
| Value | Meaning |
|-------|---------|
| `Live` | Class is happening right now |
| `Upcoming` | Class is later today |
| `Completed` | Class already finished |

**Category field values**
| Value | Meaning |
|-------|---------|
| `EXAMS` | Exam notice |
| `EVENTS` | School event |
| `CAMPUS` | Campus update |
| `GENERAL` | General notice |

---

## 2. Notices

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/notices/` |
| **Description** | All announcements for this student's class |

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 10 | Items per page |

**Request Example**
```
GET /api/android/student/notices/?page=1&page_size=10
client_key: abc123xyz
```

**Response Example**
```json
{
  "code": 200,
  "message": "Notices fetched.",
  "data": {
    "total": 15,
    "page": 1,
    "page_size": 10,
    "notices": [
      {
        "id": 1,
        "category": "EVENTS",
        "title": "Annual Sports Meet",
        "description": "Registration starts tomorrow at the physical education office.",
        "url": null,
        "date": "Feb 14, 2026"
      }
    ]
  }
}
```

---

## 3. Timetable

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/timetable/` |
| **Description** | Full weekly timetable grouped by day |

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `day` | string | — | e.g. `Monday`. Omit for full week. |

**Request Example**
```
GET /api/android/student/timetable/?day=Monday
client_key: abc123xyz
```

**Response Example**
```json
{
  "code": 200,
  "message": "Timetable fetched.",
  "data": {
    "timetable": {
      "Monday": [
        {
          "id": 1,
          "subject": "Mathematics",
          "teacher": "John Smith",
          "start_time": "8:00 AM",
          "end_time": "9:00 AM",
          "status": "Completed"
        },
        {
          "id": 2,
          "subject": "Physics",
          "teacher": "Sarah Jones",
          "start_time": "9:00 AM",
          "end_time": "10:00 AM",
          "status": "Upcoming"
        }
      ],
      "Tuesday": [ ]
    }
  }
}
```

---

## 4. Academics (Subjects)

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/academics/` |
| **Description** | Subject grid for the student's class |

**Request Example**
```
GET /api/android/student/academics/
client_key: abc123xyz
```

**Response Example**
```json
{
  "code": 200,
  "message": "Subjects fetched.",
  "data": {
    "subjects": [
      { "subject_id": 1, "subject_name": "Mathematics" },
      { "subject_id": 2, "subject_name": "Physics" },
      { "subject_id": 3, "subject_name": "Chemistry" },
      { "subject_id": 4, "subject_name": "English" }
    ]
  }
}
```

---

## 5. Assignments

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/assignments/` |
| **Description** | Student's diary / assignment entries |

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | `assigned` | `assigned` = pending. `submitted` = submitted. |
| `page` | int | 1 | Page number |
| `page_size` | int | 10 | Items per page |

**Request Example**
```
GET /api/android/student/assignments/?type=assigned&page=1
client_key: abc123xyz
```

**Response Example**
```json
{
  "code": 200,
  "message": "Assignments fetched.",
  "data": {
    "type": "assigned",
    "total": 5,
    "page": 1,
    "page_size": 10,
    "assignments": [
      {
        "id": 1,
        "task_title": "Algebra Worksheet #1",
        "subject": "Mathematics",
        "diary_date": "2026-02-20",
        "status": "P"
      }
    ]
  }
}
```

**Status values**
| Value | Meaning |
|-------|---------|
| `P` | Pending |
| `C` | Completed |
| `S` | Submitted |

---

## 6. Guardian Details

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/guardian/` |
| **Description** | Guardian contact information |

**Request Example**
```
GET /api/android/student/guardian/
client_key: abc123xyz
```

**Response Example**
```json
{
  "code": 200,
  "message": "Guardian details fetched.",
  "data": {
    "name": "Ramesh Sharma",
    "phone": "9876543210",
    "email": "ramesh@example.com",
    "gender": "male"
  }
}
```

---

## 7. Attendance

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/attendance/` |
| **Description** | Student's own attendance history with summary |

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `month` | int | — | Filter by month (1–12) |
| `year` | int | — | Filter by year e.g. `2026` |
| `page` | int | 1 | Page number |
| `page_size` | int | 30 | Items per page |

**Request Example**
```
GET /api/android/student/attendance/?month=2&year=2026
client_key: abc123xyz
```

**Response Example**
```json
{
  "code": 200,
  "message": "Attendance fetched.",
  "data": {
    "summary": { "present": 20, "absent": 3, "total": 23 },
    "page": 1,
    "page_size": 30,
    "records": [
      { "date": "2026-02-14", "status": "P" },
      { "date": "2026-02-13", "status": "A" },
      { "date": "2026-02-12", "status": "P" }
    ]
  }
}
```

**Status values**
| Value | Meaning |
|-------|---------|
| `P` | Present |
| `A` | Absent |
| `L` | Leave |

---

## 8. Exams

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/exams/` |
| **Description** | Exam list — supports three modes |

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | `all` | `ongoing` / `upcoming` / `all` |

**Request Example — Ongoing**
```
GET /api/android/student/exams/?type=ongoing
client_key: abc123xyz
```

**Response Example — Ongoing / Upcoming**
```json
{
  "code": 200,
  "message": "Exams fetched.",
  "data": {
    "type": "ongoing",
    "exams": [
      {
        "id": 1,
        "title": "Mid Term Science Quiz",
        "subject": "Science",
        "exam_code": "SCI-001",
        "url": "https://exam.school.com/sci001",
        "duration": "60",
        "start_date": "2026-02-14",
        "end_date": "2026-02-14",
        "status": "Active"
      }
    ]
  }
}
```

**Request Example — All Exams**
```
GET /api/android/student/exams/?type=all
client_key: abc123xyz
```

**Response Example — All Exams**
```json
{
  "code": 200,
  "message": "Exams fetched.",
  "data": {
    "type": "all",
    "exams": [
      { "exam_id": 1, "exam_name": "Final Exam 2026", "session_yr": "2025-26" },
      { "exam_id": 2, "exam_name": "Mid Term 2026",   "session_yr": "2025-26" }
    ]
  }
}
```

---

## 9. Exam Result (by Exam)

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/exams/result/` |
| **Description** | Per-subject marks for a specific exam |

**Query Parameters**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `exam_id` | int | Yes | Use `exam_id` from `/exams/?type=all` |

**Request Example**
```
GET /api/android/student/exams/result/?exam_id=1
client_key: abc123xyz
```

**Response Example**
```json
{
  "code": 200,
  "message": "Exam result fetched.",
  "data": {
    "student_name": "Arun Kumar",
    "total_marks": 500.0,
    "obtained_marks": 432.0,
    "grade": "A",
    "subjects": [
      { "subject": "Mathematics", "total_marks": 100.0, "obtained": 87.0, "pass_mark": 35.0 },
      { "subject": "Physics",     "total_marks": 100.0, "obtained": 79.0, "pass_mark": 35.0 },
      { "subject": "Chemistry",   "total_marks": 100.0, "obtained": 91.0, "pass_mark": 35.0 },
      { "subject": "English",     "total_marks": 100.0, "obtained": 88.0, "pass_mark": 35.0 },
      { "subject": "Biology",     "total_marks": 100.0, "obtained": 87.0, "pass_mark": 35.0 }
    ]
  }
}
```

---

## 10. Result (Overall Marks)

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/result/` |
| **Description** | All marks across all subjects with grade |

**Request Example**
```
GET /api/android/student/result/
client_key: abc123xyz
```

**Response Example**
```json
{
  "code": 200,
  "message": "Results fetched.",
  "data": {
    "student_id": 7,
    "results": [
      { "subject": "Mathematics", "mark": 87.0, "grade": "A" },
      { "subject": "Physics",     "mark": 74.0, "grade": "B" },
      { "subject": "Chemistry",   "mark": 91.0, "grade": "A+" }
    ]
  }
}
```

---

## 11. Diary — Create Entry

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **URL** | `/api/android/student/diary/` |
| **Description** | Student creates a personal diary entry |

**Request Body**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_title` | string | Yes | Task or note title |
| `subject_id` | int | No | Subject ID |
| `diary_date` | string `YYYY-MM-DD` | No | Defaults to today |

**Request Example**
```
POST /api/android/student/diary/
client_key: abc123xyz
Content-Type: application/json

{
  "task_title": "Read chapter 5",
  "subject_id": 1,
  "diary_date": "2026-02-20"
}
```

**Response Example**
```json
{
  "code": 201,
  "message": "Diary entry created.",
  "data": {
    "id": 12,
    "task_title": "Read chapter 5",
    "diary_date": "2026-02-20",
    "status": "Pending"
  }
}
```

---

## 12. Diary — View Entries

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/diary/` |
| **Description** | All diary entries for this student |

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 10 | Items per page |

**Request Example**
```
GET /api/android/student/diary/?page=1
client_key: abc123xyz
```

**Response Example**
```json
{
  "code": 200,
  "message": "Diary fetched.",
  "data": {
    "total": 8,
    "page": 1,
    "page_size": 10,
    "diary": [
      {
        "id": 12,
        "task_title": "Read chapter 5",
        "subject": "Physics",
        "diary_date": "2026-02-20",
        "status": "Pending",
        "submitted_on": "20-02-2026"
      }
    ]
  }
}
```

---

## 13. Transport

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/transport/` |
| **Description** | Assigned bus and route details |

**Request Example**
```
GET /api/android/student/transport/
client_key: abc123xyz
```

**Response Example**
```json
{
  "code": 200,
  "message": "Transport info fetched.",
  "data": {
    "student_name": "Arun Kumar",
    "class_section": "10th Std - Sec A",
    "bus_info": {
      "vehicle_no": "TN01AB1234",
      "driver_name": "John",
      "driver_mobile": "9876543210",
      "helper_name": "Ravi",
      "helper_mobile": "9123456789"
    },
    "route": {
      "route_name": "Route A",
      "pick_start_time": "7:30 AM",
      "pick_end_time": "8:30 AM",
      "drop_start_time": "3:30 PM",
      "drop_end_time": "4:30 PM"
    },
    "tracking": {
      "starting_point": null,
      "current_location": null,
      "destination": "Route A"
    }
  }
}
```

---

## 14. Holidays

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/student/holidays/` |
| **Description** | Upcoming holidays |

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 10 | Items per page |

**Request Example**
```
GET /api/android/student/holidays/?page=1
client_key: abc123xyz
```

**Response Example**
```json
{
  "code": 200,
  "message": "Holidays fetched.",
  "data": {
    "total": 5,
    "page": 1,
    "page_size": 10,
    "holidays": [
      {
        "id": 1,
        "title": "Republic Day",
        "description": "National holiday",
        "date": "2026-01-26",
        "day": "26",
        "month": "Jan"
      }
    ]
  }
}
```

---

---

# TEACHER APP

---

## 1. Dashboard

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/dashboard/` |
| **Description** | Home screen — teacher info, today's timetable, announcements, absent students, holidays |

**Request Example**
```
GET /api/android/teacher/dashboard/
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Dashboard fetched.",
  "data": {
    "teacher": {
      "name": "John Smith",
      "emp_id": 101
    },
    "total_students": 45,
    "timetable_today": [
      {
        "id": 1,
        "subject": "Mathematics",
        "class_name": "10th Std",
        "section_name": "Sec A",
        "start_time": "8:00 AM",
        "end_time": "9:00 AM",
        "status": "Live"
      }
    ],
    "announcements": [
      { "id": 1, "category": "EVENTS", "title": "Sports Meet", "date": "Feb 14, 2026" }
    ],
    "leaves": {
      "absent_count": 2,
      "everyone_present": false,
      "absent_students": [
        { "student_id": 8, "name": "Bhavya Sri", "roll_number": "102", "status": "A" }
      ]
    },
    "holidays": [
      { "id": 1, "title": "Republic Day", "description": "National holiday", "date": "2026-01-26", "day": "26", "month": "Jan" }
    ]
  }
}
```

---

## 2. Profile

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/profile/` |
| **Description** | Teacher's profile details |

**Request Example**
```
GET /api/android/teacher/profile/
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Profile fetched.",
  "data": {
    "name": "John Smith",
    "first_name": "John",
    "last_name": "Smith",
    "emp_id": 101,
    "email": "john@school.com",
    "mobile": "9876543210",
    "gender": "male",
    "qualification": "M.Sc Mathematics",
    "joining_dt": "2020-06-01"
  }
}
```

---

## 3. Timetable

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/timetable/` |
| **Description** | Teacher's full weekly timetable |

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `day` | string | — | e.g. `Monday`. Omit for full week. |

**Request Example**
```
GET /api/android/teacher/timetable/?day=Monday
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Timetable fetched.",
  "data": {
    "timetable": {
      "Monday": [
        {
          "id": 1,
          "subject": "Mathematics",
          "class_name": "10th Std",
          "section_name": "Sec A",
          "start_time": "8:00 AM",
          "end_time": "9:00 AM",
          "status": "Live"
        }
      ],
      "Wednesday": [ ]
    }
  }
}
```

---

## 4. Students — List

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/students/` |
| **Description** | All students in the teacher's classes |

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `class_id` | int | — | Filter by class |
| `section_id` | int | — | Filter by section |
| `page` | int | 1 | Page number |
| `page_size` | int | 10 | Items per page |

**Request Example**
```
GET /api/android/teacher/students/?class_id=1&section_id=2&page=1
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Students fetched.",
  "data": {
    "total": 35,
    "page": 1,
    "page_size": 10,
    "students": [
      { "student_id": 7,  "name": "Arun Kumar",   "roll_number": "101", "class_name": "10th Std", "section_name": "Sec A" },
      { "student_id": 8,  "name": "Bhavya Sri",   "roll_number": "102", "class_name": "10th Std", "section_name": "Sec A" },
      { "student_id": 9,  "name": "Deepak Raj",   "roll_number": "103", "class_name": "10th Std", "section_name": "Sec A" }
    ]
  }
}
```

---

## 5. Students — Detail

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/students/{student_id}/` |
| **Description** | Full profile of a single student |

**Request Example**
```
GET /api/android/teacher/students/7/
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Student detail fetched.",
  "data": {
    "student_id": 7,
    "roll_number": "101",
    "first_name": "Arun",
    "last_name": "Kumar",
    "gender": "male",
    "dob": "2010-05-12",
    "age": 15,
    "email": "arun@example.com",
    "phone": "9876543210",
    "blood_group": "B+",
    "class_name": "10th Std",
    "section_name": "Sec A",
    "guardian": {
      "name": "Ramesh Kumar",
      "phone": "9876500000",
      "email": "ramesh@example.com",
      "gender": "male"
    }
  }
}
```

---

## 6. Attendance — Load Sheet

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/attendance/students/` |
| **Description** | Load students with their current attendance status for a date. Call this first to show the P / A / L toggle list. |

**Query Parameters**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `class_id` | int | Yes | |
| `section_id` | int | Yes | |
| `att_date` | string `YYYY-MM-DD` | No | Defaults to today |

**Request Example**
```
GET /api/android/teacher/attendance/students/?class_id=1&section_id=2&att_date=2026-02-14
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Attendance list fetched.",
  "data": {
    "class_id": 1,
    "section_id": 2,
    "date": "2026-02-14",
    "students": [
      { "student_id": 7, "name": "Arun Kumar",   "roll_number": "101", "status": "P"    },
      { "student_id": 8, "name": "Bhavya Sri",   "roll_number": "102", "status": "A"    },
      { "student_id": 9, "name": "Deepak Raj",   "roll_number": "103", "status": null   },
      { "student_id": 10,"name": "Ishani M",     "roll_number": "104", "status": "L"    }
    ]
  }
}
```

> `status: null` — attendance not marked yet for that student.

---

## 7. Attendance — Save

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **URL** | `/api/android/teacher/attendance/` |
| **Description** | Save / update attendance for an entire class on a given date. Replaces all existing records for that class + section + date. |

**Request Body**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `class_id` | int | Yes | |
| `section_id` | int | Yes | |
| `date` | string `YYYY-MM-DD` | Yes | |
| `records` | array | Yes | Array of `{student_id, status}` |

**Status values**
| Value | Meaning |
|-------|---------|
| `P` | Present |
| `A` | Absent |
| `L` | Leave |

**Request Example**
```
POST /api/android/teacher/attendance/
client_key: teacher_session_key
Content-Type: application/json

{
  "class_id": 1,
  "section_id": 2,
  "date": "2026-02-14",
  "records": [
    { "student_id": 7,  "status": "P" },
    { "student_id": 8,  "status": "A" },
    { "student_id": 9,  "status": "P" },
    { "student_id": 10, "status": "L" }
  ]
}
```

**Response Example**
```json
{
  "code": 200,
  "message": "Attendance saved for 4 students.",
  "data": {
    "date": "2026-02-14",
    "count": 4
  }
}
```

---

## 8. Attendance — Summary

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/attendance/` |
| **Description** | Attendance summary grouped by date |

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `class_id` | int | — | Filter by class |
| `section_id` | int | — | Filter by section |
| `month` | int | — | Filter by month (1–12) |
| `year` | int | — | Filter by year |
| `page` | int | 1 | Page number |
| `page_size` | int | 30 | Items per page |

**Request Example**
```
GET /api/android/teacher/attendance/?class_id=1&section_id=2&month=2&year=2026
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Attendance summary fetched.",
  "data": {
    "page": 1,
    "page_size": 30,
    "records": [
      { "date": "2026-02-14", "total": 38, "present": 32, "absent": 4, "leave": 2 },
      { "date": "2026-02-13", "total": 38, "present": 35, "absent": 3, "leave": 0 }
    ]
  }
}
```

---

## 9. Absent Students (Leaves View)

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/leaves/` |
| **Description** | List absent students for a specific date |

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `leave_date` | string `YYYY-MM-DD` | today | |
| `page` | int | 1 | Page number |
| `page_size` | int | 10 | Items per page |

**Request Example**
```
GET /api/android/teacher/leaves/?leave_date=2026-02-14
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Absent students fetched.",
  "data": {
    "date": "2026-02-14",
    "total": 2,
    "everyone_present": false,
    "absent": [
      { "student_id": 8, "name": "Bhavya Sri", "roll_number": "102", "class_name": "10th Std", "section_name": "Sec A" }
    ]
  }
}
```

---

## 10. Assignments — List

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/assignments/` |
| **Description** | View all assignment entries across teacher's classes |

**Query Parameters**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `class_id` | int | — | Filter by class |
| `section_id` | int | — | Filter by section |
| `page` | int | 1 | Page number |
| `page_size` | int | 10 | Items per page |

**Request Example**
```
GET /api/android/teacher/assignments/?class_id=1&section_id=2
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Assignments fetched.",
  "data": {
    "total": 12,
    "page": 1,
    "page_size": 10,
    "assignments": [
      {
        "id": 1,
        "task_title": "Algebra Worksheet #1\nComplete exercises 1–10 from chapter 3.",
        "subject": "Mathematics",
        "student_name": "Arun Kumar",
        "diary_date": "2026-02-20",
        "status": "Pending"
      }
    ]
  }
}
```

---

## 11. Assignments — Create

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **URL** | `/api/android/teacher/assignments/` |
| **Description** | Create an assignment for every student in a class/section at once |

**Request Body**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `class_id` | int | Yes | |
| `section_id` | int | Yes | |
| `subject_id` | int | No | |
| `task_title` | string | No | Short title |
| `description` | string | No | Full instructions |
| `diary_date` | string `YYYY-MM-DD` | No | Due date. Defaults to today |

**Request Example**
```
POST /api/android/teacher/assignments/
client_key: teacher_session_key
Content-Type: application/json

{
  "class_id": 1,
  "section_id": 2,
  "subject_id": 3,
  "task_title": "Algebra Worksheet #1",
  "description": "Complete exercises 1–10 from chapter 3.",
  "diary_date": "2026-02-20"
}
```

**Response Example**
```json
{
  "code": 200,
  "message": "Assignment created for 35 students.",
  "data": { "count": 35 }
}
```

---

## 12. Assignments — Update

| Item | Value |
|------|-------|
| **Method** | `PUT` |
| **URL** | `/api/android/teacher/assignments/{id}/` |
| **Description** | Edit a single diary/assignment entry |

**Request Example**
```
PUT /api/android/teacher/assignments/1/
client_key: teacher_session_key
Content-Type: application/json

{
  "task_title": "Updated Worksheet #1",
  "description": "Complete all exercises.",
  "diary_date": "2026-02-22"
}
```

**Response Example**
```json
{ "code": 200, "message": "Assignment updated." }
```

---

## 13. Assignments — Delete

| Item | Value |
|------|-------|
| **Method** | `DELETE` |
| **URL** | `/api/android/teacher/assignments/{id}/` |

**Request Example**
```
DELETE /api/android/teacher/assignments/1/
client_key: teacher_session_key
```

**Response Example**
```json
{ "code": 200, "message": "Assignment deleted." }
```

---

## 14. Announcements — List

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/announcements/` |

**Query Parameters:** `page`, `page_size`

**Request Example**
```
GET /api/android/teacher/announcements/?page=1
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Announcements fetched.",
  "data": {
    "total": 5,
    "page": 1,
    "page_size": 10,
    "announcements": [
      {
        "id": 1,
        "category": "CAMPUS",
        "title": "Holiday Due to Weather",
        "description": "Due to heavy rain today is a holiday. Stay safe at home.",
        "url": null,
        "date": "Feb 15, 2026"
      }
    ]
  }
}
```

---

## 15. Announcements — Create

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **URL** | `/api/android/teacher/announcements/` |

**Request Body**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `class_id` | int | No | `null` = visible to all classes |
| `section_id` | int | No | |
| `title` | string | No | |
| `description` | string | No | |
| `url` | string | No | External link |
| `category` | string | No | `EXAMS` / `EVENTS` / `CAMPUS` / `GENERAL` |

**Request Example**
```
POST /api/android/teacher/announcements/
client_key: teacher_session_key
Content-Type: application/json

{
  "class_id": 1,
  "section_id": 2,
  "title": "Holiday Due to Weather",
  "description": "Due to heavy rain today is a holiday.",
  "category": "CAMPUS"
}
```

**Response Example**
```json
{
  "code": 200,
  "message": "Announcement created.",
  "data": {
    "id": 10,
    "title": "Holiday Due to Weather",
    "class_id": 1,
    "section_id": 2,
    "category": "CAMPUS",
    "date": "Feb 15, 2026"
  }
}
```

---

## 16. Announcements — Update

| Item | Value |
|------|-------|
| **Method** | `PUT` |
| **URL** | `/api/android/teacher/announcements/{id}/` |

**Request Example**
```
PUT /api/android/teacher/announcements/10/
client_key: teacher_session_key
Content-Type: application/json

{ "title": "Updated Title", "category": "GENERAL" }
```

**Response Example**
```json
{ "code": 200, "message": "Announcement updated." }
```

---

## 17. Announcements — Delete

| Item | Value |
|------|-------|
| **Method** | `DELETE` |
| **URL** | `/api/android/teacher/announcements/{id}/` |

**Request Example**
```
DELETE /api/android/teacher/announcements/10/
client_key: teacher_session_key
```

**Response Example**
```json
{ "code": 200, "message": "Announcement deleted." }
```

---

## 18. Exams — Schedule

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/exams/` |
| **Description** | Exam schedule for all classes the teacher is mapped to |

**Request Example**
```
GET /api/android/teacher/exams/
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Exam schedule fetched.",
  "data": {
    "exams": [
      {
        "timetable_id": 5,
        "exam_name": "Final Exam 2026",
        "subject": "Mathematics",
        "class_name": "10th Std",
        "start_date": "2026-03-10",
        "end_date": "2026-03-10",
        "total_marks": 100.0,
        "pass_mark": 35.0
      }
    ]
  }
}
```

---

## 19. Exams — Result Entry Screen

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/exams/{timetable_id}/result-entry/` |
| **Description** | Load student list with current marks for a specific exam subject. Use `timetable_id` from `/exams/`. |

**Request Example**
```
GET /api/android/teacher/exams/5/result-entry/
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Result entry data fetched.",
  "data": {
    "timetable_id": 5,
    "exam_name": "Final Exam 2026",
    "subject": "Mathematics",
    "class_name": "10-A",
    "max_marks": 100.0,
    "pass_mark": 35.0,
    "students": [
      { "student_id": 7,  "roll_number": "101", "name": "Brian Miller",    "mark": null  },
      { "student_id": 8,  "roll_number": "102", "name": "Amanda Robinson", "mark": 87.0  },
      { "student_id": 9,  "roll_number": "103", "name": "Percy NDEMBET",   "mark": null  },
      { "student_id": 10, "roll_number": "104", "name": "Jessica White",   "mark": null  }
    ]
  }
}
```

> `mark: null` — marks not entered yet. Show `00` in the UI.

---

## 20. Exams — Submit Results

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **URL** | `/api/android/teacher/exams/results/submit/` |
| **Description** | Bulk save / update marks for all students in one call |

**Request Body**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timetable_id` | int | Yes | From `/exams/` |
| `records` | array | Yes | Array of `{student_id, mark}` |

**Request Example**
```
POST /api/android/teacher/exams/results/submit/
client_key: teacher_session_key
Content-Type: application/json

{
  "timetable_id": 5,
  "records": [
    { "student_id": 7,  "mark": 78 },
    { "student_id": 8,  "mark": 92 },
    { "student_id": 9,  "mark": 65 },
    { "student_id": 10, "mark": 88 }
  ]
}
```

**Response Example**
```json
{
  "code": 200,
  "message": "Marks saved for 4 students.",
  "data": { "count": 4 }
}
```

---

## 21. Exams — View All Results

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/exams/results/` |
| **Description** | All student marks across teacher's classes |

**Query Parameters:** `class_id`, `section_id`, `subject_id`, `page`, `page_size`

**Request Example**
```
GET /api/android/teacher/exams/results/?class_id=1&subject_id=3
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Exam results fetched.",
  "data": {
    "total": 35,
    "page": 1,
    "page_size": 20,
    "results": [
      { "student_id": 7,  "name": "Arun Kumar",   "roll_number": "101", "subject": "Mathematics", "mark": 87.0, "grade": "A" },
      { "student_id": 8,  "name": "Bhavya Sri",   "roll_number": "102", "subject": "Mathematics", "mark": 65.0, "grade": "B" }
    ]
  }
}
```

---

## 22. Daily Tasks — List

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/tasks/` |
| **Description** | Custom alarm / daily tasks for teacher's classes |

**Query Parameters:** `class_id`, `section_id`, `task_date (YYYY-MM-DD)`, `page`, `page_size`

**Request Example**
```
GET /api/android/teacher/tasks/?class_id=1
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Tasks fetched.",
  "data": {
    "total": 3,
    "page": 1,
    "page_size": 10,
    "tasks": [
      {
        "id": 1,
        "class_id": 1,
        "section_id": 2,
        "message": "Morning Assembly\nRemind students to bring permission slips.",
        "alarm_date": "2026-02-14",
        "slot_time": "08:00"
      }
    ]
  }
}
```

---

## 23. Daily Tasks — Create

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **URL** | `/api/android/teacher/tasks/` |

**Request Body**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `class_id` | int | No | |
| `section_id` | int | No | |
| `title` | string | No | Task name |
| `message` | string | No | Notification body |
| `alarm_date` | string `YYYY-MM-DD` | Yes | |
| `slot_time` | string | No | e.g. `"09:34"` |

**Request Example**
```
POST /api/android/teacher/tasks/
client_key: teacher_session_key
Content-Type: application/json

{
  "class_id": 1,
  "section_id": 2,
  "title": "Morning Assembly",
  "message": "Remind students to bring permission slips.",
  "alarm_date": "2026-02-14",
  "slot_time": "09:34"
}
```

**Response Example**
```json
{
  "code": 200,
  "message": "Task created.",
  "data": {
    "id": 5,
    "class_id": 1,
    "section_id": 2,
    "message": "Morning Assembly\nRemind students to bring permission slips.",
    "alarm_date": "2026-02-14",
    "slot_time": "09:34"
  }
}
```

---

## 24. Micro Schedule — List

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/micro-schedule/` |
| **Description** | Teacher's lesson plans |

**Query Parameters:** `class_id`, `section_id`, `subject_id`, `schedule_dt (YYYY-MM-DD)`, `page`, `page_size`

**Request Example**
```
GET /api/android/teacher/micro-schedule/?class_id=1&subject_id=3
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Micro schedules fetched.",
  "data": {
    "total": 5,
    "page": 1,
    "page_size": 10,
    "schedules": [
      {
        "id": 1,
        "title": "Introduction to Quadratic Equations",
        "description": "Cover sections 3.1 to 3.3. Use visual method on board.",
        "class_name": "10th Std",
        "section_name": "Sec A",
        "subject": "Mathematics",
        "schedule_dt": "2026-02-14"
      }
    ]
  }
}
```

---

## 25. Micro Schedule — Create

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **URL** | `/api/android/teacher/micro-schedule/` |

**Request Body**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `class_id` | int | No | |
| `section_id` | int | No | |
| `subject_id` | int | No | |
| `title` | string | No | Lesson topic |
| `description` | string | No | Teaching plan notes |
| `schedule_dt` | string `YYYY-MM-DD` | Yes | |

**Request Example**
```
POST /api/android/teacher/micro-schedule/
client_key: teacher_session_key
Content-Type: application/json

{
  "class_id": 1,
  "section_id": 2,
  "subject_id": 3,
  "title": "Introduction to Quadratic Equations",
  "description": "Cover sections 3.1 to 3.3. Use visual method on board.",
  "schedule_dt": "2026-02-14"
}
```

**Response Example**
```json
{
  "code": 200,
  "message": "Micro schedule created.",
  "data": { "id": 1, "title": "Introduction to Quadratic Equations", "schedule_dt": "2026-02-14" }
}
```

---

## 26. Micro Schedule — Update

| Item | Value |
|------|-------|
| **Method** | `PUT` |
| **URL** | `/api/android/teacher/micro-schedule/{id}/` |
| **Description** | All fields optional |

**Request Example**
```
PUT /api/android/teacher/micro-schedule/1/
client_key: teacher_session_key
Content-Type: application/json

{ "title": "Quadratic Equations — Revised", "description": "Also cover section 3.4." }
```

**Response Example**
```json
{ "code": 200, "message": "Micro schedule updated." }
```

---

## 27. Micro Schedule — Delete

| Item | Value |
|------|-------|
| **Method** | `DELETE` |
| **URL** | `/api/android/teacher/micro-schedule/{id}/` |

**Request Example**
```
DELETE /api/android/teacher/micro-schedule/1/
client_key: teacher_session_key
```

**Response Example**
```json
{ "code": 200, "message": "Micro schedule deleted." }
```

---

## 28. Leave — Apply

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **URL** | `/api/android/teacher/leaves/apply/` |
| **Description** | Teacher applies for leave |

**Request Body**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string | Yes | |
| `from_dt` | string `YYYY-MM-DD` | Yes | Start date |
| `to_date` | string `YYYY-MM-DD` | Yes | End date |
| `type` | string | No | `Full` / `First Half` / `Second Half` |

**Request Example**
```
POST /api/android/teacher/leaves/apply/
client_key: teacher_session_key
Content-Type: application/json

{
  "reason": "Personal work",
  "from_dt": "2026-02-20",
  "to_date": "2026-02-21",
  "type": "Full"
}
```

**Response Example**
```json
{
  "code": 200,
  "message": "Leave request submitted.",
  "data": {
    "id": 10,
    "reason": "Personal work",
    "from_dt": "2026-02-20",
    "to_date": "2026-02-21",
    "type": "Full",
    "status": "Pending"
  }
}
```

---

## 29. Leave — My History

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/leaves/my/` |
| **Description** | Teacher's own leave request history |

**Query Parameters:** `page`, `page_size`

**Request Example**
```
GET /api/android/teacher/leaves/my/?page=1
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Leave requests fetched.",
  "data": {
    "total": 3,
    "page": 1,
    "page_size": 10,
    "leaves": [
      {
        "id": 10,
        "reason": "Personal work",
        "from_dt": "2026-02-20",
        "to_date": "2026-02-21",
        "type": "Full",
        "status": "Pending",
        "applied": "Feb 18, 2026"
      }
    ]
  }
}
```

**Status values:** `Pending` / `Approved` / `Rejected`

---

## 30. Chat — Staff List

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/chat/staff/` |
| **Description** | All active staff members (used on Staffs tab to start a new chat) |

**Query Parameters:** `page`, `page_size`

**Request Example**
```
GET /api/android/teacher/chat/staff/
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Staff list fetched.",
  "data": {
    "total": 12,
    "staff": [
      { "emp_id": 5, "name": "Sarah Jones", "email": "sarah@school.com", "mobile": "9000000001" },
      { "emp_id": 6, "name": "Brian Miller","email": "brian@school.com", "mobile": "9000000002" }
    ]
  }
}
```

---

## 31. Chat — Conversations Inbox

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/chat/conversations/` |
| **Description** | All conversations with last message preview — powers the Chat screen list |

**Request Example**
```
GET /api/android/teacher/chat/conversations/
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Conversations fetched.",
  "data": {
    "conversations": [
      { "emp_id": 5, "name": "Brian Miller",       "last_message": "hi",         "time": "12:57 PM", "is_read": true  },
      { "emp_id": 6, "name": "Amanda Robinson",    "last_message": "school1@gmail.com", "time": "09:05 AM", "is_read": false },
      { "emp_id": 7, "name": "Percy NDEMBET",      "last_message": "hlo",        "time": "07:49 AM", "is_read": true  },
      { "emp_id": 8, "name": "محمد ارشد عزیز",   "last_message": "Attachment", "time": "11:36 AM", "is_read": false }
    ]
  }
}
```

---

## 32. Chat — Message Thread

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/chat/messages/{emp_id}/` |
| **Description** | Full message thread with a staff member. Automatically marks received messages as read. |

**Query Parameters:** `page`, `page_size` (default 30, ordered oldest → newest)

**Request Example**
```
GET /api/android/teacher/chat/messages/5/
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Messages fetched.",
  "data": {
    "total": 10,
    "page": 1,
    "page_size": 30,
    "messages": [
      {
        "id": 1,
        "sender_id": 3,
        "receiver_id": 5,
        "message": "hi",
        "is_mine": true,
        "is_read": true,
        "time": "12:57 PM",
        "date": "Feb 14, 2026"
      },
      {
        "id": 2,
        "sender_id": 5,
        "receiver_id": 3,
        "message": "Hello! How are you?",
        "is_mine": false,
        "is_read": true,
        "time": "12:58 PM",
        "date": "Feb 14, 2026"
      }
    ]
  }
}
```

> `is_mine: true` — message was sent by the logged-in teacher. Use this to align messages (right = mine, left = theirs).

---

## 33. Chat — Send Message

| Item | Value |
|------|-------|
| **Method** | `POST` |
| **URL** | `/api/android/teacher/chat/messages/{emp_id}/` |
| **Description** | Send a message to another staff member |

**Request Body**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | Message text |

**Request Example**
```
POST /api/android/teacher/chat/messages/5/
client_key: teacher_session_key
Content-Type: application/json

{ "message": "Can we reschedule the meeting?" }
```

**Response Example**
```json
{
  "code": 200,
  "message": "Message sent.",
  "data": {
    "id": 42,
    "message": "Can we reschedule the meeting?",
    "time": "09:34 AM"
  }
}
```

---

## 34. Holidays

| Item | Value |
|------|-------|
| **Method** | `GET` |
| **URL** | `/api/android/teacher/holidays/` |
| **Description** | Upcoming holidays |

**Query Parameters:** `page`, `page_size`

**Request Example**
```
GET /api/android/teacher/holidays/?page=1
client_key: teacher_session_key
```

**Response Example**
```json
{
  "code": 200,
  "message": "Holidays fetched.",
  "data": {
    "total": 5,
    "page": 1,
    "page_size": 10,
    "holidays": [
      { "id": 1, "title": "Republic Day", "description": "National holiday", "date": "2026-01-26", "day": "26", "month": "Jan" }
    ]
  }
}
```

---

---

# Quick Reference

## Student App Endpoints

| # | Method | URL | Description |
|---|--------|-----|-------------|
| 1 | GET | `/api/android/student/dashboard/` | Home screen |
| 2 | GET | `/api/android/student/notices/` | Announcements |
| 3 | GET | `/api/android/student/timetable/` | Weekly timetable |
| 4 | GET | `/api/android/student/academics/` | Subject grid |
| 5 | GET | `/api/android/student/assignments/` | Assignments list |
| 6 | GET | `/api/android/student/guardian/` | Guardian info |
| 7 | GET | `/api/android/student/attendance/` | Attendance history |
| 8 | GET | `/api/android/student/exams/` | Exam list |
| 9 | GET | `/api/android/student/exams/result/` | Result by exam |
| 10 | GET | `/api/android/student/result/` | Overall marks |
| 11 | POST | `/api/android/student/diary/` | Create diary entry |
| 12 | GET | `/api/android/student/diary/` | View diary |
| 13 | GET | `/api/android/student/transport/` | Bus & route info |
| 14 | GET | `/api/android/student/holidays/` | Upcoming holidays |

## Teacher App Endpoints

| # | Method | URL | Description |
|---|--------|-----|-------------|
| 1 | GET | `/api/android/teacher/dashboard/` | Home screen |
| 2 | GET | `/api/android/teacher/profile/` | Teacher profile |
| 3 | GET | `/api/android/teacher/timetable/` | Weekly timetable |
| 4 | GET | `/api/android/teacher/students/` | Students list |
| 5 | GET | `/api/android/teacher/students/{id}/` | Student detail |
| 6 | GET | `/api/android/teacher/attendance/students/` | Load attendance sheet |
| 7 | POST | `/api/android/teacher/attendance/` | Save attendance |
| 8 | GET | `/api/android/teacher/attendance/` | Attendance summary |
| 9 | GET | `/api/android/teacher/leaves/` | Absent students |
| 10 | GET | `/api/android/teacher/assignments/` | Assignments list |
| 11 | POST | `/api/android/teacher/assignments/` | Create assignment |
| 12 | PUT | `/api/android/teacher/assignments/{id}/` | Edit assignment |
| 13 | DELETE | `/api/android/teacher/assignments/{id}/` | Delete assignment |
| 14 | GET | `/api/android/teacher/announcements/` | Announcements list |
| 15 | POST | `/api/android/teacher/announcements/` | Create announcement |
| 16 | PUT | `/api/android/teacher/announcements/{id}/` | Edit announcement |
| 17 | DELETE | `/api/android/teacher/announcements/{id}/` | Delete announcement |
| 18 | GET | `/api/android/teacher/exams/` | Exam schedule |
| 19 | GET | `/api/android/teacher/exams/{timetable_id}/result-entry/` | Marks entry screen |
| 20 | POST | `/api/android/teacher/exams/results/submit/` | Submit marks |
| 21 | GET | `/api/android/teacher/exams/results/` | View all results |
| 22 | GET | `/api/android/teacher/tasks/` | Daily tasks list |
| 23 | POST | `/api/android/teacher/tasks/` | Create task |
| 24 | GET | `/api/android/teacher/micro-schedule/` | Lesson plans list |
| 25 | POST | `/api/android/teacher/micro-schedule/` | Create lesson plan |
| 26 | PUT | `/api/android/teacher/micro-schedule/{id}/` | Edit lesson plan |
| 27 | DELETE | `/api/android/teacher/micro-schedule/{id}/` | Delete lesson plan |
| 28 | POST | `/api/android/teacher/leaves/apply/` | Apply for leave |
| 29 | GET | `/api/android/teacher/leaves/my/` | My leave history |
| 30 | GET | `/api/android/teacher/chat/staff/` | Staff list |
| 31 | GET | `/api/android/teacher/chat/conversations/` | Chat inbox |
| 32 | GET | `/api/android/teacher/chat/messages/{emp_id}/` | Message thread |
| 33 | POST | `/api/android/teacher/chat/messages/{emp_id}/` | Send message |
| 34 | GET | `/api/android/teacher/holidays/` | Upcoming holidays |
