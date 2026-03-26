# helper/optmessage.py
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from random import randint

from models.user_models import OtpVerification
from helper.pushnotification import send_push_notification


MAX_ATTEMPTS       = 3
OTP_EXPIRE_MINUTES = 5


def generate_otp() -> str:
    return str(randint(100000, 999999))


async def _get_active_otp(identifier: str, db: AsyncSession):
    """Fetch the latest unused OTP record for an identifier."""
    stmt = select(OtpVerification).where(
        OtpVerification.identifier == identifier,
        OtpVerification.is_used    == False,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _send_otp_logic(identifier: str, db: AsyncSession, fcb_token: str) -> str:
    """
    Core send OTP logic — reused by send and resend.
    Invalidates any existing OTP, creates a new one, returns the OTP.
    """
    existing = await _get_active_otp(identifier, db)
    if existing:
        existing.is_used = True

    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)

    new_otp = OtpVerification(
        identifier = identifier,
        otp        = otp,
        expires_at = expires_at,
    )
    db.add(new_otp)
    await db.commit()

    try:
        send_push_notification(device_token=fcb_token, otp=otp)
    except Exception as E:
        db.rollback()
    return otp


async def _verify_otp_logic(identifier: str, otp: str, db: AsyncSession) -> bool:
    """
    Core verify OTP logic.
    Returns True on success, raises HTTPException on failure.
    """
    otp_record = await _get_active_otp(identifier, db)

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active OTP found. Please request a new one."
        )

    if otp_record.attempts >= MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Max attempts reached. Please request a new OTP."
        )

    if otp_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="OTP has expired. Please request a new one."
        )

    if otp_record.otp != otp:
        otp_record.attempts += 1
        await db.commit()
        remaining = MAX_ATTEMPTS - otp_record.attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP. {remaining} attempts remaining."
        )

    otp_record.is_used = True
    await db.commit()
    return True
