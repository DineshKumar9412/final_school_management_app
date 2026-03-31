# security/valid_session.py
from datetime import datetime

from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.redis_cache import cache
from database.session import get_db
from models.session import Session


async def valid_session(
    client_key: str = Cookie(default=None, alias="client_key"),
    x_client_key: str = Header(default=None, alias="client_key"),
    db: AsyncSession = Depends(get_db),
) -> Session:

    client_key = client_key or x_client_key

    if not client_key:
        raise HTTPException(status_code=401, detail="Missing session")

    cache_key = f"session:{client_key}"

    # ── 1. Check Redis cache first ─────────────────────────────────────────────
    cached = await cache.get(cache_key)
    if cached:
        valid_till = datetime.fromisoformat(cached["valid_till"])
        if valid_till < datetime.utcnow():
            # Expired in cache — clean both cache + DB
            await cache.delete(cache_key)
            result = await db.execute(
                select(Session).where(Session.client_key == client_key)
            )
            session = result.scalar_one_or_none()
            if session:
                await db.delete(session)
                await db.commit()
            raise HTTPException(status_code=401, detail="Session expired")

        # Rebuild a lightweight Session object from cache (no DB hit)
        session = Session(
            id         = cached["id"],
            device_id  = cached.get("device_id"),
            user_id    = cached.get("user_id"),
            role       = cached.get("role"),
            client_key = client_key,
            valid_till = valid_till,
        )
        return session

    # ── 2. Cache miss — query DB ───────────────────────────────────────────────
    result = await db.execute(
        select(Session).where(Session.client_key == client_key)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    if session.valid_till < datetime.utcnow():
        await db.delete(session)
        await db.commit()
        raise HTTPException(status_code=401, detail="Session expired")

    # ── 3. Warm the cache for next request ────────────────────────────────────
    ttl_seconds = int((session.valid_till - datetime.utcnow()).total_seconds())
    await cache.set(
        key    = cache_key,
        value  = {
            "id"        : session.id,
            "device_id" : session.device_id,
            "user_id"   : session.user_id,
            "role"      : session.role,
            "valid_till": session.valid_till.isoformat(),
        },
        expire = ttl_seconds,
    )

    return session
