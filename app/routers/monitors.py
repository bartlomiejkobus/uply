from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.monitor import Monitor
from app.schemas.monitor import MonitorCreate, MonitorResponse
from app.services.monitor_engine import monitor_engine

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


@router.get("/", response_model=list[MonitorResponse])
async def get_monitors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Monitor))
    return result.scalars().all()


@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(monitor_id: int, db: AsyncSession = Depends(get_db)):
    monitor = await db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@router.post("/", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_monitor(data: MonitorCreate, db: AsyncSession = Depends(get_db)):
    """Create a new monitor. Returns 409 if the URL is already monitored."""
    monitor = Monitor(url=str(data.url))
    db.add(monitor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Monitor with this URL already exists")
    await db.refresh(monitor)
    monitor_engine.add_monitor(monitor.id)
    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(monitor_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a monitor and all its check history."""
    monitor = await db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    monitor_engine.remove_monitor(monitor_id)
    await db.delete(monitor)
    await db.commit()
