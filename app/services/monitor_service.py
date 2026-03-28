from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.monitor import Monitor


async def list_monitors(db: AsyncSession) -> list[Monitor]:
    result = await db.execute(select(Monitor))
    return list(result.scalars().all())


async def get_monitor(db: AsyncSession, monitor_id: int) -> Monitor | None:
    return await db.get(Monitor, monitor_id)


async def get_monitor_or_404(
    monitor_id: int, db: AsyncSession = Depends(get_db)
) -> Monitor:
    monitor = await db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


async def create_monitor(db: AsyncSession, url: str) -> Monitor | None:
    """Create a new monitor. Returns None if URL already exists."""
    monitor = Monitor(url=url)
    db.add(monitor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return None
    await db.refresh(monitor)
    return monitor


async def delete_monitor(db: AsyncSession, monitor: Monitor) -> None:
    await db.delete(monitor)
    await db.commit()
