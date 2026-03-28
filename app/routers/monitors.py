from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.monitor import Monitor
from app.schemas.monitor import MonitorCreate, MonitorResponse
from app.services import monitor_service
from app.services.monitor_service import get_monitor_or_404
from app.services.monitor_engine import monitor_engine

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


@router.get(
    "/",
    response_model=list[MonitorResponse],
    summary="List monitors",
    description="Return all registered monitors.",
)
async def get_monitors(db: AsyncSession = Depends(get_db)):
    return await monitor_service.list_monitors(db)


@router.get(
    "/{monitor_id}",
    response_model=MonitorResponse,
    summary="Get monitor",
    description="Return a single monitor by ID.",
)
async def get_monitor(monitor: Monitor = Depends(get_monitor_or_404)):
    return monitor


@router.post(
    "/",
    response_model=MonitorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create monitor",
    description="Register a new URL to monitor. Returns 409 if the URL is already monitored.",
)
async def create_monitor(data: MonitorCreate, db: AsyncSession = Depends(get_db)):
    monitor = await monitor_service.create_monitor(db, str(data.url))
    if not monitor:
        raise HTTPException(
            status_code=409, detail="Monitor with this URL already exists"
        )
    monitor_engine.add_monitor(monitor.id)
    return monitor


@router.delete(
    "/{monitor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete monitor",
    description="Delete a monitor and all its check history.",
)
async def delete_monitor(
    monitor: Monitor = Depends(get_monitor_or_404),
    db: AsyncSession = Depends(get_db),
):
    monitor_engine.remove_monitor(monitor.id)
    await monitor_service.delete_monitor(db, monitor)
