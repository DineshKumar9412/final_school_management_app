# scheduler/alarm_scheduler.py
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update

from database.session import AsyncSessionLocal
from helper.pushnotification import send_alarm_notification
from models.auth_models import FcmToken
from models.custom_alarm_models import CustomAlarm

# Slot definitions: (hour, minute, slot_time_str)
# slot_time_str must match what is stored in custom_alarm.slot_time
ALARM_SLOTS = [
    (8,  0,  "8.00"),
    (8,  5,  "8.05"),
    (8,  10, "8.10"),
    (9,  0,  "9.00"),
    (9,  5,  "9.05"),
    (9,  10, "9.10"),
    (10, 0,  "10.00"),
    (10, 5,  "10.05"),
    (10, 10, "10.10"),
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
    scheduler = AsyncIOScheduler()

    # Reset job — 7:50 AM daily
    scheduler.add_job(
        reset_alarm_status,
        CronTrigger(hour=7, minute=50),
        id="reset_alarm_status",
        replace_existing=True,
    )

    # Slot jobs
    for hour, minute, slot_str in ALARM_SLOTS:
        scheduler.add_job(
            fire_alarm_slot,
            CronTrigger(hour=hour, minute=minute),
            id=f"alarm_slot_{slot_str}",
            args=[slot_str],
            replace_existing=True,
        )

    return scheduler
