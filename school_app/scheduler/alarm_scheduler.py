# scheduler/alarm_scheduler.py
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update

from database.session import AsyncSessionLocal
from helper.pushnotification import send_alarm_notification
from models.auth_models import FcmToken
from models.custom_alarm_models import CustomAlarm

# Slot definitions: (hour, minute, unique_job_id, query_slot)
# Clients only create alarms with slot_time = "8.00" / "9.00" / "10.00".
# The scheduler fires three reminders per slot (:00, :05, :10) all querying the same parent slot.
ALARM_SLOTS = [
    (8,  0,  "8_00_1", "8.00"),
    (8,  5,  "8_00_2", "8.00"),
    (8,  10, "8_00_3", "8.00"),
    (9,  0,  "9_00_1", "9.00"),
    (9,  5,  "9_00_2", "9.00"),
    (9,  10, "9_00_3", "9.00"),
    (10, 0,  "10_00_1", "10.00"),
    (10, 5,  "10_00_2", "10.00"),
    (10, 10, "10_00_3", "10.00"),
]


# ── Reset all statuses to 0 at 7:50 AM ────────────────────────────────────────

async def reset_alarm_status() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(update(FcmToken).values(status=0))
        await db.commit()
    print("[Scheduler] All FCM token statuses reset to 0.")


# ── Fire notifications for a given slot ───────────────────────────────────────

async def fire_alarm_slot(slot_time: str) -> None:
    today = date.today()

    async with AsyncSessionLocal() as db:
        # 1. Find alarms for today at this slot
        alarm_result = await db.execute(
            select(CustomAlarm).where(
                CustomAlarm.alarm_date == today,
                CustomAlarm.slot_time  == slot_time,
            )
        )
        alarms = alarm_result.scalars().all()

        if not alarms:
            print(f"[Scheduler] No alarms for slot {slot_time} on {today}.")
            return

        for alarm in alarms:
            # 2. Fetch FCM tokens for matching class/section where status=0
            stmt = select(FcmToken).where(FcmToken.status == 0)

            if alarm.class_id is not None:
                stmt = stmt.where(FcmToken.class_id == alarm.class_id)
            if alarm.section_id is not None:
                stmt = stmt.where(FcmToken.section_id == alarm.section_id)

            token_result = await db.execute(stmt)
            tokens = token_result.scalars().all()

            print(f"[Scheduler] Alarm {alarm.id} — slot {slot_time} — {len(tokens)} recipients.")

            for rec in tokens:
                if rec.fcm_token:
                    send_alarm_notification(
                        device_token = rec.fcm_token,
                        message      = alarm.message or "",
                        slot_time    = slot_time,
                    )


# ── Build and return scheduler ────────────────────────────────────────────────

def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    # Reset job — 7:50 AM daily
    scheduler.add_job(
        reset_alarm_status,
        CronTrigger(hour=7, minute=50, timezone="Asia/Kolkata"),
        id="reset_alarm_status",
        replace_existing=True,
    )

    # Slot jobs
    for hour, minute, job_id, query_slot in ALARM_SLOTS:
        scheduler.add_job(
            fire_alarm_slot,
            CronTrigger(hour=hour, minute=minute, timezone="Asia/Kolkata"),
            id=f"alarm_slot_{job_id}",
            args=[query_slot],
            replace_existing=True,
        )

    return scheduler
