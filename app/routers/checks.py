from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.monitor import Monitor
from app.schemas.check import PaginatedCheckPairs
from app.services import check_service
from app.services.monitor_service import get_monitor_or_404

router = APIRouter(prefix="/api/monitors", tags=["checks"])


@router.get(
    "/{monitor_id}/checks",
    response_model=PaginatedCheckPairs,
    summary="Check history",
    description="Return paginated check history for a monitor, newest first. "
    "Each item pairs the HTTP and ping results from the same check cycle.",
)
async def get_checks(
    monitor: Monitor = Depends(get_monitor_or_404),
    limit: int = Query(
        default=50, ge=1, le=200, description="Number of check pairs per page"
    ),
    offset: int = Query(default=0, ge=0, description="Number of check pairs to skip"),
    db: AsyncSession = Depends(get_db),
):
    return await check_service.get_paginated_checks(db, monitor.id, limit, offset)
